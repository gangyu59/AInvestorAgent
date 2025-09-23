# backend/scoring/weights.py
# 仅提供“权重配置”的最小实现，保持与现有 routers/scores.py 的导入契约一致
from __future__ import annotations
from typing import Dict, Mapping, Optional
import os

# 预设多个版本，便于你在服务端切版本（例如在管理页或环境变量中切换）
WEIGHTS: Dict[str, Mapping[str, float]] = {
    # 你快车道里建议的默认版本
    "v1.0.0": {
        "value": 0.25,
        "quality": 0.20,
        "momentum": 0.35,
        "sentiment": 0.20,
        # 目前没有 risk 因子，先置 0 作为占位（将来有了可改成 >0 并同步前端雷达）
        "risk": 0.0,
    },
    # 你可以加更多版本做对比
    "balanced": {
        "value": 0.25,
        "quality": 0.25,
        "momentum": 0.25,
        "sentiment": 0.25,
        "risk": 0.0,
    },
}

# 当前生效版本（可通过环境变量覆盖）：SCORER_VERSION=v1.0.0
ACTIVE_VERSION: str = os.getenv("SCORER_VERSION", "v1.0.0")

def get_active_version() -> str:
    """返回当前版本标签"""
    return ACTIVE_VERSION if ACTIVE_VERSION in WEIGHTS else "v1.0.0"

def get_weights(version: Optional[str] = None) -> Mapping[str, float]:
    """
    取某个版本的权重；version 为空时取当前生效版本。
    始终返回包含 value/quality/momentum/sentiment/risk 的映射。
    """
    ver = (version or get_active_version())
    base = WEIGHTS.get(ver) or WEIGHTS["v1.0.0"]
    # 确保返回的 keys 完整
    return {
        "value": float(base.get("value", 0.0)),
        "quality": float(base.get("quality", 0.0)),
        "momentum": float(base.get("momentum", 0.0)),
        "sentiment": float(base.get("sentiment", 0.0)),
        "risk": float(base.get("risk", 0.0)),
    }

__all__ = ["WEIGHTS", "get_weights", "get_active_version"]
