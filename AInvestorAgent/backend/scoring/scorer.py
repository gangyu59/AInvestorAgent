from __future__ import annotations
from dataclasses import dataclass
from backend.factors.momentum import momentum_return, _last_close
from typing import Dict, List, Optional
from datetime import date
from sqlalchemy.orm import Session

from backend.factors.momentum import momentum_return
from backend.factors.sentiment import avg_sentiment_7d
from backend.storage import models

# 基线权重（可在 .env 或配置中覆盖）
BASE_WEIGHTS = {"value": 0.25, "quality": 0.20, "momentum": 0.35, "sentiment": 0.20}

@dataclass
class FactorRow:
    symbol: str
    f_value: Optional[float] = None
    f_quality: Optional[float] = None
    f_momentum_raw: Optional[float] = None
    f_sentiment: Optional[float] = None
    f_momentum: Optional[float] = None


def _minmax_scale(arr: List[Optional[float]]) -> List[Optional[float]]:
    vals = [x for x in arr if x is not None]
    if not vals:
        return [None] * len(arr)

    lo, hi = min(vals), max(vals)

    # ⭐ 修改这里：单值时直接返回原值（不缩放）
    if len(vals) == 1:
        return arr  # 单值不缩放，保持原值

    if hi - lo < 1e-12:  # 多个值但都相同
        return [0.5 if x is not None else None for x in arr]

    return [None if x is None else (x - lo) / (hi - lo) for x in arr]


def compute_factors(db: Session, symbols: List[str], asof: date) -> List[FactorRow]:
    rows: List[FactorRow] = []
    for s in symbols:
        # 动量和情绪
        mom_r = momentum_return(db, s, asof, lookback_days=60)
        senti = avg_sentiment_7d(db, s, asof, days=30)

        # ⭐ 添加调试输出
        print(f"  {s} 原始动量返回值={mom_r}")

        # 添加价值和质量因子计算
        f_value = _compute_value_factor(db, s, asof)
        f_quality = _compute_quality_factor(db, s, asof)

        rows.append(FactorRow(
            symbol=s,
            f_value=f_value,
            f_quality=f_quality,
            f_momentum_raw=mom_r,  # ⭐ 保存原始值
            f_sentiment=senti
        ))

    # ⭐ 调试：显示缩放前后的动量值
    raw_momentums = [r.f_momentum_raw for r in rows]
    print(f"\n📊 缩放前动量列表: {raw_momentums}")

    scaled = _minmax_scale(raw_momentums)
    print(f"📊 缩放后动量列表: {scaled}\n")

    for r, m in zip(rows, scaled):
        r.f_momentum = m
    return rows


def _compute_value_factor(db: Session, symbol: str, asof: date) -> float:
    """计算价值因子(基于 PE/PB)"""
    from backend.storage.models import Fundamental

    fund = db.query(Fundamental).filter(
        Fundamental.symbol == symbol
    ).order_by(Fundamental.as_of.desc()).first()

    if not fund:
        print(f"  ⚠️ {symbol}: 数据库中无基本面数据")
        return 0.5

    scores = []

    # PE因子(低PE高分)
    if fund.pe and fund.pe > 0:
        # 处理极端值：TSLA的PE=243太高
        if fund.pe > 100:
            pe_score = 0.0  # 估值过高，给最低分
        elif fund.pe < 10:
            pe_score = 1.0  # 估值很低，给最高分
        else:
            # 正常范围：10-50
            pe_score = max(0, min(1, (50 - fund.pe) / 40))
        scores.append(pe_score)
        print(f"  {symbol} PE={fund.pe:.2f} → PE分数={pe_score:.3f}")
    else:
        print(f"  ⚠️ {symbol}: PE数据无效({fund.pe})")

    # PB因子(低PB高分)
    if fund.pb and fund.pb > 0:
        # AAPL的PB=57.97太高，说明是成长股
        if fund.pb > 20:
            pb_score = 0.0
        elif fund.pb < 2:
            pb_score = 1.0
        else:
            # 正常范围：2-10
            pb_score = max(0, min(1, (10 - fund.pb) / 8))
        scores.append(pb_score)
        print(f"  {symbol} PB={fund.pb:.2f} → PB分数={pb_score:.3f}")
    else:
        print(f"  ⚠️ {symbol}: PB数据无效({fund.pb})")

    if not scores:
        print(f"  ⚠️ {symbol}: 无有效PE/PB数据，返回中性0.5")
        return 0.5

    final = sum(scores) / len(scores)
    print(f"  ✅ {symbol} 价值因子={final:.3f}")
    return final


