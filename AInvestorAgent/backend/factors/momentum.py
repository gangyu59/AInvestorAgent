# backend/factors/momentum.py
from datetime import date, timedelta
from sqlalchemy.orm import Session
from backend.storage import models
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any

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

def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
    """计算MACD指标"""
    if len(prices) < slow + signal:
        return {'macd': [np.nan] * len(prices), 'signal': [np.nan] * len(prices), 'histogram': [np.nan] * len(prices)}

    # 计算EMA
    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema_values = [data[0]]  # 第一个值作为初始EMA
        for i in range(1, len(data)):
            ema_val = (data[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema_val)
        return ema_values

    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)

    # MACD线
    macd = [fast_val - slow_val for fast_val, slow_val in zip(ema_fast, ema_slow)]

    # 信号线
    signal_line = ema(macd[slow - 1:], signal)  # 从slow-1开始计算信号线
    signal_full = [np.nan] * (slow - 1) + signal_line

    # 柱状图
    histogram = []
    for i in range(len(macd)):
        if i < len(signal_full) and not np.isnan(signal_full[i]):
            histogram.append(macd[i] - signal_full[i])
        else:
            histogram.append(np.nan)

    return {
        'macd': macd,
        'signal': signal_full,
        'histogram': histogram
    }

def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, List[float]]:
    """计算布林带"""
    if len(prices) < period:
        return {'upper': [np.nan] * len(prices), 'middle': [np.nan] * len(prices), 'lower': [np.nan] * len(prices)}

    sma = calculate_sma(prices, period)
    upper, lower = [], []

    for i in range(len(prices)):
        if i < period - 1:
            upper.append(np.nan)
            lower.append(np.nan)
        else:
            std = np.std(prices[i - period + 1:i + 1])
            upper.append(sma[i] + std_dev * std)
            lower.append(sma[i] - std_dev * std)

    return {
        'upper': upper,
        'middle': sma,
        'lower': lower
    }

def calculate_signal_strength(db: Session, symbol: str, asof: date) -> Dict[str, float]:
    """
    计算综合信号强度
    """
    indicators = calculate_technical_indicators(db, symbol, asof)
    df = get_price_series(db, symbol, asof, lookback_days=252)

    if len(df) < 50:
        return {}

    signal_strength = {}

    try:
        close = df['close'].tolist()

        # 趋势信号强度
        ma20 = indicators.get('ma20')
        ma60 = indicators.get('ma60')
        current_price = close[-1]

        trend_signals = []
        if ma20 and ma60:
            # 均线排列
            if current_price > ma20 > ma60:
                trend_signals.append(1)  # 强多头排列
            elif current_price > ma20 and ma20 < ma60:
                trend_signals.append(0.5)  # 弱多头
            elif current_price < ma20 < ma60:
                trend_signals.append(-1)  # 强空头排列
            else:
                trend_signals.append(-0.5)  # 弱空头

        # RSI信号
        rsi = indicators.get('rsi')
        if rsi:
            if rsi > 70:
                trend_signals.append(-0.5)  # 超买
            elif rsi < 30:
                trend_signals.append(0.5)  # 超卖
            else:
                trend_signals.append(0)  # 中性

        # 动量信号
        momentum_score = indicators.get('momentum_score', 0)
        if momentum_score > 0.1:
            trend_signals.append(1)
        elif momentum_score < -0.1:
            trend_signals.append(-1)
        else:
            trend_signals.append(0)

        # 计算MACD信号
        macd_result = calculate_macd(close)
        macd_hist = macd_result['histogram']
        if len(macd_hist) > 0 and not np.isnan(macd_hist[-1]):
            if macd_hist[-1] > 0:
                trend_signals.append(0.5)
            else:
                trend_signals.append(-0.5)

        # 布林带信号
        bb_result = calculate_bollinger_bands(close)
        if not np.isnan(bb_result['upper'][-1]):
            bb_position = (current_price - bb_result['lower'][-1]) / (bb_result['upper'][-1] - bb_result['lower'][-1])
            if bb_position > 0.8:
                trend_signals.append(-0.3)  # 接近上轨，谨慎
            elif bb_position < 0.2:
                trend_signals.append(0.3)  # 接近下轨，关注
            else:
                trend_signals.append(0)

        # 综合信号强度
        if trend_signals:
            signal_strength['overall_signal'] = float(np.mean(trend_signals))
            signal_strength['signal_count'] = len(trend_signals)
            signal_strength['signal_consistency'] = float(np.std(trend_signals))  # 一致性（越小越一致）

            # 信号评级
            avg_signal = signal_strength['overall_signal']
            consistency = signal_strength['signal_consistency']

            if avg_signal > 0.5 and consistency < 0.3:
                signal_strength['rating'] = "strong_buy"
            elif avg_signal > 0.2 and consistency < 0.5:
                signal_strength['rating'] = "buy"
            elif avg_signal < -0.5 and consistency < 0.3:
                signal_strength['rating'] = "strong_sell"
            elif avg_signal < -0.2 and consistency < 0.5:
                signal_strength['rating'] = "sell"
            else:
                signal_strength['rating'] = "hold"

    except Exception as e:
        print(f"信号强度计算失败 {symbol}: {e}")

    return signal_strength

