# backend/api/routers/simulation.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.simulation.trading_engine import trading_engine
from datetime import date, datetime, timedelta
import sys
import os

# 添加路径以导入历史回测模拟器
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


class TradeRequest(BaseModel):
    symbol: str
    action: str  # BUY/SELL
    quantity: float
    price: Optional[float] = None


class ExecuteDecisionRequest(BaseModel):
    holdings: List[dict]  # [{"symbol": "AAPL", "weight": 0.3}, ...]
    total_amount: Optional[float] = None


# 🆕 历史回测请求模型
class HistoricalBacktestRequest(BaseModel):
    watchlist: List[str]
    initialCapital: float = 100000.0
    startDate: str = None  # "2024-01-01"
    endDate: str = None
    rebalanceFrequency: str = "W-MON"  # 每周一
    minScore: float = 50.0


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
    """执行投资决策(自动调仓)"""
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

            # 简化:假设当前价格执行
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


# 🆕 历史回测模拟端点
@router.post("/historical-backtest")
async def run_historical_backtest(req: HistoricalBacktestRequest):
    """
    运行历史回测模拟

    使用历史数据模拟Paper Trading,验证策略有效性
    """
    try:
        print(f"🎯 启动历史回测模拟")
        print(f"📋 股票池: {req.watchlist}")
        print(f"💰 初始资金: ${req.initialCapital:,.2f}")
        print(f"📅 回测期间: {req.startDate} → {req.endDate}")

        # 动态导入历史回测模拟器
        try:
            from scripts.historical_backtest_simulator import HistoricalBacktestSimulator
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="无法导入历史回测模拟器。请确保 scripts/historical_backtest_simulator.py 存在。"
            )

        # 设置日期范围
        end_date = req.endDate if req.endDate else datetime.now().strftime("%Y-%m-%d")
        start_date = req.startDate if req.startDate else (
                datetime.now() - timedelta(days=365)
        ).strftime("%Y-%m-%d")

        # 创建模拟器实例
        simulator = HistoricalBacktestSimulator(
            watchlist=req.watchlist,
            initial_capital=req.initialCapital,
            start_date=start_date,
            end_date=end_date
        )

        # 运行回测
        print("🚀 开始执行历史回测...")
        simulator.run_backtest(rebalance_frequency=req.rebalanceFrequency)

        # 构建返回数据
        history_data = []
        for record in simulator.history:
            history_data.append({
                "date": record["date"].strftime("%Y-%m-%d") if isinstance(record["date"], date) else record["date"],
                "nav": round(record["nav"], 4),
                "totalValue": round(record["total_value"], 2),
                "cash": round(record["cash"], 2),
                "holdings": round(record["total_value"] - record["cash"], 2),
                "positions": record["positions"],
                "drawdown": round((record["nav"] - max(
                    [h["nav"] for h in simulator.history[:simulator.history.index(record) + 1]])) / max(
                    [h["nav"] for h in
                     simulator.history[:simulator.history.index(record) + 1]]) * 100 if simulator.history.index(
                    record) > 0 else 0, 2)
            })

        # 构建交易数据
        trades_data = []
        for trade in simulator.trades:
            trades_data.append({
                "date": trade["date"].strftime("%Y-%m-%d") if isinstance(trade["date"], date) else trade["date"],
                "symbol": trade["symbol"],
                "action": trade["action"],
                "shares": trade["shares"],
                "price": f"{trade['price']:.2f}",
                "value": f"{trade['value']:.2f}",
                "reason": f"评分变化触发 - {trade['action']}操作"
            })

        # 计算指标
        if len(history_data) > 0:
            final_nav = history_data[-1]["nav"]
            initial_nav = history_data[0]["nav"]
            total_return = (final_nav - initial_nav) / initial_nav * 100

            # 年化收益
            days = len(history_data)
            ann_return = (pow(final_nav, 365 / max(days, 1)) - 1) * 100

            # 最大回撤
            max_dd = min([h["drawdown"] for h in history_data])

            # 计算夏普比率
            returns = []
            for i in range(1, len(history_data)):
                daily_return = (history_data[i]["nav"] - history_data[i - 1]["nav"]) / history_data[i - 1]["nav"]
                returns.append(daily_return)

            if len(returns) > 0:
                avg_return = sum(returns) / len(returns)
                variance = sum([(r - avg_return) ** 2 for r in returns]) / len(returns)
                std_return = variance ** 0.5
                sharpe = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
            else:
                sharpe = 0

            # 胜率
            win_rate = len([r for r in returns if r > 0]) / len(returns) * 100 if len(returns) > 0 else 0
            win_trades = len([t for t in trades_data if t["action"] == "BUY"])

            metrics = {
                "totalReturn": round(total_return, 2),
                "annReturn": round(ann_return, 2),
                "maxDrawdown": round(max_dd, 2),
                "sharpe": round(sharpe, 3),
                "winRate": round(win_rate, 1),
                "totalTrades": len(trades_data),
                "winTrades": win_trades,
                "avgHoldings": round(sum([h["positions"] for h in history_data]) / len(history_data), 1)
            }
        else:
            metrics = {
                "totalReturn": 0,
                "annReturn": 0,
                "maxDrawdown": 0,
                "sharpe": 0,
                "winRate": 0,
                "totalTrades": 0,
                "winTrades": 0,
                "avgHoldings": 0
            }

        print("✅ 历史回测完成")
        print(f"📊 总收益: {metrics['totalReturn']:.2f}%")
        print(f"📈 年化收益: {metrics['annReturn']:.2f}%")
        print(f"📉 最大回撤: {metrics['maxDrawdown']:.2f}%")
        print(f"⚖️ 夏普比率: {metrics['sharpe']:.3f}")

        return {
            "success": True,
            "data": {
                "history": history_data,
                "trades": trades_data,
                "metrics": metrics,
                "config": {
                    "watchlist": req.watchlist,
                    "initialCapital": req.initialCapital,
                    "startDate": start_date,
                    "endDate": end_date,
                    "rebalanceFrequency": req.rebalanceFrequency
                }
            }
        }

    except Exception as e:
        import traceback
        print(f"❌ 历史回测失败: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"历史回测执行失败: {str(e)}"
        )