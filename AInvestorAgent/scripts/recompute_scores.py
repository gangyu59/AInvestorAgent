# scripts/recompute_scores.py
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
from backend.scoring.scorer import compute_factors, aggregate_score, upsert_scores

def _default_symbols(session) -> List[str]:
    try:
        syms = dao.get_popular_symbols(session)
        if syms:
            return syms
    except Exception:
        pass
    return ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","AVGO","ADBE"]

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="重算综合评分并入库")
    ap.add_argument("--symbols", type=str, default="AAPL,MSFT,NVDA,AMZN,GOOGL",
                    help='逗号分隔；传 "all" 则自动读取常用清单')
    ap.add_argument("--asof", type=str, default=date.today().isoformat())
    ap.add_argument("--version", type=str, default="v1.0.0")
    args = ap.parse_args(argv)

    asof = date.fromisoformat(args.asof)
    version_tag = args.version

    with SessionLocal() as s:
        if args.symbols.strip().lower() == "all":
            symbols = _default_symbols(s)
        else:
            symbols = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
        print(f"🧮 重算评分 as_of={asof} version={version_tag} symbols={symbols}")

        done = 0
        for sym in symbols:
            try:
                rows = compute_factors(s, [sym], asof)  # ✅ 去掉 mock=
                if not rows:
                    print(f"  ⚠️ {sym}: 无因子")
                    continue
                r = rows[0]
                total = float(aggregate_score(r))  # 0–100
                setattr(r, "score", total)         # 与 upsert_scores 约定一致
                upsert_scores(s, asof, [r], version_tag=version_tag)
                print(f"  ✅ {sym}: score={total:.1f}")
                done += 1
            except Exception as e:
                print(f"  ❌ {sym}: {e}")

        print(f"完成：{done}/{len(symbols)}")

if __name__ == "__main__":
    sys.exit(main())
