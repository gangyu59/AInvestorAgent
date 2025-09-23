# backend/scoring/combine.py
from __future__ import annotations
from typing import Any, Dict, Mapping, Optional

# 读取权重：你已经在 backend/scoring/weights.py 里放了 WEIGHTS
try:
    from .weights import WEIGHTS as _WEIGHTS  # type: ignore
except Exception:
    # 兜底（即使权重文件缺失，也让服务能启动）
    _WEIGHTS = {
        "value": 0.30,
        "quality": 0.25,
        "momentum": 0.25,
        "sentiment": 0.20,
        # risk 非必需：如有则按“越小越好”处理
        "risk": 0.00,
    }

def _get(obj: Any, name: str) -> Optional[float]:
    """兼容 dict/对象 两种取值方式；无值返回 None。"""
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        v = obj.get(name)
        if v is None:
            # 兼容 without "f_" 前缀
            v = obj.get(name.replace("f_", ""))
        return None if v is None else float(v)
    # 对象：优先 f_xxx，其次去掉前缀
    if hasattr(obj, name):
        v = getattr(obj, name)
    else:
        alt = name.replace("f_", "")
        v = getattr(obj, alt, None)
    return None if v is None else float(v)

def _clamp01(x: Optional[float]) -> float:
    """把 None 安全映射为 0，并把区间裁剪在 [0,1]。"""
    if x is None:
        return 0.0
    try:
        x = float(x)
    except Exception:
        return 0.0
    if x != x:  # NaN
        return 0.0
    return 0.0 if x < 0 else (1.0 if x > 1 else x)

def _normalize_weights(w: Mapping[str, float]) -> Dict[str, float]:
    """把权重归一化到总和=1（忽略<=0的项）。"""
    pos = {k: float(v) for k, v in w.items() if float(v) > 0}
    s = sum(pos.values())
    if s <= 0:
        # 极端兜底：均分 value/quality/momentum/sentiment
        base = {"value": .25, "quality": .25, "momentum": .25, "sentiment": .25}
        return base
    return {k: v / s for k, v in pos.items()}

def combine_score(
    factor_row: Any,
    weights: Optional[Mapping[str, float]] = None,
    version_tag: str = "v1.0.0",
) -> Dict[str, Any]:
    """
    把因子合成为分项分数 + 总分（0–100）。
    约定：因子值是 0–1 的标准化值；risk 越小越好（如提供则使用 1-risk）。
    返回结构必须满足前端期望：
      { value, quality, momentum, sentiment, score, version_tag }
    """
    W = _normalize_weights((weights or _WEIGHTS) or {})

    f_value     = _clamp01(_get(factor_row, "f_value"))
    f_quality   = _clamp01(_get(factor_row, "f_quality"))
    f_momentum  = _clamp01(_get(factor_row, "f_momentum"))
    f_sentiment = _clamp01(_get(factor_row, "f_sentiment"))
    f_risk_raw  = _get(factor_row, "f_risk")
    # risk: 如果存在，则按“越小越好”，映射为 (1 - 风险)
    f_risk = _clamp01(1.0 - float(f_risk_raw)) if f_risk_raw is not None else None

    # 分项分数（各分项均是 0–100 内的整数，便于表格显示）
    s_value     = round(100.0 * f_value    * W.get("value", 0.0))
    s_quality   = round(100.0 * f_quality  * W.get("quality", 0.0))
    s_momentum  = round(100.0 * f_momentum * W.get("momentum", 0.0))
    s_sentiment = round(100.0 * f_sentiment* W.get("sentiment", 0.0))
    s_risk      = round(100.0 * (f_risk or 0.0) * W.get("risk", 0.0))

    total = int(s_value + s_quality + s_momentum + s_sentiment + s_risk)

    return {
        "value": int(s_value),
        "quality": int(s_quality),
        "momentum": int(s_momentum),
        "sentiment": int(s_sentiment),
        # risk 分项是可选；前端现在没显示，可保留在结构里以备后用
        # "risk": int(s_risk),
        "score": total,
        "version_tag": version_tag,
    }