def _compute_quality_factor(db: Session, symbol: str, asof: date) -> float:
    """计算质量因子(基于 ROE/净利率)"""
    from backend.storage.models import Fundamental

    fund = db.query(Fundamental).filter(
        Fundamental.symbol == symbol
    ).order_by(Fundamental.as_of.desc()).first()

    if not fund:
        print(f"  ⚠️ {symbol}: 数据库中无基本面数据")
        return 0.5

    scores = []

    # ROE因子（注意：数据库里的ROE可能是小数或百分比）
    if fund.roe is not None and fund.roe != 0:
        # 判断是小数格式(0.xx)还是百分比格式(xx.xx)
        roe_pct = fund.roe if fund.roe > 1 else fund.roe * 100

        if roe_pct < 0:
            roe_score = 0.0  # 负ROE最低分
        elif roe_pct > 30:
            roe_score = 1.0  # 超高ROE最高分
        else:
            # 正常范围：0-30%
            roe_score = max(0, min(1, roe_pct / 30))
        scores.append(roe_score)
        print(f"  {symbol} ROE={roe_pct:.2f}% → ROE分数={roe_score:.3f}")
    else:
        print(f"  ⚠️ {symbol}: ROE数据无效({fund.roe})")

    # 净利率因子
    if fund.net_margin is not None and fund.net_margin != 0:
        margin_pct = fund.net_margin if fund.net_margin > 1 else fund.net_margin * 100

        if margin_pct < 0:
            margin_score = 0.0
        elif margin_pct > 25:
            margin_score = 1.0
        else:
            # 正常范围：0-25%
            margin_score = max(0, min(1, margin_pct / 25))
        scores.append(margin_score)
        print(f"  {symbol} 净利率={margin_pct:.2f}% → 利润率分数={margin_score:.3f}")
    else:
        print(f"  ⚠️ {symbol}: 净利率数据无效({fund.net_margin})")

    if not scores:
        print(f"  ⚠️ {symbol}: 无有效ROE/净利率数据，返回中性0.5")
        return 0.5

    final = sum(scores) / len(scores)
    print(f"  ✅ {symbol} 质量因子={final:.3f}")
    return final


def aggregate_score(row: FactorRow, weights: Dict[str, float]=BASE_WEIGHTS) -> float:
    parts = []
    total_w = 0.0
    for k, w in weights.items():
        v = {"value": row.f_value,
             "quality": row.f_quality,
             "momentum": getattr(row, "f_momentum", None),
             "sentiment": row.f_sentiment}[k]
        if v is None:
            continue
        parts.append(w * v)
        total_w += w
    if total_w <= 0:
        return 50.0  # 完全缺失时给中性分
    return 100.0 * sum(parts) / total_w

def upsert_scores(db: Session, asof: date, rows: List[FactorRow], version_tag="v0.1"):
    for r in rows:
        score = aggregate_score(r)
        obj = (db.query(models.ScoreDaily)
                 .filter(models.ScoreDaily.as_of == asof,
                         models.ScoreDaily.symbol == r.symbol)
                 .one_or_none())
        data = dict(as_of=asof, symbol=r.symbol,
                    f_value=r.f_value, f_quality=r.f_quality,
                    f_momentum=getattr(r, "f_momentum", None),
                    f_sentiment=r.f_sentiment, score=score,
                    version_tag=version_tag)
        if obj:
            for k, v in data.items(): setattr(obj, k, v)
        else:
            db.add(models.ScoreDaily(**data))
    db.commit()

# === Portfolio builder (追加) ===
@dataclass
class Pick:
    symbol: str
    score: float
    f_value: Optional[float]
    f_quality: Optional[float]
    f_momentum: Optional[float]
    f_sentiment: Optional[float]
    weight: float

