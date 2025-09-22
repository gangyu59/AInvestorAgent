#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用 newsapi.org 拉近 N 天新闻 -> 写入 SQLite (news_raw, news_scores)
- 用 X-Api-Key 传密钥（更稳）
- 支持 --noproxy 忽略系统代理（配合 VPN 使用）
- 只依赖 requests + 你的 backend.* ORM，其他不动

用法：
  python scripts/fetch_news.py --symbols AAPL,MSFT,TSLA,SPY --days 14 --noproxy
"""

import os
import sys
import argparse
import datetime as dt
import re
from pathlib import Path
from typing import List, Dict, Any
import json, socket, ssl
from urllib.parse import urlencode
import time

# ---- 让 backend.* 可 import ----
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy.exc import IntegrityError
from backend.storage.db import SessionLocal, engine, Base
from backend.storage.models import NewsRaw, NewsScore

# ---- 情绪词典 [-1,1] ----
_POS = {"beat","beats","surge","soar","jump","bullish","gain","gains","up",
        "optimistic","strong","record","profit","profits","upgrade","buy",
        "outperform","positive","growth","rally","win","wins","expand"}
_NEG = {"miss","falls","fall","drop","plunge","bearish","down","loss",
        "losses","warning","downgrade","sell","underperform","negative",
        "fraud","probe","lawsuit","weak","cut","cuts","decline","recall"}
_word_re = re.compile(r"[A-Za-z']+")


# -- 尝试通过 DoH 拿 newsapi.org 的 A 记录（失败也没关系）
def _doh_candidates(host: str, use_proxy: bool, timeout: int = 6) -> list[str]:
    sess = requests.Session()
    sess.trust_env = use_proxy  # 与主会话一致：--noproxy 时不走系统代理
    sess.headers.update({"accept": "application/dns-json"})
    out: list[str] = []
    for url in (
        "https://dns.google/resolve",
        "https://cloudflare-dns.com/dns-query",
    ):
        try:
            r = sess.get(url, params={"name": host, "type": "A"}, timeout=timeout)
            j = r.json()
            for a in j.get("Answer") or []:
                if a.get("type") == 1 and a.get("data"):
                    out.append(a["data"])
        except Exception:
            pass
    # 回退：用系统 getaddrinfo（只取 IPv4）
    if not out:
        try:
            gai = socket.getaddrinfo(host, 443, family=socket.AF_INET, proto=socket.IPPROTO_TCP)
            out = [t[4][0] for t in gai]
        except Exception:
            out = []
    # 去重保持顺序
    seen = set(); uniq = []
    for ip in out:
        if ip not in seen:
            seen.add(ip); uniq.append(ip)
    return uniq

# -- 用原生 socket + SSL 做 “连 IP 但 SNI=host” 的 GET，请求头带 X-Api-Key；返回 JSON
def _https_json_via_ip(host: str, ip: str, path_qs: str, headers: dict, timeout: int = 25) -> dict:
    ctx = ssl.create_default_context()  # 严格校验证书 & 主机名
    with socket.create_connection((ip, 443), timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            req = f"GET {path_qs} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
            for k, v in headers.items():
                req += f"{k}: {v}\r\n"
            req += "\r\n"
            ssock.sendall(req.encode("utf-8"))
            chunks = bytearray()
            while True:
                c = ssock.recv(8192)
                if not c: break
                chunks.extend(c)
    # 解析响应（含 chunked 处理）
    sep = chunks.find(b"\r\n\r\n")
    if sep < 0: raise RuntimeError("bad http response")
    hdr = chunks[:sep].decode("iso-8859-1", errors="ignore").lower()
    body = chunks[sep+4:]
    if "transfer-encoding: chunked" in hdr:
        body = _decode_chunked(body)
    status_line = chunks.split(b"\r\n", 1)[0].decode("ascii", errors="ignore")
    if not status_line.split()[1].startswith(("2","3")):
        raise RuntimeError(status_line)
    return json.loads(body.decode("utf-8"))

def _decode_chunked(b: bytes) -> bytes:
    out = bytearray(); i = 0
    while True:
        j = b.find(b"\r\n", i)
        if j < 0: break
        try: size = int(b[i:j].decode("ascii").strip(), 16)
        except Exception: break
        i = j + 2
        if size == 0: break
        out.extend(b[i:i+size]); i += size + 2
    return bytes(out)

def simple_sentiment(text: str) -> float:
    if not text:
        return 0.0
    toks = [t.lower() for t in _word_re.findall(text)]
    p = sum(1 for t in toks if t in _POS)
    n = sum(1 for t in toks if t in _NEG)
    return 0.0 if (p == 0 and n == 0) else (p - n) / float(p + n)

# ---- requests Session ----
def make_session(noproxy: bool, timeout: int = 25) -> requests.Session:
    s = requests.Session()
    s.trust_env = (not noproxy)  # True=读取系统代理，False=忽略
    retries = Retry(total=3, backoff_factor=1.5,
                    status_forcelist=[429,500,502,503,504],
                    allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://",  HTTPAdapter(max_retries=retries))
    s.request_timeout = timeout
    return s

# ---- 拉 newsapi ----
def fetch_from_newsapi(sess: requests.Session, symbol: str, days: int, api_key: str,
                       base_url: str = "https://newsapi.org/v2/everything",
                       lang: str = "en", timeout: int = 25,
                       pages: int = 1, page_size: int = 100,
                       force_ip: str | None = None) -> list[dict]:
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "q": symbol,
        "from": since,
        "language": lang,
        "searchIn": "title,description",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "page": 1,
    }
    headers = {
        "X-Api-Key": api_key,
        "User-Agent": "AInvestorAgent/1.0 (+news fetch)",
        "Accept": "application/json",
        "Connection": "close",
    }
    out: list[dict] = []

    # ① 先按正常域名逐页拉，某一页失败就保留已获数据并停止
    for page in range(1, max(1, pages) + 1):
        params["page"] = page
        try:
            r = sess.get(base_url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            j = r.json()
            arts = (j or {}).get("articles") or []
            for a in arts:
                out.append({
                    "title": a.get("title") or "",
                    "description": a.get("description") or "",
                    "url": a.get("url") or "",
                    "source": ((a.get("source") or {}).get("name")) or "",
                    "publishedAt": a.get("publishedAt") or "",
                })
            if len(arts) < int(page_size):
                break
            time.sleep(0.6)
        except Exception as e:
            if out:
                print(f"[WARN] {symbol}: page {page} failed ({e}); keep {len(out)} from previous pages")
                break
            # ② 第一页就失败 → 进入 IP 兜底（SNI=host）
            host = "newsapi.org"
            path_qs = "/v2/everything?" + urlencode(params, doseq=True)
            candidates = [force_ip] if force_ip else _doh_candidates(host, use_proxy=sess.trust_env)
            last = e
            for ip in [c for c in candidates if c]:
                try:
                    j = _https_json_via_ip(host, ip, path_qs, headers, timeout=timeout)
                    arts = (j or {}).get("articles") or []
                    for a in arts:
                        out.append({
                            "title": a.get("title") or "",
                            "description": a.get("description") or "",
                            "url": a.get("url") or "",
                            "source": ((a.get("source") or {}).get("name")) or "",
                            "publishedAt": a.get("publishedAt") or "",
                        })
                    # 兜底只取第一页，够前端时间轴/列表
                    return out
                except Exception as ee:
                    last = ee
                    continue
            # 所有 IP 都失败，抛出原始错误
            raise last
    return out



# ---- 落库 ----
def to_datetime_aware(s: str) -> dt.datetime:
    if not s:
        return dt.datetime.now(dt.timezone.utc)
    try:
        return dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception:
        return dt.datetime.now(dt.timezone.utc)

def upsert_news_and_score(session, symbol: str, items: List[Dict[str, Any]]) -> Dict[str, int]:
    ins = dup = sc = 0
    for a in items:
        title = (a.get("title") or "").strip()
        url = (a.get("url") or "").strip()
        if not title or not url:
            continue
        n = NewsRaw(
            symbol=symbol,
            title=title,
            summary=(a.get("description") or "").strip(),
            url=url,
            source=(a.get("source") or "").strip(),
            published_at=to_datetime_aware(a.get("publishedAt") or ""),
        )
        try:
            session.add(n); session.flush(); ins += 1
        except IntegrityError:
            session.rollback(); dup += 1
            n = session.query(NewsRaw).filter(NewsRaw.symbol==symbol, NewsRaw.url==url).first()
            if not n: continue
        score = simple_sentiment(f"{n.title}. {n.summary or ''}")
        session.add(NewsScore(news_id=n.id, sentiment=float(score))); sc += 1
    session.commit()
    return {"inserted": ins, "dupe": dup, "scored": sc}

# ---- CLI ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True, help="逗号分隔: AAPL,MSFT,TSLA,SPY")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--noproxy", action="store_true", help="忽略系统代理（配合 VPN 用）")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--pages", type=int, default=1, help="最多拉取的分页数（默认1页，稳定优先）")
    ap.add_argument("--force-ip", help="直连指定 IPv4（仍保留 SNI=newsapi.org）")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    api_key = os.getenv("NEWS_API_KEY") or ""
    base_url = os.getenv("NEWS_API_URL") or "https://newsapi.org/v2/everything"
    if not api_key:
        print("❌ 缺少 NEWS_API_KEY（在项目根 .env 配置）"); return 2

    Base.metadata.create_all(bind=engine)
    sess = make_session(noproxy=args.noproxy, timeout=args.timeout)

    total = {"inserted":0,"dupe":0,"scored":0}
    with SessionLocal() as db:
        for sym in symbols:
            try:
                items = fetch_from_newsapi(
                    sess, sym, args.days, api_key, base_url, args.lang, args.timeout,
                    pages=args.pages, page_size=100, force_ip=args.force_ip
                )
                stats = upsert_news_and_score(db, sym, items)
                for k in total: total[k] += stats[k]
                print(f"✅ {sym}: 新增 {stats['inserted']} 条, 去重 {stats['dupe']} 条, 打分 {stats['scored']} 条")
            except Exception as e:
                print(f"⚠️ {sym} 拉取失败：{e}")

    print(f"=== 完成：inserted={total['inserted']} dupe={total['dupe']} scored={total['scored']} ===")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
