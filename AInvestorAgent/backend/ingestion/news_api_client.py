import os, requests
from datetime import datetime, timedelta, timezone

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
# 如你用自有站点，请在 .env 里设置 NEWS_BASE_URL
# 默认用 newsapi.org 的 everything 端点
NEWS_BASE_URL = os.getenv("NEWS_BASE_URL", "https://newsapi.org/v2/everything")

def _iso(dt):  # UTC ISO8601
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_news(symbol: str, days: int = 7, limit: int = 50) -> list[dict]:
    """
    标准化返回:
      [{title, summary, url, source, published_at}, ...]  (published_at 为 ISO8601 UTC 字符串)
    兼容 newsapi.org；若你把 NEWS_BASE_URL 指向自家/别家，只要支持 q/from/to/pageSize/sortBy/language 即可。
    API Key 同时通过 header 与 query 传入，以适配不同供应商。
    """
    if not NEWS_API_KEY:
        raise RuntimeError("缺少 NEWS_API_KEY")

    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(days=days)

    params = {
        "q": symbol,
        "from": from_dt.date().isoformat(),
        "to": to_dt.date().isoformat(),
        "pageSize": min(int(limit), 100),
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": NEWS_API_KEY,          # 大多数供应商接受 query 里的 apiKey
    }
    headers = {
        "X-Api-Key": NEWS_API_KEY        # 有些只认 header
    }

    r = requests.get(NEWS_BASE_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()

    # 兼容 newsapi.org 的数据结构
    articles = data.get("articles") or data.get("data") or []
    out = []
    for a in articles:
        title = a.get("title") or ""
        summary = a.get("description") or a.get("content") or a.get("summary") or ""
        url = a.get("url") or a.get("link") or ""
        src = (a.get("source") or {}).get("name") if isinstance(a.get("source"), dict) else a.get("source") or ""
        pub = a.get("publishedAt") or a.get("published_at") or a.get("date") or ""
        # 统一时间
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except Exception:
            dt = to_dt
        out.append({
            "title": title.strip(),
            "summary": (summary or "").strip(),
            "url": url.strip(),
            "source": (src or "").strip(),
            "published_at": _iso(dt),
        })
    return out

# 轻量情绪打分（关键词投票；后续可替换为 LLM/词典）
_POS = {"beat","surge","growth","upgrade","strong","record","positive","gain","outperform","buy","rise"}
_NEG = {"miss","fall","downgrade","lawsuit","fraud","negative","loss","recall","layoff","sell","drop"}

def sentiment_score(title: str, summary: str = "") -> float:
    text = f"{title} {summary}".lower()
    p = sum(1 for w in _POS if f" {w} " in f" {text} ")
    n = sum(1 for w in _NEG if f" {w} " in f" {text} ")
    if p == n == 0: return 0.0
    s = (p - n) / max(p + n, 1)
    return max(-1.0, min(1.0, s))