def _clip_and_renorm(weights: List[float], min_w: float, max_w: float) -> List[float]:
    # 先裁剪，再对未达标部分按比例补齐，最多迭代3次避免数值误差
    import math
    w = [min(max(x, 0.0), 1.0) for x in weights]
    for _ in range(3):
        w = [min(max(x, min_w), max_w) for x in w]
        s = sum(w)
        if s <= 0:
            w = [1.0/len(w)] * len(w); break
        w = [x/s for x in w]
        # 若再裁剪不会变化就退出
        w2 = [min(max(x, min_w), max_w) for x in w]
        if all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12) for a, b in zip(w, w2)):
            break
        w = w2
    # 再做一次精确归一
    s = sum(w)
    return [x/s for x in w] if s > 0 else [1.0/len(w)]*len(w)

def build_portfolio(
    db: Session,
    symbols: List[str],
    asof: date,
    top_n: int = 5,
    scheme: str = "proportional",  # "equal" or "proportional"
    alpha: float = 1.0,             # 对分数做指数，alpha>1更集中
    min_w: float = 0.0,
    max_w: float = 0.4,
) -> Dict:
    """
    从打分中选出 Top-N，并根据 scheme 生成权重（裁剪到 [min_w,max_w] 后归一）。
    返回 dict: {as_of, version_tag, items:[{symbol,score,f_*,weight}], meta:{...}}
    """
    rows = compute_factors(db, symbols, asof)
    # 计算分数（使用你现有 aggregate_score）
    scored = []
    for r in rows:
        s = aggregate_score(r)  # 0..100
        scored.append((s, r))
    # 取 Top-N
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:max(1, min(top_n, len(scored)))]
    # 权重
    if scheme == "equal":
        raw = [1.0/len(top)] * len(top)
    else:
        # proportional to score^alpha
        xs = [max(t[0], 1e-6) ** max(alpha, 0.0) for t in top]
        s = sum(xs)
        raw = [x/s for x in xs] if s > 0 else [1.0/len(top)] * len(top)
    w = _clip_and_renorm(raw, min_w, max_w)

    items: List[Pick] = []
    for (score, r), wi in zip(top, w):
        items.append(Pick(
            symbol=r.symbol, score=score,
            f_value=r.f_value, f_quality=r.f_quality,
            f_momentum=getattr(r, "f_momentum", None),
            f_sentiment=r.f_sentiment,
            weight=round(wi, 6),
        ))
    # 顺手把 scores 写库（你已有 upsert_scores）
    upsert_scores(db, asof, [t[1] for t in top], version_tag="v0.1")
    return {
        "as_of": asof.isoformat(),
        "version_tag": "v0.1",
        "items": [i.__dict__ for i in items],
        "meta": {"scheme": scheme, "alpha": alpha, "min_w": min_w, "max_w": max_w}
    }


# === 因子有效性验证 (追加到现有 scorer.py) ===
from scipy import stats
import numpy as np


