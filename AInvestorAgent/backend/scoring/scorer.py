from __future__ import annotations
from dataclasses import dataclass
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
    f_value: Optional[float]     # 0..1 或 None
    f_quality: Optional[float]
    f_momentum_raw: Optional[float]  # 原始收益率，先不缩放
    f_sentiment: Optional[float]     # 0..1 或 None

def _minmax_scale(arr: List[Optional[float]]) -> List[Optional[float]]:
    vals = [x for x in arr if x is not None]
    if not vals:
        return [None]*len(arr)
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return [0.5 if x is not None else None for x in arr]
    return [None if x is None else (x - lo) / (hi - lo) for x in arr]

def compute_factors(db: Session, symbols: List[str], asof: date) -> List[FactorRow]:
    rows: List[FactorRow] = []
    for s in symbols:
        mom_r = momentum_return(db, s, asof, lookback_days=60)
        senti = avg_sentiment_7d(db, s, asof, days=7)
        # 价值/质量先留空（未来接 fundamentals），用 None 表示缺失
        rows.append(FactorRow(symbol=s, f_value=None, f_quality=None,
                              f_momentum_raw=mom_r, f_sentiment=senti))
    # 将动量收益率 min-max 到 0..1
    scaled = _minmax_scale([r.f_momentum_raw for r in rows])
    for r, m in zip(rows, scaled):
        r.f_momentum = m
    return rows

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
