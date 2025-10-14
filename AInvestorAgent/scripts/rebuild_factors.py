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

        try:
            rows = compute_factors(s, symbols, asof)  # ← 传入整个列表
            if not rows:
                print(f"  ⚠️ 无可计算数据")
            else:
                # 批量入库
                if upsert_factors:
                    upsert_factors(s, asof, rows)

                # 显示结果
                for r in rows:
                    print(f"  ✅ {r.symbol}: "
                          f"f_value={r.f_value:.3f} "
                          f"f_quality={r.f_quality:.3f} "
                          f"f_momentum={r.f_momentum:.3f} "
                          f"f_sentiment={r.f_sentiment:.3f}")
        except Exception as e:
            print(f"  ❌ 计算失败: {e}")

        print(f"完成")

if __name__ == "__main__":
    sys.exit(main())
