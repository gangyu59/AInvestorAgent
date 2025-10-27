#!/usr/bin/env python3
"""
智能批量更新路由 - 增强版
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import subprocess
import time
import logging

from backend.storage.db import get_db
from backend.storage.models import PriceDaily
from backend.ingestion.loaders import load_daily_from_alpha
from backend.ingestion.alpha_vantage_client import AlphaVantageError

# 使用标准Python logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])


# ========== 原有Schema（保持兼容）==========
class BatchUpdateRequest(BaseModel):
    symbols: List[str]
    fetch_prices: bool = True
    fetch_fundamentals: bool = False
    fetch_news: bool = True
    rebuild_factors: bool = True
    recompute_scores: bool = True
    days: int = 7
    pages: int = 2


# ========== 新增Schema（智能模式）==========
class SmartUpdateRequest(BaseModel):
    symbols: List[str]
    force_full: bool = False
    update_prices: bool = True
    update_news: bool = True
    update_fundamentals: bool = False
    auto_factors: bool = True
    auto_scores: bool = True


class StockUpdateResult(BaseModel):
    symbol: str
    success: bool
    prices_added: int = 0
    news_added: int = 0
    error: Optional[str] = None
    mode: str = "compact"
    before_count: int = 0
    after_count: int = 0
    duration_seconds: float = 0


class SmartUpdateResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: List[StockUpdateResult]
    duration_seconds: float
    factors_rebuilt: bool = False
    scores_computed: bool = False


# ========== 数据检测逻辑 ==========
def check_data_coverage(db: Session, symbol: str) -> dict:
    """检查数据覆盖情况"""
    count = db.query(PriceDaily).filter(PriceDaily.symbol == symbol).count()

    if count == 0:
        return {
            "count": 0,
            "status": "empty",
            "needs_full": True,
            "reason": "无数据"
        }

    first = db.query(PriceDaily).filter(
        PriceDaily.symbol == symbol
    ).order_by(PriceDaily.date.asc()).first()

    last = db.query(PriceDaily).filter(
        PriceDaily.symbol == symbol
    ).order_by(PriceDaily.date.desc()).first()

    needs_full = False
    reason = "数据充足"

    if count < 200:
        needs_full = True
        reason = f"数据点不足200(当前{count})"
    elif first and (datetime.now().date() - first.date).days < 730:
        needs_full = True
        reason = "历史数据不足2年"

    return {
        "count": count,
        "first_date": str(first.date) if first else None,
        "last_date": str(last.date) if last else None,
        "needs_full": needs_full,
        "reason": reason,
        "status": "insufficient" if needs_full else "sufficient"
    }


def fetch_prices_smart(db: Session, symbol: str, force_full: bool = False) -> StockUpdateResult:
    """智能拉取价格数据"""
    result = StockUpdateResult(symbol=symbol, success=False)
    start_time = time.time()

    try:
        coverage = check_data_coverage(db, symbol)
        result.before_count = coverage["count"]

        use_full = force_full or coverage["needs_full"]
        result.mode = "full" if use_full else "compact"

        logger.info(
            f"📊 {symbol}: 现有{coverage['count']}条, "
            f"模式={result.mode}, 原因={coverage['reason']}"
        )

        try:
            n = load_daily_from_alpha(
                db,
                symbol,
                adjusted=True,
                outputsize="full" if use_full else "compact"
            )
            result.prices_added = n
            result.success = True
            logger.info(f"✅ {symbol}: 成功添加{n}条(adjusted)")

        except AlphaVantageError as e:
            error_str = str(e)
            if "TIME_SERIES_DAILY_ADJUSTED" in error_str or "Invalid API call" in error_str:
                logger.warning(f"⚠️ {symbol}: ADJUSTED不可用,降级到DAILY")
                n = load_daily_from_alpha(
                    db,
                    symbol,
                    adjusted=False,
                    outputsize="full" if use_full else "compact"
                )
                result.prices_added = n
                result.success = True
                logger.info(f"✅ {symbol}: 成功添加{n}条(daily)")
            else:
                raise

        db.commit()
        result.after_count = db.query(PriceDaily).filter(
            PriceDaily.symbol == symbol
        ).count()

    except Exception as e:
        db.rollback()
        result.error = str(e)
        logger.error(f"❌ {symbol}: {e}")

    result.duration_seconds = time.time() - start_time
    return result


# ========== 原有API端点（保持兼容）==========
@router.post("/update_all")
async def batch_update(req: BatchUpdateRequest):
    """一键更新：价格→基本面→新闻→因子→评分（原有方式）"""
    symbols_str = ",".join(req.symbols)
    results = {}

    try:
        if req.fetch_prices:
            logger.info(f"📊 拉取价格: {symbols_str}")
            result = subprocess.run(
                ["python", "-m", "scripts.fetch_prices"] + req.symbols,
                capture_output=True, text=True, timeout=120
            )
            results["prices"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"
            if result.returncode != 0:
                results["prices_error"] = result.stderr

        if req.fetch_news:
            logger.info(f"📰 拉取新闻: {symbols_str}")
            result = subprocess.run(
                ["python", "scripts/fetch_news.py",
                 "--symbols", symbols_str,
                 "--days", str(req.days),
                 "--pages", str(req.pages),
                 "--noproxy"],
                capture_output=True, text=True, timeout=300
            )
            results["news"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"
            if result.returncode != 0:
                results["news_error"] = result.stderr

        if req.rebuild_factors:
            logger.info(f"🧮 重建因子: {symbols_str}")
            result = subprocess.run(
                ["python", "scripts/rebuild_factors.py",
                 "--symbols", symbols_str],
                capture_output=True, text=True, timeout=120
            )
            results["factors"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"
            if result.returncode != 0:
                results["factors_error"] = result.stderr

        if req.recompute_scores:
            logger.info(f"⭐ 重算评分: {symbols_str}")
            result = subprocess.run(
                ["python", "scripts/recompute_scores.py",
                 "--symbols", symbols_str],
                capture_output=True, text=True, timeout=120
            )
            results["scores"] = "✅ 成功" if result.returncode == 0 else "❌ 失败"
            if result.returncode != 0:
                results["scores_error"] = result.stderr

        return {"status": "success", "results": results}

    except Exception as e:
        logger.error(f"❌ 批量更新失败: {e}")
        raise HTTPException(500, f"批量更新失败: {str(e)}")


# ========== 新增API端点（智能模式）==========
@router.post("/update", response_model=SmartUpdateResponse)
async def smart_update(
        request: SmartUpdateRequest,
        db: Session = Depends(get_db)
):
    """智能批量更新（新方式）"""
    start_time = time.time()
    results = []

    logger.info(f"🚀 智能更新开始: {len(request.symbols)}只股票")
    logger.info(f"   force_full={request.force_full}")

    if request.update_prices:
        for i, symbol in enumerate(request.symbols, 1):
            logger.info(f"\n[{i}/{len(request.symbols)}] 处理 {symbol}")

            result = fetch_prices_smart(db, symbol, request.force_full)
            results.append(result)

            if i < len(request.symbols):
                wait_seconds = 15
                logger.info(f"⏱️ 等待{wait_seconds}秒...")
                time.sleep(wait_seconds)

    # 🆕 新闻抓取和打分
    if request.update_news:
        try:
            logger.info("📰 抓取和打分新闻...")
            symbols_str = ",".join(request.symbols)
            result = subprocess.run(
                ["python", "scripts/fetch_news.py",
                 "--symbols", symbols_str,
                 "--days", "30",
                 "--pages", "2"],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                logger.info(f"✅ 新闻更新完成")
            else:
                logger.warning(f"⚠️ 新闻更新失败: {result.stderr}")
        except Exception as e:
            logger.error(f"新闻更新异常: {e}")

    factors_rebuilt = False
    if request.auto_factors and any(r.success for r in results):
        try:
            logger.info("🧮 自动重建因子...")
            symbols_str = ",".join(request.symbols)
            result = subprocess.run(
                ["python", "scripts/rebuild_factors.py",
                 "--symbols", symbols_str],
                capture_output=True, text=True, timeout=120
            )
            factors_rebuilt = result.returncode == 0
        except Exception as e:
            logger.error(f"因子重建失败: {e}")

    scores_computed = False
    if request.auto_scores and factors_rebuilt:
        try:
            logger.info("⭐ 自动重算评分...")
            symbols_str = ",".join(request.symbols)
            result = subprocess.run(
                ["python", "scripts/recompute_scores.py",
                 "--symbols", symbols_str],
                capture_output=True, text=True, timeout=120
            )
            scores_computed = result.returncode == 0
        except Exception as e:
            logger.error(f"评分重算失败: {e}")

    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count
    duration = time.time() - start_time

    logger.info(
        f"\n✅ 更新完成: 成功{success_count}/{len(results)}, "
        f"耗时{duration:.1f}秒"
    )

    return SmartUpdateResponse(
        total=len(results),
        success=success_count,
        failed=failed_count,
        results=results,
        duration_seconds=duration,
        factors_rebuilt=factors_rebuilt,
        scores_computed=scores_computed
    )


@router.get("/coverage")
async def check_coverage(
        symbols: str,
        db: Session = Depends(get_db)
):
    """检查数据覆盖情况"""
    symbol_list = [s.strip().upper() for s in symbols.split(',')]

    results = []
    for symbol in symbol_list:
        coverage = check_data_coverage(db, symbol)
        results.append({
            "symbol": symbol,
            **coverage
        })

    return {"symbols": results}


@router.post("/rebuild_factors")
async def rebuild_factors_endpoint(symbols: List[str]):
    """单独重建因子"""
    try:
        symbols_str = ",".join(symbols)
        result = subprocess.run(
            ["python", "scripts/rebuild_factors.py", "--symbols", symbols_str],
            capture_output=True, text=True, timeout=120
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/recompute_scores")
async def recompute_scores_endpoint(symbols: List[str]):
    """单独重算评分"""
    try:
        symbols_str = ",".join(symbols)
        result = subprocess.run(
            ["python", "scripts/recompute_scores.py", "--symbols", symbols_str],
            capture_output=True, text=True, timeout=120
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        raise HTTPException(500, str(e))