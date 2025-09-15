# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sqlite3, random, math, csv
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

DB_PATH = os.environ.get("AINVESTOR_DB", "db/stock.sqlite")
EXPORT_DIR = "db/exports"

# ---------- 数据类 ----------
@dataclass
class SymbolRow:
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    currency: str = "USD"

@dataclass
class PriceRow:
    symbol: str
    date: str        # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int

@dataclass
class FundamentalRow:
    symbol: str
    as_of: str       # YYYY-MM-DD
    pe: float
    pb: float
    roe: float
    net_margin: float
    market_cap: float
    source: str = "fixture"

@dataclass
class NewsRawRow:
    symbol: str
    title: str
    summary: str
    url: str
    source: str
    published_at: str   # YYYY-MM-DD

@dataclass
class NewsScoreRow:
    news_id: int
    sentiment: float
    topic: Optional[str] = None

# ---------- DB 初始化 ----------
SCHEMA = {
    "symbols": """
    CREATE TABLE IF NOT EXISTS symbols(
        symbol TEXT PRIMARY KEY,
        name TEXT, exchange TEXT, sector TEXT, industry TEXT, currency TEXT
    )""",
    "prices_daily": """
    CREATE TABLE IF NOT EXISTS prices_daily(
        symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER,
        PRIMARY KEY(symbol, date)
    )""",
    "fundamentals": """
    CREATE TABLE IF NOT EXISTS fundamentals(
        symbol TEXT PRIMARY KEY,
        as_of TEXT, pe REAL, pb REAL, roe REAL, net_margin REAL, market_cap REAL, source TEXT
    )""",
    "news_raw": """
    CREATE TABLE IF NOT EXISTS news_raw(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, title TEXT, summary TEXT, url TEXT, source TEXT, published_at TEXT
    )""",
    "news_scores": """
    CREATE TABLE IF NOT EXISTS news_scores(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        news_id INTEGER, sentiment REAL, topic TEXT,
        FOREIGN KEY(news_id) REFERENCES news_raw(id)
    )"""
}

def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    for ddl in SCHEMA.values():
        conn.execute(ddl)
    conn.commit()
    return conn

# ---------- 工具：写入/导出 ----------
def upsert_symbols(conn: sqlite3.Connection, rows: List[SymbolRow]):
    sql = """INSERT INTO symbols(symbol,name,exchange,sector,industry,currency)
             VALUES(?,?,?,?,?,?)
             ON CONFLICT(symbol) DO UPDATE SET
                name=excluded.name, exchange=excluded.exchange, sector=excluded.sector,
                industry=excluded.industry, currency=excluded.currency"""
    conn.executemany(sql, [(r.symbol, r.name, r.exchange, r.sector, r.industry, r.currency) for r in rows])

def upsert_fundamentals(conn: sqlite3.Connection, rows: List[FundamentalRow]):
    sql = """INSERT INTO fundamentals(symbol,as_of,pe,pb,roe,net_margin,market_cap,source)
             VALUES(?,?,?,?,?,?,?,?)
             ON CONFLICT(symbol) DO UPDATE SET
               as_of=excluded.as_of, pe=excluded.pe, pb=excluded.pb,
               roe=excluded.roe, net_margin=excluded.net_margin,
               market_cap=excluded.market_cap, source=excluded.source"""
    conn.executemany(sql, [(r.symbol,r.as_of,r.pe,r.pb,r.roe,r.net_margin,r.market_cap,r.source) for r in rows])

def upsert_prices(conn: sqlite3.Connection, rows: List[PriceRow]):
    sql = """INSERT OR REPLACE INTO prices_daily(symbol,date,open,high,low,close,adj_close,volume)
             VALUES(?,?,?,?,?,?,?,?)"""
    conn.executemany(sql, [(r.symbol,r.date,r.open,r.high,r.low,r.close,r.adj_close,r.volume) for r in rows])

def insert_news(conn: sqlite3.Connection, rows: List[NewsRawRow]) -> List[int]:
    sql = """INSERT INTO news_raw(symbol,title,summary,url,source,published_at) VALUES(?,?,?,?,?,?)"""
    cur = conn.executemany(sql, [(r.symbol,r.title,r.summary,r.url,r.source,r.published_at) for r in rows])
    conn.commit()
    # sqlite3 不直接返回多自增ID；重新查询最后N条ID：
    last_id = conn.execute("SELECT MAX(id) FROM news_raw").fetchone()[0] or 0
    ids = list(range(last_id - len(rows) + 1, last_id + 1))
    return ids

def insert_news_scores(conn: sqlite3.Connection, rows: List[NewsScoreRow]):
    sql = """INSERT INTO news_scores(news_id,sentiment,topic) VALUES(?,?,?)"""
    conn.executemany(sql, [(r.news_id, r.sentiment, r.topic) for r in rows])

