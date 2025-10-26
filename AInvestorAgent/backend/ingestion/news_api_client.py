# AInvestorAgent/backend/ingestion/news_api_client.py
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv

# 自动加载 .env（保持你原本逻辑）
load_dotenv()

NEWS_API_KEY = (
    os.getenv("NEWS_API_KEY")
    or os.getenv("NEWSAPI_KEY")
    or os.getenv("NEWS_APIKEY")
    or ""
)

BASE_URL = "https://newsapi.org/v2/everything"

# =========================================
# 你的 watchlist 22 只 + 常见别名（可随时补）
# =========================================
SYMBOL_ALIASES: dict[str, list[str]] = {
    # —— 你已有的（节选）——
    "AAPL": ["Apple", "Apple Inc", "Apple Computer"],
    "MSFT": ["Microsoft", "Microsoft Corp", "Microsoft Corporation"],
    "NVDA": ["Nvidia", "NVIDIA Corp", "NVIDIA Corporation"],
    "AMZN": ["Amazon", "Amazon.com", "Amazon.com Inc"],
    "GOOGL": ["Google", "Alphabet", "Alphabet Inc"],
    "TSLA": ["Tesla", "Tesla Motors", "Tesla Inc"],
    "META": ["Meta", "Facebook", "Meta Platforms", "Meta Platforms Inc"],
    "APP":  ["AppLovin", "Applovin", "AppLovin Corp", "AppLovin Corporation"],
    "ORCL": ["Oracle", "Oracle Corp", "Oracle Corporation"],
    "AVGO": ["Broadcom", "Broadcom Inc"],
    "AMD":  ["AMD", "Advanced Micro Devices", "Advanced Micro Devices Inc"],
    "INOD": ["Innodata", "Innodata Inc"],
    "SHOP": ["Shopify", "Shopify Inc"],
    "PATH": ["UiPath", "UiPath Inc"],
    "ARM":  ["Arm Holdings", "ARM Holdings", "Arm Holdings Plc"],
    "ASML": ["ASML", "ASML Holding", "ASML Holding NV"],

    # ===== 重点补强这 6 只 =====
    # Constellation Energy（媒体常省略 Corporation / Group）
    "CEG": [
        "Constellation Energy",
        "Constellation Energy Corp",
        "Constellation Energy Corporation",
        "Constellation Energy Group",
        "Constellation",  # 常见简称
    ],

    # Vistra（很多稿子写“Vistra Energy”，尤其旧文和行业报道）
    "VST": [
        "Vistra",
        "Vistra Corp",
        "Vistra Corporation",
        "Vistra Energy",
    ],

    # Centrus Energy（也常写为“Centrus”）
    "LEU": [
        "Centrus Energy",
        "Centrus Energy Corp",
        "Centrus Energy Corporation",
        "Centrus",
    ],

    # Iris Energy（上市主体是 Limited）
    "IREN": [
        "Iris Energy",
        "Iris Energy Limited",
        "Iris Energy Ltd",
    ],

    # Neuberger Berman Income Securities（封闭式基金，媒体多写全称）
    "NBIS": [
        "Neuberger Berman",
        "Neuberger Berman Income Securities",
        "Neuberger Berman Income Securities Fund",
        "Neuberger Berman Income Securities Fund Inc",
    ],

    # Palantir（多数报道写公司名）
    "PLTR": [
        "Palantir",
        "Palantir Technologies",
        "Palantir Technologies Inc",
    ],
}


def build_terms(symbol: str) -> list[str]:
    """
    为 NewsAPI 逐个请求生成关键词列表（每个 term 单独作为 q）：
    - 代码（"ORCL"）
    - 美股常见写法：$ORCL
    - 交易所前缀（两种空格风格）："NASDAQ:ORCL" / "NYSE:ORCL" / "NASDAQ: ORCL" / "NYSE: ORCL"
    - 公司别名（逐个短语）
    统一用引号包裹，强制短语匹配。
    """
    sym = symbol.upper().strip()
    aliases = SYMBOL_ALIASES.get(sym, [])

    terms: list[str] = []
    # 代码
    terms.append(f'"{sym}"')
    # $代码
    terms.append(f'"${sym}"')
    # 交易所前缀（无空格 & 带空格两套）
    for ex in ("NASDAQ", "NYSE"):
        terms.append(f'"{ex}:{sym}"')
        terms.append(f'"{ex}: {sym}"')

    # 公司别名
    for a in aliases:
        a2 = a.strip()
        if not a2:
            continue
        terms.append(f'"{a2}"')

    # 去重保持顺序（防止无意义重复）
    seen = set()
    deduped = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped




def fetch_news(symbol: str, days: int = 14, limit: int = 100, pages: int = 1) -> List[Dict[str, Any]]:
    """
    从 NewsAPI 抓取新闻：
    - 不用 OR 拼接在同一个 q；
    - 对每个 term（代码/$代码/交易所前缀/公司名别名）分别请求，再在本地按 url 去重合并。
    """
    if not NEWS_API_KEY:
        raise RuntimeError("未检测到 NEWS_API_KEY，请在 .env 中设置你的 NewsAPI 密钥。")

    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    page_size = min(max(limit, 1), 100)

    headers = {"X-Api-Key": NEWS_API_KEY}
    out: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()

    for term in build_terms(symbol):
        for page in range(1, max(1, pages) + 1):
            params = {
                "q": term,
                "from": since_str,
                "sortBy": "publishedAt",
                "language": "en",
                "searchIn": "title,description,content",
                "pageSize": page_size,
                "page": page,
            }
            r = requests.get(BASE_URL, params=params, headers=headers, timeout=20)
            if not r.ok:
                break
            j = r.json()
            articles = j.get("articles", [])
            if not articles:
                break

            for a in articles:
                url = a.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                out.append({
                    "title": a.get("title") or "",
                    "description": a.get("description") or "",
                    "url": url,
                    "source": (a.get("source") or {}).get("name"),
                    "published_at": a.get("publishedAt") or "",
                })

            if len(articles) < page_size:
                break

    out.sort(key=lambda x: (x.get("published_at") or ""), reverse=True)
    return out


