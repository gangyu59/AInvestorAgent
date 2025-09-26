# backend/simulation/trading_engine.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from backend.storage.models import SimAccount, SimPosition, SimTrade, SimDailyPnL
from backend.storage.db import engine
from backend.ingestion.alpha_vantage_client import get_prices_for_symbol
import logging

logger = logging.getLogger(__name__)


class TradingEngine:
    """模拟交易引擎"""

    def __init__(self, account_id: str = "default"):
        self.account_id = account_id

    def get_or_create_account(self, initial_cash: float = 100000.0) -> SimAccount:
        """获取或创建模拟账户"""
        with Session(engine) as db:
            account = db.query(SimAccount).filter_by(account_id=self.account_id).first()
            if not account:
                account = SimAccount(
                    account_id=self.account_id,
                    account_name=f"模拟账户 {self.account_id}",
                    initial_cash=initial_cash,
                    current_cash=initial_cash,
                    total_value=initial_cash
                )
                db.add(account)
                db.commit()
                db.refresh(account)
            return account

    def _get_latest_price(self, symbol: str) -> float:
        """获取股票最新价格"""
        try:
            prices = get_prices_for_symbol(symbol, limit=1)
            if prices and len(prices) > 0:
                return float(prices[-1]["close"])
            else:
                raise ValueError(f"无法获取 {symbol} 的价格数据")
        except Exception as e:
            logger.error(f"获取 {symbol} 价格失败: {e}")
            raise ValueError(f"无法获取 {symbol} 的当前价格")

    def execute_trade(self, symbol: str, action: str, quantity: float,
                      price: Optional[float] = None, source: str = "MANUAL") -> Dict:
        """执行交易"""
        if action not in ["BUY", "SELL"]:
            raise ValueError("Action must be BUY or SELL")

        # 获取最新价格
        if price is None:
            price = self._get_latest_price(symbol)

        total_amount = quantity * price
        commission = total_amount * 0.001  # 0.1% 手续费

        with Session(engine) as db:
            account = self.get_or_create_account()

            if action == "BUY":
                # 检查现金是否足够
                if account.current_cash < (total_amount + commission):
                    raise ValueError("现金不足")

                # 更新现金
                account.current_cash -= (total_amount + commission)

                # 更新持仓
                position = db.query(SimPosition).filter_by(
                    account_id=self.account_id, symbol=symbol
                ).first()

                if position:
                    # 计算新的平均成本
                    total_cost = position.quantity * position.avg_cost + total_amount
                    position.quantity += quantity
                    position.avg_cost = total_cost / position.quantity if position.quantity > 0 else price
                else:
                    # 创建新持仓
                    position = SimPosition(
                        account_id=self.account_id,
                        symbol=symbol,
                        quantity=quantity,
                        avg_cost=price
                    )
                    db.add(position)

            elif action == "SELL":
                # 检查持仓是否足够
                position = db.query(SimPosition).filter_by(
                    account_id=self.account_id, symbol=symbol
                ).first()

                if not position or position.quantity < quantity:
                    raise ValueError("持仓不足")

                # 更新持仓
                position.quantity -= quantity

                # 更新现金
                account.current_cash += (total_amount - commission)

                # 如果持仓为0，删除记录
                if position.quantity <= 0:
                    db.delete(position)

            # 记录交易
            trade = SimTrade(
                account_id=self.account_id,
                symbol=symbol,
                action=action,
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                commission=commission,
                source=source
            )
            db.add(trade)

            db.commit()

            return {
                "trade_id": trade.trade_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "price": price,
                "total_amount": total_amount,
                "commission": commission,
                "status": "FILLED"
            }

    def get_portfolio_status(self) -> Dict:
        """获取投资组合状态"""
        with Session(engine) as db:
            account = self.get_or_create_account()
            positions = db.query(SimPosition).filter_by(account_id=self.account_id).all()

            portfolio_value = account.current_cash
            holdings = []

            for pos in positions:
                try:
                    current_price = self._get_latest_price(pos.symbol)
                    market_value = pos.quantity * current_price
                    unrealized_pnl = market_value - (pos.quantity * pos.avg_cost)

                    # 更新持仓市值
                    pos.market_value = market_value
                    pos.unrealized_pnl = unrealized_pnl

                    portfolio_value += market_value

                    holdings.append({
                        "symbol": pos.symbol,
                        "quantity": pos.quantity,
                        "avg_cost": pos.avg_cost,
                        "current_price": current_price,
                        "market_value": market_value,
                        "unrealized_pnl": unrealized_pnl,
                        "weight": 0  # 稍后计算
                    })
                except Exception as e:
                    logger.warning(f"获取 {pos.symbol} 价格失败: {e}")

            # 计算权重
            for holding in holdings:
                holding["weight"] = holding["market_value"] / portfolio_value if portfolio_value > 0 else 0

            # 更新账户总价值
            account.total_value = portfolio_value
            db.commit()

            return {
                "account_id": self.account_id,
                "total_value": portfolio_value,
                "cash": account.current_cash,
                "position_value": portfolio_value - account.current_cash,
                "initial_cash": account.initial_cash,
                "total_pnl": portfolio_value - account.initial_cash,
                "total_return": (portfolio_value - account.initial_cash) / account.initial_cash,
                "holdings": holdings
            }

    def calculate_daily_pnl(self, target_date: Optional[date] = None) -> Dict:
        """计算每日P&L"""
        if target_date is None:
            target_date = date.today()

        date_str = target_date.strftime("%Y-%m-%d")

        with Session(engine) as db:
            # 检查今日是否已计算
            existing = db.query(SimDailyPnL).filter_by(
                account_id=self.account_id,
                trade_date=date_str
            ).first()

            if existing:
                return {
                    "date": date_str,
                    "total_value": existing.total_value,
                    "daily_pnl": existing.daily_pnl,
                    "return_pct": existing.return_pct
                }

            # 获取当前组合状态
            status = self.get_portfolio_status()

            # 获取前一日记录
            prev_record = db.query(SimDailyPnL).filter_by(
                account_id=self.account_id
            ).order_by(SimDailyPnL.trade_date.desc()).first()

            prev_value = prev_record.total_value if prev_record else status["initial_cash"]
            daily_pnl = status["total_value"] - prev_value
            return_pct = daily_pnl / prev_value if prev_value > 0 else 0

            # 记录今日P&L
            pnl_record = SimDailyPnL(
                account_id=self.account_id,
                trade_date=date_str,
                total_value=status["total_value"],
                cash_value=status["cash"],
                position_value=status["position_value"],
                daily_pnl=daily_pnl,
                cumulative_pnl=status["total_pnl"],
                return_pct=return_pct
            )

            db.add(pnl_record)
            db.commit()

            return {
                "date": date_str,
                "total_value": status["total_value"],
                "daily_pnl": daily_pnl,
                "return_pct": return_pct,
                "cumulative_pnl": status["total_pnl"]
            }


# 全局交易引擎实例
trading_engine = TradingEngine()