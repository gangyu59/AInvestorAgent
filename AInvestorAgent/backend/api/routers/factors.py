# backend/api/routes/factors.py
from fastapi import APIRouter
from datetime import date
from backend.storage.db import SessionLocal
from backend.scoring.scorer import compute_factors, upsert_scores

router = APIRouter(prefix="/api/factors", tags=["factors"])


@router.post("/rebuild")
def rebuild_factors(req: dict):
    """重建因子数据"""
    symbols = req.get("symbols", [])
    as_of_str = req.get("as_of", date.today().isoformat())
    as_of = date.fromisoformat(as_of_str)

    print(f"🔧 API调用: 重建因子 {symbols}, as_of={as_of}")

    try:
        with SessionLocal() as db:
            rows = compute_factors(db, symbols, as_of)
            if rows:
                upsert_scores(db, as_of, rows, version_tag="v0.1")
                print(f"✅ 因子重建成功: {len(rows)}个")
                return {
                    "success": len(rows),
                    "symbols": [r.symbol for r in rows],
                    "message": f"成功计算{len(rows)}个股票的因子"
                }
            else:
                return {"success": 0, "message": "没有可计算的数据"}
    except Exception as e:
        print(f"❌ 因子计算失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": 0, "error": str(e), "message": "因子计算失败"}