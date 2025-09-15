# backend/agents/risk_manager.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent
from collections import defaultdict
from dataclasses import dataclass

class RiskManager:
    name = "risk_manager"

    def __init__(self, ctx: Dict[str, Any] | None = None):
        self._ctx = dict(ctx or {})

    def _norm_params(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        # 全部取自传入 ctx，给稳健默认值
        return {
            "max_stock": float(ctx.get("risk.max_stock", 0.30)),
            "max_sector": float(ctx.get("risk.max_sector", 0.50)),
            "count_range": tuple(ctx.get("risk.count_range", (5, 15))),
        }

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        risk = self._norm_params(ctx)

        # 优先取已有权重；没有就按 candidates/equal 补一份
        weights = ctx.get("weights")
        if not weights:
            items = (ctx.get("proposal") or {}).get("items") or ctx.get("candidates") or []
            syms = [x["symbol"] for x in items][:risk["count_range"][1]]
            if not syms:
                return {"ok": False, "data": {}}
            w = 1.0 / len(syms)
            weights = [{"symbol": s, "weight": w} for s in syms]

        # 单票上限裁剪 + 归一化
        capped = []
        for w in weights:
            v = min(float(w["weight"]), risk["max_stock"])
            capped.append({"symbol": w["symbol"], "weight": v, "sector": w.get("sector")})
        total = sum(x["weight"] for x in capped) or 1.0
        kept = [{"symbol": x["symbol"], "weight": x["weight"] / total} for x in capped]

        return {"ok": True, "data": {"kept": kept, "weights": kept}}
