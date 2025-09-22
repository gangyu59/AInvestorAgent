"""
用法示例：
  python -m scripts.fetch_prices AAPL MSFT
  # 或读取 seeds/init_symbols.csv
"""
import csv
import sys
from pathlib import Path
from backend.storage.db import SessionLocal
from backend.storage.models import Base
from backend.ingestion.loaders import load_daily_from_alpha
from backend.storage.dao import record_run
from backend.storage.db import engine
import time
from backend.ingestion.alpha_vantage_client import AlphaVantageError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def iter_seed_symbols():
    p = Path(__file__).resolve().parents[1] / "backend" / "storage" / "seeds" / "init_symbols.csv"
    if p.exists():
        with p.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                s = (row.get("symbol") or "").strip()
                if s:
                    yield s

def main(symbols):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not symbols:
            symbols = list(iter_seed_symbols())
        for sym in symbols:
            try:
                # 先尝试 ADJUSTED
                n = load_daily_from_alpha(db, sym, adjusted=True, outputsize="compact")
                print(f"[OK] {sym}: {n} rows upserted (adjusted)")
            except AlphaVantageError as e:
                msg = str(e)
                # 碰到 ADJUSTED 的 Invalid API call → 自动降级到 DAILY
                if "TIME_SERIES_DAILY_ADJUSTED" in msg or "Invalid API call" in msg:
                    print(f"[WARN] {sym}: adjusted 不可用，降级为 DAILY")
                    try:
                        n = load_daily_from_alpha(db, sym, adjusted=False, outputsize="compact")
                        print(f"[OK] {sym}: {n} rows upserted (daily)")
                    except Exception as e2:
                        print(f"[ERROR] {sym}: DAILY 拉取失败 -> {e2}")
                else:
                    print(f"[ERROR] {sym}: {e}")
            # 轻微限速，规避 5 calls/min 限制
            time.sleep(13)
        db.commit()
    except Exception as e:
        db.rollback()
        print("[ERROR]", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    syms = [s.strip() for s in sys.argv[1:]]  # 支持多代码
    main(syms)
