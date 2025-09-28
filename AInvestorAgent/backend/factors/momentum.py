# backend/factors/momentum.py
from datetime import date, timedelta
from sqlalchemy.orm import Session
from backend.storage import models
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

def _last_close(db: Session, symbol: str, asof: date):
    q = (db.query(models.PriceDaily)
           .filter(models.PriceDaily.symbol == symbol,
                   models.PriceDaily.date <= asof)
           .order_by(models.PriceDaily.date.desc())
           .limit(1).all())
    return q[0].close if q else None

def momentum_return(db: Session, symbol: str, asof: date, lookback_days: int = 60):
    c_t = _last_close(db, symbol, asof)
    c_0 = _last_close(db, symbol, asof - timedelta(days=lookback_days))
    if c_t and c_0 and c_0 > 0:
        return (c_t / c_0) - 1.0
    return None

# === 新增强功能（无需talib） ===

def get_price_series(db: Session, symbol: str, asof: date, lookback_days: int = 252) -> pd.DataFrame:
    """获取价格序列数据"""
    start_date = asof - timedelta(days=lookback_days)
    
    prices = db.query(models.PriceDaily).filter(
        models.PriceDaily.symbol == symbol,
        models.PriceDaily.date >= start_date,
        models.PriceDaily.date <= asof
    ).order_by(models.PriceDaily.date).all()
    
    if not prices:
        return pd.DataFrame()
    
    data = []
    for p in prices:
        data.append({
            'date': p.date,
            'open': float(p.open),
            'high': float(p.high),
            'low': float(p.low),
            'close': float(p.close),
            'volume': float(p.volume)
        })
    
    return pd.DataFrame(data)

def calculate_sma(prices: List[float], period: int) -> List[float]:
    """计算简单移动平均线"""
    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(np.nan)
        else:
            sma.append(np.mean(prices[i-period+1:i+1]))
    return sma

def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """计算RSI指标"""
    if len(prices) < period + 1:
        return [np.nan] * len(prices)
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    rsi = [np.nan] * (period)  # 前period个值为NaN
    
    # 初始平均值
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    if avg_loss == 0:
        rsi.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi.append(100 - (100 / (1 + rs)))
    
    # 后续计算
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
    
    return rsi

def calculate_technical_indicators(db: Session, symbol: str, asof: date) -> Dict[str, float]:
    """计算全套技术指标（纯Python实现）"""
    df = get_price_series(db, symbol, asof, lookback_days=252)
    
    if len(df) < 20:
        return {}
    
    indicators = {}
    
    try:
        close = df['close'].tolist()
        high = df['high'].tolist()
        low = df['low'].tolist()
        volume = df['volume'].tolist()
        
        # 移动平均线
        if len(close) >= 5:
            ma5 = calculate_sma(close, 5)
            indicators['ma5'] = ma5[-1] if not np.isnan(ma5[-1]) else None
            
        if len(close) >= 10:
            ma10 = calculate_sma(close, 10)
            indicators['ma10'] = ma10[-1] if not np.isnan(ma10[-1]) else None
            
        if len(close) >= 20:
            ma20 = calculate_sma(close, 20)
            indicators['ma20'] = ma20[-1] if not np.isnan(ma20[-1]) else None
            
        if len(close) >= 60:
            ma60 = calculate_sma(close, 60)
            indicators['ma60'] = ma60[-1] if not np.isnan(ma60[-1]) else None
        
        # RSI计算
        if len(close) >= 15:
            rsi_values = calculate_rsi(close, 14)
            indicators['rsi'] = rsi_values[-1] if not np.isnan(rsi_values[-1]) else None
        
        # 波动率
        if len(close) >= 20:
            returns = [close[i]/close[i-1] - 1 for i in range(1, len(close))]
            indicators['volatility'] = np.std(returns) * np.sqrt(252)  # 年化波动率
        
        # 价格相对位置（20日内）
        if len(close) >= 20:
            recent_high = max(high[-20:])
            recent_low = min(low[-20:])
            if recent_high != recent_low:
                indicators['price_position'] = (close[-1] - recent_low) / (recent_high - recent_low)
            else:
                indicators['price_position'] = 0.5
        
        # 成交量相对位置
        if len(volume) >= 20:
            avg_volume = np.mean(volume[-20:])
            if avg_volume > 0:
                indicators['volume_ratio'] = volume[-1] / avg_volume
            else:
                indicators['volume_ratio'] = 1.0
        
        # 动量因子增强
        momentum_1m = momentum_return(db, symbol, asof, 20) or 0
        momentum_3m = momentum_return(db, symbol, asof, 60) or 0
        momentum_12m = momentum_return(db, symbol, asof, 252) or 0
        
        indicators.update({
            'momentum_1m': momentum_1m,
            'momentum_3m': momentum_3m,
            'momentum_12m': momentum_12m,
            'momentum_score': (momentum_1m * 0.5 + momentum_3m * 0.3 + momentum_12m * 0.2)
        })
        
    except Exception as e:
        print(f"技术指标计算失败 {symbol}: {e}")
    
    return indicators