def export_csv(table: str, conn: sqlite3.Connection, where: str = "", params: Tuple = ()):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    sql = f"SELECT * FROM {table} " + (f"WHERE {where}" if where else "")
    rows = conn.execute(sql, params).fetchall()
    cols = [d[0] for d in conn.execute(f"PRAGMA table_info({table})")]
    path = os.path.join(EXPORT_DIR, f"{table}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    return path

# ---------- 场景生成器 ----------
def business_days(end: datetime, n_days: int) -> List[datetime]:
    days = []
    cur = end - timedelta(days=n_days*2)  # 多取一些，再过滤
    while len(days) < n_days:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            days.append(cur)
    return days

def gen_price_series(trend: str, n: int, start_price: float = 100.0, vol: float = 0.015,
                     shock: Optional[Tuple[int, float]] = None) -> List[float]:
    """
    trend: 'bull'|'bear'|'choppy'|'crash_recover'
    vol: 日收益波动 ~N(0, vol)
    shock: (t_index, magnitude) 例如 (60, -0.15) 表示第60天一次性下跌15%
    """
    price = start_price
    series = []
    drift_map = {
        "bull": 0.0008,
        "bear": -0.0008,
        "choppy": 0.0,
        "crash_recover": 0.0005
    }
    drift = drift_map.get(trend, 0.0)
    for t in range(n):
        eps = random.gauss(0, vol)
        price *= (1.0 + drift + eps)
        if shock and t == shock[0]:
            price *= (1.0 + shock[1])
        price = max(1e-3, price)
        series.append(round(price, 4))
    # crash_recover: 后段提高 drift 模拟修复
    if trend == "crash_recover":
        for i in range(n//3, n):
            series[i] = round(series[i-1] * (1.0 + 0.0015 + random.gauss(0, vol*0.8)), 4)
    return series

POS_WORDS = ["beat", "upgrade", "strong", "record", "positive", "surge", "optimistic", "growth"]
NEG_WORDS = ["miss", "downgrade", "weak", "recall", "negative", "plunge", "concern", "slowdown"]
NEU_WORDS = ["update", "announces", "launch", "report", "conference", "brief"]

def gen_news(symbol: str, dates: List[str], daily_prob=0.3,
             polarity_mix: Tuple[float,float,float]=(0.6,0.3,0.1)) -> Tuple[List[NewsRawRow], List[float]]:
    """返回 (news_rows, daily_sentiment)；情绪先用词典打分代替 LLM（符合里程碑2的简化路径）"""
    pos_p, neu_p, neg_p = polarity_mix
    daily = []
    news_rows = []
    for d in dates:
        todays = []
        if random.random() < daily_prob:
            # 每天 1~3 条
            k = random.choice([1,1,2,2,3])
            for _ in range(k):
                r = random.random()
                if r < pos_p:
                    w = random.choice(POS_WORDS); pol = 1.0
                elif r < pos_p + neg_p:
                    w = random.choice(NEG_WORDS); pol = -1.0
                else:
                    w = random.choice(NEU_WORDS); pol = 0.0
                title = f"{symbol} {w} news on {d}"
                summary = f"{'positive' if pol>0 else ('negative' if pol<0 else 'neutral')} headline {w}"
                todays.append((title, summary, pol))
        # 聚合为当日均值
        if todays:
            sent = sum(p for _,_,p in todays) / len(todays)
        else:
            sent = 0.0
        daily.append(sent)
        for (title, summary, pol) in todays:
            news_rows.append(NewsRawRow(symbol, title, summary, f"https://example.com/{symbol}/{d}", "fixture", d))
    return news_rows, daily

def simple_sentiment_score(text: str) -> float:
    t = text.lower()
    score = 0.0
    score += sum(t.count(x) for x in POS_WORDS) * 1.0
    score -= sum(t.count(x) for x in NEG_WORDS) * 1.0
    # 归一到 [-1,1]
    return max(-1.0, min(1.0, score / 3.0))

# ---------- 主入口：一键造数 ----------
def make_fixtures(symbols: List[SymbolRow],
                  assign_trend: Dict[str, str],
                  sector_bias: Optional[str],
                  days: int = 180,
                  as_of: Optional[str] = None,
                  shock_map: Optional[Dict[str, Tuple[int,float]]] = None,
                  seed: int = 42) -> Dict[str, int]:
    """
    assign_trend: 每个 symbol -> trend ('bull'|'bear'|'choppy'|'crash_recover')
    sector_bias: 行业集中度压力测试（例如 'Technology' 会在候选时占比更高，以测试 RiskManager）
    """
    random.seed(seed)
    as_of = as_of or datetime.utcnow().strftime("%Y-%m-%d")
    conn = get_conn()

    # 1) symbols / fundamentals
    upsert_symbols(conn, symbols)

    # 基本面分层：高质量/中等/较差（价值/质量因子会受此影响；与你的评分契约一致）:contentReference[oaicite:6]{index=6}
    funds = []
    for r in symbols:
        tier = random.random()
        if tier < 0.33:       # 价值&质量较好：低PE/PB，高ROE/净利率
            pe, pb = random.uniform(8,15), random.uniform(1.0,2.5)
            roe, nm = random.uniform(18,28), random.uniform(12,22)
        elif tier < 0.66:     # 中等
            pe, pb = random.uniform(15,25), random.uniform(2.0,4.0)
            roe, nm = random.uniform(10,18), random.uniform(5,12)
        else:                 # 较差
            pe, pb = random.uniform(25,40), random.uniform(3.5,6.0)
            roe, nm = random.uniform(0,10), random.uniform(-5,5)
        mc = random.uniform(10, 800) * 1e9
        funds.append(FundamentalRow(r.symbol, as_of, round(pe,2), round(pb,2), round(roe,2), round(nm,2), round(mc,2)))
    upsert_fundamentals(conn, funds)

    # 2) prices & news
    end = datetime.fromisoformat(as_of)
    dates_dt = business_days(end, days)
    dates = [d.strftime("%Y-%m-%d") for d in dates_dt]

    price_rows: List[PriceRow] = []
    news_raw_rows: List[NewsRawRow] = []
    news_scores_rows: List[NewsScoreRow] = []

    for r in symbols:
        trend = assign_trend.get(r.symbol, "choppy")
        shock = (days//2, -0.15) if trend in ("bear","crash_recover") else None
        shock = shock_map.get(r.symbol) if shock_map and r.symbol in shock_map else shock
        series = gen_price_series(trend, len(dates), start_price=random.uniform(30,200), vol=0.012, shock=shock)
        prev = series[0]
        for d, px in zip(dates, series):
            day_open = round(prev * random.uniform(0.995, 1.005), 4)
            high = round(max(day_open, px) * random.uniform(1.000, 1.006), 4)
            low = round(min(day_open, px) * random.uniform(0.994, 1.000), 4)
            volume = int(random.uniform(2e6, 1.2e7))
            price_rows.append(PriceRow(r.symbol, d, day_open, high, low, px, px, volume))
            prev = px

        # 新闻与情绪（先用词典分，符合里程碑2“可运行最小化”）:contentReference[oaicite:7]{index=7}
        mix = (0.6, 0.3, 0.1) if trend!="bear" else (0.3, 0.3, 0.4)
        raw_rows, _daily = gen_news(r.symbol, dates[-30:], daily_prob=0.5, polarity_mix=mix)
        ids = insert_news(conn, raw_rows)
        # 将每条新闻打分至 news_scores
        for nid, raw in zip(ids, raw_rows):
            s = simple_sentiment_score(raw.title + " " + raw.summary)
            news_scores_rows.append(NewsScoreRow(nid, s, "fixture"))

    # 入库（批量）
    upsert_prices(conn, price_rows)
    insert_news_scores(conn, news_scores_rows)
    conn.commit()

    # 3) 导出 CSV（便于审查 / 可视化联调）
    exported = {}
    for t in ("symbols","fundamentals","prices_daily","news_raw","news_scores"):
        exported[t] = export_csv(t, conn)

    return {
        "symbols": len(symbols),
        "prices_rows": len(price_rows),
        "news_rows": len(news_scores_rows),
    }

# ---------- 预置股票池（跨行业，覆盖风控与行业集中度场景） ----------
DEFAULT_POOL: List[SymbolRow] = [
    SymbolRow("AAPL","Apple","NASDAQ","Technology","Consumer Electronics"),
    SymbolRow("MSFT","Microsoft","NASDAQ","Technology","Software"),
    SymbolRow("NVDA","NVIDIA","NASDAQ","Technology","Semiconductors"),
    SymbolRow("AMZN","Amazon","NASDAQ","Consumer Discretionary","Internet Retail"),
    SymbolRow("META","Meta","NASDAQ","Communication Services","Interactive Media"),
    SymbolRow("GOOGL","Alphabet","NASDAQ","Communication Services","Search & Ads"),
    SymbolRow("JPM","JPMorgan","NYSE","Financials","Banks"),
    SymbolRow("XOM","ExxonMobil","NYSE","Energy","Oil & Gas"),
    SymbolRow("NEE","NextEra","NYSE","Utilities","Electric Utilities"),
    SymbolRow("PG","Procter & Gamble","NYSE","Consumer Staples","Household"),
    SymbolRow("CAT","Caterpillar","NYSE","Industrials","Machinery"),
    SymbolRow("HD","Home Depot","NYSE","Consumer Discretionary","Home Improvement")
]
