# scripts/rebuild_factors.py
from __future__ import annotations
from pathlib import Path
import sys
from datetime import date
from typing import List

# --- 让 import backend.* 在任何路径下都能工作 ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.storage.db import SessionLocal
from backend.storage import dao  # 你已有 dao 封装
from backend.scoring.scorer import compute_factors  # 你已有
# 某些代码库会有 upsert_factors；若无，则兼容跳过
try:
    from backend.scoring.scorer import upsert_factors  # 可选
except Exception:
    upsert_factors = None  # type: ignore


def _default_symbols(session) -> List[str]:
    # 优先从已有表/快照中取常见大票；没有的话，用一个内置列表兜底
    try:
        syms = dao.get_popular_symbols(session)  # 如果你 dao 里有这个函数
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

        total = 0
        for sym in symbols:
            try:
                rows = compute_factors(s, [sym], asof, mock=False)
                if not rows:
                    print(f"  ⚠️ {sym}: 无可计算数据")
                    continue
                if upsert_factors:
                    upsert_factors(s, asof, rows)  # 存入 factors_daily（若你实现了）
                total += 1
                r = rows[0]
                print(f"  ✅ {sym}: f_value={getattr(r,'f_value',None)} "
                      f"f_quality={getattr(r,'f_quality',None)} "
                      f"f_momentum={getattr(r,'f_momentum',None)} "
                      f"f_sentiment={getattr(r,'f_sentiment',None)}")
            except Exception as e:
                print(f"  ❌ {sym}: {e}")

        print(f"完成：{total}/{len(symbols)}")

if __name__ == "__main__":
    sys.exit(main())
