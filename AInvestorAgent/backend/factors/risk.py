# backend/factors/risk.py
from datetime import date, timedelta
from sqlalchemy.orm import Session
from backend.storage import models
import numpy as np
from typing import Dict, List, Optional
from .momentum import get_price_series


def calculate_var(returns: List[float], confidence_level: float = 0.95) -> float:
    """计算风险价值VaR"""
    if not returns or len(returns) < 30:
        return 0.0

    return float(np.percentile(returns, (1 - confidence_level) * 100))


def calculate_max_drawdown(prices: List[float]) -> Dict[str, float]:
    """计算最大回撤"""
    if not prices or len(prices) < 2:
        return {'max_drawdown': 0.0, 'current_drawdown': 0.0}

    # 计算累积收益
    cumulative = np.array(prices)
    peak = np.maximum.accumulate(cumulative)

    # 计算回撤
    drawdown = (cumulative - peak) / peak
    max_drawdown = np.min(drawdown)
    current_drawdown = drawdown[-1]

    return {
        'max_drawdown': float(max_drawdown),
        'current_drawdown': float(current_drawdown)
    }


def calculate_risk_metrics(db: Session, symbol: str, asof: date) -> Dict[str, float]:
    """计算风险指标"""
    df = get_price_series(db, symbol, asof, lookback_days=252)

    if len(df) < 30:
        return {}

    metrics = {}

    try:
        close_prices = df['close'].tolist()

        # 计算收益率
        returns = []
        for i in range(1, len(close_prices)):
            ret = (close_prices[i] - close_prices[i - 1]) / close_prices[i - 1]
            returns.append(ret)

        if len(returns) >= 30:
            # VaR计算
            metrics['var_95'] = calculate_var(returns, 0.95)
            metrics['var_99'] = calculate_var(returns, 0.99)

            # 最大回撤
            drawdown_metrics = calculate_max_drawdown(close_prices)
            metrics.update(drawdown_metrics)

            # 波动率
            daily_vol = np.std(returns)
            metrics['daily_volatility'] = float(daily_vol)
            metrics['annual_volatility'] = float(daily_vol * np.sqrt(252))

            # 夏普比率（假设无风险利率2%）
            risk_free_rate = 0.02
            excess_return = np.mean(returns) * 252 - risk_free_rate
            if daily_vol > 0:
                metrics['sharpe_ratio'] = float(excess_return / (daily_vol * np.sqrt(252)))
            else:
                metrics['sharpe_ratio'] = 0.0

    except Exception as e:
        print(f"风险指标计算失败 {symbol}: {e}")

    return metrics