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

        # 修改后：批量处理所有股票
        try:
            # ⭐ 一次性计算所有股票的因子
            rows = compute_factors(s, symbols, asof)

            if not rows:
                print(f"  ⚠️ 无可计算数据")
            else:
                # 批量写入评分
                for r in rows:
                    total = float(aggregate_score(r))
                    setattr(r, "score", total)
                    print(f"  ✅ {r.symbol}: score={total:.1f}")

                # 批量入库
                upsert_scores(s, asof, rows, version_tag=version_tag)
                print(f"完成：{len(rows)}/{len(symbols)}")

        except Exception as e:
            print(f"  ❌ 批量计算失败: {e}")

        print(f"\n✅ 所有股票评分已更新")

if __name__ == "__main__":
    sys.exit(main())
