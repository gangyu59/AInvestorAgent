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
            n = load_daily_from_alpha(db, sym, adjusted=True, outputsize="compact")
            record_run(db, f"fetch_daily:{sym.upper()}")
            print(f"[OK] {sym}: {n} rows upserted")
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