def validate_factor_effectiveness(db: Session, symbols: List[str],
                                  lookback_months: int = 12) -> Dict[str, Dict]:
    """
    验证因子有效性：计算 IC (Information Coefficient)
    IC = 因子值与未来收益的相关性
    """
    from datetime import timedelta
    import pandas as pd

    results = {
        'momentum': {'ic_series': [], 'ic_mean': 0.0, 'ic_std': 0.0, 'ic_ir': 0.0},
        'sentiment': {'ic_series': [], 'ic_mean': 0.0, 'ic_std': 0.0, 'ic_ir': 0.0},
        'overall_score': {'ic_series': [], 'ic_mean': 0.0, 'ic_std': 0.0, 'ic_ir': 0.0}
    }

    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_months * 30)

        # 按月计算IC
        current_date = start_date
        while current_date < end_date:
            next_month = current_date + timedelta(days=30)

            # 获取当月因子值
            factor_data = []
            future_returns = []

            for symbol in symbols:
                # 当月因子
                mom_factor = momentum_return(db, symbol, current_date, 60)
                sent_factor = avg_sentiment_7d(db, symbol, current_date, 7)

                # 未来1月收益
                current_price = _last_close(db, symbol, current_date)
                future_price = _last_close(db, symbol, next_month)

                if all(x is not None for x in [mom_factor, sent_factor, current_price, future_price]):
                    future_ret = (future_price / current_price) - 1.0

                    # 计算综合分数
                    row = FactorRow(symbol, None, None, mom_factor, sent_factor)
                    scaled_mom = _minmax_scale([mom_factor])[0] or 0.5
                    row.f_momentum = scaled_mom
                    overall_score = aggregate_score(row)

                    factor_data.append({
                        'momentum': scaled_mom,
                        'sentiment': sent_factor,
                        'overall_score': overall_score / 100.0  # 归一化到0-1
                    })
                    future_returns.append(future_ret)

            # 计算当月IC
            if len(factor_data) >= 5:  # 至少5只股票
                for factor_name in ['momentum', 'sentiment', 'overall_score']:
                    factor_values = [d[factor_name] for d in factor_data]
                    ic, p_value = stats.pearsonr(factor_values, future_returns)
                    if not np.isnan(ic):
                        results[factor_name]['ic_series'].append(ic)

            current_date = next_month

        # 计算统计指标
        for factor_name in results:
            ic_series = results[factor_name]['ic_series']
            if ic_series:
                results[factor_name]['ic_mean'] = float(np.mean(ic_series))
                results[factor_name]['ic_std'] = float(np.std(ic_series))
                results[factor_name]['ic_ir'] = (
                    results[factor_name]['ic_mean'] / results[factor_name]['ic_std']
                    if results[factor_name]['ic_std'] > 0 else 0.0
                )
                # 正IC占比
                positive_rate = sum(1 for ic in ic_series if ic > 0) / len(ic_series)
                results[factor_name]['positive_rate'] = positive_rate

    except Exception as e:
        print(f"因子有效性验证失败: {e}")

    return results


def get_portfolio_risk_metrics(db: Session, weights: List[Dict[str, Any]],
                               asof: date) -> Dict[str, float]:
    """
    计算组合风险指标
    """
    from backend.factors.risk import calculate_risk_metrics, get_price_series

    portfolio_metrics = {}

    try:
        total_weight = sum(w.get('weight', 0) for w in weights)
        if total_weight <= 0:
            return portfolio_metrics

        # 获取各股票的历史收益率
        all_returns = []
        valid_weights = []

        for w in weights:
            symbol = w.get('symbol')
            weight = w.get('weight', 0) / total_weight  # 归一化权重

            if symbol and weight > 0:
                df = get_price_series(db, symbol, asof, 252)
                if len(df) >= 30:
                    prices = df['close'].tolist()
                    returns = [(prices[i] - prices[i - 1]) / prices[i - 1]
                               for i in range(1, len(prices))]

                    all_returns.append(np.array(returns) * weight)
                    valid_weights.append(weight)

        if all_returns:
            # 计算组合收益率序列
            min_length = min(len(r) for r in all_returns)
            portfolio_returns = np.sum([r[:min_length] for r in all_returns], axis=0)

            # 组合风险指标
            portfolio_metrics['portfolio_volatility'] = float(np.std(portfolio_returns) * np.sqrt(252))
            portfolio_metrics['portfolio_var_95'] = float(np.percentile(portfolio_returns, 5))
            portfolio_metrics['portfolio_var_99'] = float(np.percentile(portfolio_returns, 1))

            # 最大回撤（组合层面）
            cumulative = np.cumprod(1 + portfolio_returns)
            peak = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - peak) / peak
            portfolio_metrics['portfolio_max_drawdown'] = float(np.min(drawdown))

            # 夏普比率
            excess_return = np.mean(portfolio_returns) * 252 - 0.02  # 假设无风险利率2%
            portfolio_metrics['portfolio_sharpe'] = (
                excess_return / portfolio_metrics['portfolio_volatility']
                if portfolio_metrics['portfolio_volatility'] > 0 else 0.0
            )

            # 集中度风险
            portfolio_metrics['concentration_risk'] = float(np.sum(np.array(valid_weights) ** 2))

    except Exception as e:
        print(f"组合风险指标计算失败: {e}")

    return portfolio_metrics