def calculate_momentum_quality(db: Session, symbol: str, asof: date) -> Dict[str, float]:
    """
    评估动量质量（区分真动量和假突破）
    """
    df = get_price_series(db, symbol, asof, lookback_days=252)

    if len(df) < 60:
        return {}

    quality_metrics = {}

    try:
        close = df['close'].tolist()
        volume = df['volume'].tolist()

        # 动量持续性
        returns_20d = [(close[i] - close[i - 20]) / close[i - 20] for i in range(20, len(close))]
        if len(returns_20d) >= 5:
            # 最近5个周期的动量方向一致性
            positive_count = sum(1 for r in returns_20d[-5:] if r > 0)
            quality_metrics['momentum_persistence'] = positive_count / 5.0

        # 量价配合度
        price_changes = [close[i] - close[i - 1] for i in range(1, len(close))]
        volume_changes = [volume[i] - volume[i - 1] for i in range(1, len(volume))]

        # 计算价涨量增的比例
        price_vol_match = sum(1 for i in range(len(price_changes))
                              if (price_changes[i] > 0 and volume_changes[i] > 0) or
                              (price_changes[i] < 0 and volume_changes[i] < 0))
        quality_metrics['price_volume_match'] = price_vol_match / len(price_changes)

        # 动量稳定性（收益率标准差的倒数）
        recent_returns = [(close[i] - close[i - 1]) / close[i - 1] for i in range(max(1, len(close) - 60), len(close))]
        if recent_returns:
            volatility = np.std(recent_returns)
            momentum_value = (close[-1] / close[max(0, len(close) - 60)] - 1)
            if volatility > 0:
                quality_metrics['momentum_stability'] = abs(momentum_value) / volatility
            else:
                quality_metrics['momentum_stability'] = 0.0

        # 综合动量质量评分
        persistence = quality_metrics.get('momentum_persistence', 0.5)
        pv_match = quality_metrics.get('price_volume_match', 0.5)
        stability = min(1.0, quality_metrics.get('momentum_stability', 0) / 2.0)

        quality_metrics['overall_momentum_quality'] = (persistence * 0.4 + pv_match * 0.3 + stability * 0.3)

    except Exception as e:
        print(f"动量质量计算失败 {symbol}: {e}")

    return quality_metrics

def get_advanced_momentum_report(db: Session, symbol: str, asof: date) -> Dict[str, Any]:
    """
    生成高级动量分析报告
    """
    from typing import Any

    report = {
        'symbol': symbol,
        'as_of': asof.isoformat(),
        'technical_indicators': {},
        'signal_strength': {},
        'momentum_quality': {},
        'recommendations': []
    }

    try:
        # 基础技术指标
        report['technical_indicators'] = calculate_technical_indicators(db, symbol, asof)

        # 信号强度
        report['signal_strength'] = calculate_signal_strength(db, symbol, asof)

        # 动量质量
        report['momentum_quality'] = calculate_momentum_quality(db, symbol, asof)

        # 生成建议
        signal_strength = report['signal_strength']
        rating = signal_strength.get('rating', 'hold')

        if rating == "strong_buy":
            report['recommendations'].append("技术面强烈买入信号，多项指标共振向上")
        elif rating == "buy":
            report['recommendations'].append("技术面偏多，建议适度关注")
        elif rating == "hold":
            report['recommendations'].append("技术面中性，观望为主")
        elif rating == "sell":
            report['recommendations'].append("技术面偏弱，建议谨慎")
        else:
            report['recommendations'].append("技术面看空，规避风险")

        # 风险提示
        volatility = report['technical_indicators'].get('volatility', 0)
        if volatility > 0.35:
            report['recommendations'].append("⚠️ 波动率较高，注意控制仓位")

        rsi = report['technical_indicators'].get('rsi')
        if rsi:
            if rsi > 75:
                report['recommendations'].append("⚠️ RSI超买区域，短期可能回调")
            elif rsi < 25:
                report['recommendations'].append("⚠️ RSI超卖区域，存在反弹机会")

        # 动量质量评估
        momentum_quality = report['momentum_quality'].get('overall_momentum_quality', 0.5)
        if momentum_quality > 0.7:
            report['recommendations'].append("✓ 动量质量优秀，趋势可持续性强")
        elif momentum_quality < 0.3:
            report['recommendations'].append("⚠️ 动量质量较弱，可能为假突破")

    except Exception as e:
        print(f"动量报告生成失败 {symbol}: {e}")
        report['error'] = str(e)

    return report