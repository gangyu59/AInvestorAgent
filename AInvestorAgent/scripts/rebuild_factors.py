# scripts/rebuild_factors.py
from __future__ import annotations
from pathlib import Path
import sys
from datetime import date
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.storage.db import SessionLocal
from backend.storage import dao
from backend.scoring.scorer import compute_factors

try:
    from backend.scoring.scorer import upsert_factors  # 可选
except Exception:
    upsert_factors = None  # type: ignore

def _default_symbols(session) -> List[str]:
    try:
        syms = dao.get_popular_symbols(session)  # 若无此函数会走 except
        if syms:
            return syms
    except Exception:
        pass
    return ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","AVGO","ADBE"]

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="重算并（可选）入库因子")
    ap.add_argument("--symbols", type=str, default="AAPL,MSFT,NVDA,AMZN,GOOGL",
                    help='逗号分隔；传 "all" 则自动读取常用清单')
    ap.add_argument("--asof", type=str, default=date.today().isoformat())
    args = ap.parse_args(argv)

    asof = date.fromisoformat(args.asof)

    with SessionLocal() as s:
        if args.symbols.strip().lower() == "all":
            symbols = _default_symbols(s)
        else:
            symbols = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
        print(f"🔧 重建因子 as_of={asof} symbols={symbols}")

        done = 0
        for sym in symbols:
            try:
                rows = compute_factors(s, [sym], asof)  # ✅ 去掉 mock=
                if not rows:
                    print(f"  ⚠️ {sym}: 无可计算数据")
                    continue
                if upsert_factors:
                    upsert_factors(s, asof, rows)
                r = rows[0]
                print(f"  ✅ {sym}: "
                      f"f_value={getattr(r,'f_value',None)} "
                      f"f_quality={getattr(r,'f_quality',None)} "
                      f"f_momentum={getattr(r,'f_momentum',None)} "
                      f"f_sentiment={getattr(r,'f_sentiment',None)}")
                done += 1
            except Exception as e:
                print(f"  ❌ {sym}: {e}")

        print(f"完成：{done}/{len(symbols)}")

if __name__ == "__main__":
    sys.exit(main())
