from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
from typing import List

router = APIRouter(prefix="/api/batch", tags=["batch"])


class BatchUpdateRequest(BaseModel):
    symbols: List[str]
    fetch_prices: bool = True
    fetch_fundamentals: bool = False
    fetch_news: bool = True
    rebuild_factors: bool = True
    recompute_scores: bool = True
    days: int = 7
    pages: int = 2


@router.post("/update_all")
async def batch_update(req: BatchUpdateRequest):
    """一键更新：价格→基本面→新闻→因子→评分"""

    symbols_str = ",".join(req.symbols)
    results = {}

    try:
        # 1. 价格
        if req.fetch_prices:
            result = subprocess.run(
                ["python", "-m", "scripts.fetch_prices"] + req.symbols,
                capture_output=True, text=True, timeout=120
            )
            results["prices"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"

        # 2. 新闻
        if req.fetch_news:
            result = subprocess.run(
                ["python", "scripts/fetch_news.py", "--symbols", symbols_str,
                 "--days", str(req.days), "--pages", str(req.pages), "--noproxy"],
                capture_output=True, text=True, timeout=300
            )
            results["news"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"

        # 3. 因子
        if req.rebuild_factors:
            result = subprocess.run(
                ["python", "scripts/rebuild_factors.py", "--symbols", symbols_str],
                capture_output=True, text=True, timeout=120
            )
            results["factors"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"

        # 4. 评分
        if req.recompute_scores:
            result = subprocess.run(
                ["python", "scripts/recompute_scores.py", "--symbols", symbols_str],
                capture_output=True, text=True, timeout=120
            )
            results["scores"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"

        return {"status": "success", "results": results}

    except Exception as e:
        raise HTTPException(500, f"批量更新失败: {str(e)}")