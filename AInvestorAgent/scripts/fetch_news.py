#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/fetch_news.py - 终极修复版本
关键修复:
1. published_at 日期比较使用正确的SQL函数
2. 去重只检查最近60天
3. 修复字段顺序
"""

import sys
import os
import time
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, UTC

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
except Exception:
    pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from backend.storage.db import SessionLocal

try:
    from backend.storage.models import NewsRaw, NewsScore, Symbol

    HAS_SYMBOL_MODEL = True
except Exception:
    from backend.storage.models import NewsRaw, NewsScore

    HAS_SYMBOL_MODEL = False

NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2/everything")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
DEFAULT_TIMEOUT = int(os.getenv("NEWS_TIMEOUT", "35"))


def _to_iso_utc_days_ago(days: int) -> str:
    dt = datetime.now(UTC) - timedelta(days=int(days))
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_published_at(raw: Optional[str]):
    """
    标准化时间为 Python datetime 对象
    SQLAlchemy的DATETIME类型要求datetime对象，不能是字符串！
    """
    if not raw:
        return None
    x = raw.strip()
    if not x:
        return None

    # 解析ISO格式: 2025-10-24T16:26:25Z
    # 移除时区标记 'Z'，转换为datetime对象
    try:
        # 移除 'Z' 后缀
        if x.endswith('Z'):
            x = x[:-1]

        # 解析为datetime对象
        from datetime import datetime as dt
        return dt.fromisoformat(x)
    except Exception:
        # 如果解析失败，返回None
        return None


def _get_company_name(db: Session, symbol: str) -> Optional[str]:
    if HAS_SYMBOL_MODEL:
        row = db.query(Symbol).filter(Symbol.symbol == symbol).first()
        return getattr(row, "name", None) if row else None
    try:
        result = db.execute(text("SELECT name FROM symbols WHERE symbol = :sym LIMIT 1"), {"sym": symbol}).fetchone()
        return result[0] if result and result[0] else None
    except Exception:
        return None


def _count_scored(db: Session, ids: List[int]) -> int:
    if not ids:
        return 0
    placeholders = ",".join([f":p{i}" for i in range(len(ids))])
    q = f"SELECT COUNT(1) FROM news_scores WHERE news_id IN ({placeholders})"
    params = {f"p{i}": nid for i, nid in enumerate(ids)}
    row = db.execute(text(q), params).fetchone()
    return int(row[0]) if row else 0


def fetch_news(symbol: str, *, days: int = 30, pages: int = 1,
               timeout: int = DEFAULT_TIMEOUT, noproxy: bool = False,
               db_for_query: Optional[Session] = None,
               debug: bool = False) -> List[Dict[str, Any]]:
    if not NEWS_API_KEY:
        raise RuntimeError("缺少 NEWS_API_KEY 环境变量")

    company = None
    if db_for_query is not None:
        try:
            company = _get_company_name(db_for_query, symbol)
        except Exception:
            company = None

    query = f'"{company}" OR {symbol}' if company else symbol
    if debug:
        print(f"  🔍 搜索词: {query}")

    session = requests.Session()
    if noproxy:
        session.trust_env = False
    headers = {"X-Api-Key": NEWS_API_KEY, "Accept": "application/json", "Connection": "close"}

    since_iso = _to_iso_utc_days_ago(days)
    all_articles: List[Dict[str, Any]] = []

    for p in range(1, int(pages) + 1):
        params = {
            "q": query,
            "language": "en",
            "from": since_iso,
            "sortBy": "publishedAt",
            "pageSize": 100,
            "page": p,
        }

        if debug:
            print(f"  📡 请求第{p}页...")

        try:
            r = session.get(NEWS_API_URL, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            sys.stderr.write(f"[warn] {symbol} p{p} request error: {e}\n")
            break

        if r.status_code != 200:
            sys.stderr.write(f"[warn] {symbol} p{p} HTTP {r.status_code}: {r.text[:160]}\n")
            break

        data = r.json() or {}
        articles = data.get("articles") or []
        total_results = data.get("totalResults", 0)

        if debug:
            print(f"  📰 API返回: {len(articles)}条 (总共{total_results}条)")

        if not articles:
            break

        all_articles.extend(articles)

        if len(articles) < 100:
            break

        time.sleep(0.6)

    if debug:
        print(f"  ✅ 共获取 {len(all_articles)} 条新闻")

    return all_articles


def upsert_news_and_score(db: Session, symbol: str, items: List[Dict[str, Any]], *,
                          rescore_window_days: int = 30,
                          debug: bool = False) -> Dict[str, int]:
    """
    将新闻入库并打分

    🔧 关键修复: 使用 SQL datetime() 函数正确比较日期
    """
    inserted = dupe = 0

    # 🔧 修复: 使用SQL的datetime函数来正确比较日期
    # 计算60天前的日期
    cutoff_days = 60

    # 使用原生SQL，让SQLite处理日期比较
    existing_urls_query = text("""
        SELECT url FROM news_raw 
        WHERE symbol = :symbol 
        AND datetime(published_at) >= datetime('now', :delta)
    """)

    result = db.execute(existing_urls_query, {
        "symbol": symbol,
        "delta": f"-{cutoff_days} days"
    })

    existing_urls = {row[0] for row in result if row[0]}

    if debug:
        print(f"  📦 数据库中最近{cutoff_days}天已有 {len(existing_urls)} 条URL")

    batch_urls = set()

    for i, a in enumerate(items, 1):
        url = (a.get("url") or "").strip()
        if not url:
            continue

        if url in batch_urls:
            dupe += 1
            continue

        if url in existing_urls:
            dupe += 1
            if debug and i <= 3:
                print(f"    ⚠️ URL已存在: {url[:60]}...")
            continue

        # 🔧 修复: publishedAt 在前
        pub_raw = a.get("publishedAt") or a.get("published_at") or ""
        published_at = _normalize_published_at(pub_raw)

        src_obj = a.get("source") or {}
        source = (src_obj.get("name") if isinstance(src_obj, dict) else str(src_obj)) or "unknown"

        obj = NewsRaw(
            symbol=symbol,
            title=a.get("title") or "",
            summary=a.get("description") or "",
            url=url,
            source=source,
            published_at=published_at
        )

        try:
            db.add(obj)
            db.flush()
            batch_urls.add(url)
            inserted += 1

            if debug and inserted <= 5:
                print(f"    ✅ 新增: {published_at} - {obj.title[:40]}...")

        except IntegrityError:
            db.rollback()
            dupe += 1
            if debug and dupe <= 3:
                print(f"    ⚠️ 重复(IntegrityError): {url[:60]}...")
        except Exception as e:
            db.rollback()
            if debug:
                print(f"    ❌ 入库失败: {e}")
            continue

    try:
        db.commit()
        if debug:
            print(f"  💾 提交完成: 新增{inserted}, 去重{dupe}")
    except IntegrityError:
        db.rollback()
        if debug:
            print(f"  ❌ 提交失败(IntegrityError)")

    # 打分阶段 - 处理所有未打分的新闻（包括之前入库但未打分的）
    scored = 0
    try:
        from backend.sentiment.scorer import classify_polarity
        from datetime import datetime as dt

        # 查找该股票所有未打分的新闻（不限于刚插入的）
        window_sql = text("""
            SELECT nr.id
            FROM news_raw AS nr
            LEFT JOIN news_scores AS ns ON ns.news_id = nr.id
            WHERE nr.symbol = :sym
              AND datetime(nr.published_at) >= datetime('now', :delta)
              AND ns.news_id IS NULL
            ORDER BY nr.id DESC
            LIMIT 1000
        """)

        delta = f"-{int(rescore_window_days)} days"
        ids = [row[0] for row in db.execute(window_sql, {"sym": symbol, "delta": delta}).fetchall()]

        if ids:
            if debug:
                print(f"  🧮 待打分新闻: {len(ids)}条（包括历史未打分）")

            # 获取新闻记录
            news_items = db.query(NewsRaw).filter(NewsRaw.id.in_(ids)).all()

            # 逐条打分
            for news in news_items:
                # 使用classify_polarity计算情绪
                sentiment = classify_polarity(news.title or "", news.summary or "")

                # 创建打分记录
                score_record = NewsScore(
                    news_id=news.id,
                    sentiment=sentiment
                )
                db.add(score_record)
                scored += 1

            db.commit()

            if debug:
                print(f"  ✅ 完成打分: {scored}条")
        else:
            if debug:
                print(f"  ℹ️ 无需打分的新闻")

    except Exception as e:
        db.rollback()
        if debug:
            print(f"  ⚠️ 打分失败: {e}")
            import traceback
            traceback.print_exc()

    return {"inserted": inserted, "dupe": dupe, "scored": scored}


def main():
    p = argparse.ArgumentParser(description="批量抓取新闻 → 入库 → 打分")
    p.add_argument("--symbols", type=str, required=True, help="股票列表，用逗号分隔")
    p.add_argument("--days", type=int, default=30, help="抓取最近N天的新闻")
    p.add_argument("--pages", type=int, default=2, help="每个股票抓取N页")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--noproxy", action="store_true")
    p.add_argument("--rescore-window-days", type=int, default=30)
    p.add_argument("--debug", action="store_true", help="显示详细调试信息")
    args = p.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        print("⚠️ 未提供有效的 symbols")
        sys.exit(1)
    if not NEWS_API_KEY:
        print("⚠️ 缺少 NEWS_API_KEY 环境变量")
        sys.exit(2)

    total = {"inserted": 0, "dupe": 0, "scored": 0}

    print(f"\n{'=' * 70}")
    print(f"开始处理 {len(symbols)} 只股票")
    print(f"{'=' * 70}\n")

    with SessionLocal() as db:
        for i, sym in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] 处理 {sym}...")

            try:
                items = fetch_news(
                    sym,
                    days=args.days,
                    pages=args.pages,
                    timeout=args.timeout,
                    noproxy=args.noproxy,
                    db_for_query=db,
                    debug=args.debug
                )

                stats = upsert_news_and_score(
                    db,
                    sym,
                    items,
                    rescore_window_days=args.rescore_window_days,
                    debug=args.debug
                )

                for k in total:
                    total[k] += stats.get(k, 0)

                print(f"✅ {sym}: 新增 {stats['inserted']} 条, 去重 {stats['dupe']} 条, 打分 {stats['scored']} 条\n")

            except Exception as e:
                print(f"⚠️ {sym} 抓取失败: {e}\n")
                if args.debug:
                    import traceback
                    traceback.print_exc()

    print(f"{'=' * 70}")
    print(f"✅ 完成：新增={total['inserted']} 去重={total['dupe']} 打分={total['scored']}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()