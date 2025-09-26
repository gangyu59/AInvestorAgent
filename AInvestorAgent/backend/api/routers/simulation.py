# backend/api/routers/simulation.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.simulation.trading_engine import trading_engine
from datetime import date

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class TradeRequest(BaseModel):
    symbol: str
    action: str  # BUY/SELL
    quantity: float
    price: Optional[float] = None


class ExecuteDecisionRequest(BaseModel):
    holdings: List[dict]  # [{"symbol": "AAPL", "weight": 0.3}, ...]
    total_amount: Optional[float] = None


@router.post("/trade")
async def execute_trade(req: TradeRequest):
    """执行单笔交易"""
    try:
        result = trading_engine.execute_trade(
            symbol=req.symbol.upper(),
            action=req.action.upper(),
            quantity=req.quantity,
            price=req.price,
            source="MANUAL"
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portfolio")
async def get_portfolio():
    """获取投资组合状态"""
    try:
        status = trading_engine.get_portfolio_status()
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-decision")
async def execute_decision(req: ExecuteDecisionRequest):
    """执行投资决策（自动调仓）"""
    try:
        # 获取当前持仓
        current_status = trading_engine.get_portfolio_status()
        current_holdings = {h["symbol"]: h["quantity"] for h in current_status["holdings"]}
        total_value = req.total_amount or current_status["total_value"]

        trades_executed = []

        # 计算目标持仓
        target_holdings = {}
        for holding in req.holdings:
            symbol = holding["symbol"].upper()
            weight = holding["weight"]
            target_value = total_value * weight

            # 简化：假设当前价格执行
            try:
                from backend.ingestion.alpha_vantage_client import get_latest_price
                current_price = get_latest_price(symbol)
                target_quantity = target_value / current_price
                target_holdings[symbol] = target_quantity
            except Exception as e:
                continue

        # 执行调仓交易
        for symbol, target_qty in target_holdings.items():
            current_qty = current_holdings.get(symbol, 0)
            diff = target_qty - current_qty

            if abs(diff) > 0.01:  # 忽略微小差异
                action = "BUY" if diff > 0 else "SELL"
                quantity = abs(diff)

                try:
                    trade = trading_engine.execute_trade(
                        symbol=symbol,
                        action=action,
                        quantity=quantity,
                        source="AUTO"
                    )
                    trades_executed.append(trade)
                except Exception as e:
                    continue

        return {
            "success": True,
            "data": {
                "trades_executed": trades_executed,
                "portfolio_status": trading_engine.get_portfolio_status()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pnl")
async def get_daily_pnl(days: int = 30):
    """获取每日P&L历史"""
    try:
        from backend.storage.db import engine
        from backend.storage.models import SimDailyPnL
        from sqlalchemy.orm import Session

        with Session(engine) as db:
            records = db.query(SimDailyPnL).filter_by(
                account_id="default"
            ).order_by(SimDailyPnL.trade_date.desc()).limit(days).all()

            data = []
            for record in reversed(records):
                data.append({
                    "date": record.trade_date,
                    "total_value": record.total_value,
                    "daily_pnl": record.daily_pnl,
                    "return_pct": record.return_pct,
                    "cumulative_pnl": record.cumulative_pnl
                })

        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-pnl")
async def calculate_pnl():
    """手动计算今日P&L"""
    try:
        result = trading_engine.calculate_daily_pnl()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))