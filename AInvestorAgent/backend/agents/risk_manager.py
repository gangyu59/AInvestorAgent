# backend/agents/risk_manager.py - 完整版本
from __future__ import annotations
from typing import Dict, Any, List
from collections import defaultdict

class RiskManager:
    name = "risk_manager"

    def __init__(self, ctx: Any | None = None):
        if ctx is None:
            self._ctx = {}
        elif isinstance(ctx, dict):
            self._ctx = ctx
        else:
            # 兼容 AgentContext 或其他对象，直接存引用
            self._ctx = {"ctx": ctx}

    def _norm_params(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "max_stock": float(ctx.get("risk.max_stock", 0.30)),
            "max_sector": float(ctx.get("risk.max_sector", 0.50)),
            "count_range": tuple(ctx.get("risk.count_range", (5, 15))),
        }

    def act(self, *, weights: List[Dict[str, Any]], max_weight: float = 0.30, max_sector: float = 0.50) -> Dict[str, Any]:
        """
        便捷风控：接受权重列表与阈值，复用 run(ctx) 的完整风控逻辑。
        - weights: [{"symbol": "...", "weight": 0.5, ("sector": "...")}, ...]
        - max_weight: 单票上限（对应 risk.max_stock）
        - max_sector: 行业上限（对应 risk.max_sector）
        返回: {"ok": True/False, "weights": {symbol: weight, ...}}
        """
        ctx: Dict[str, Any] = {
            "weights": weights,
            "risk.max_stock": float(max_weight),
            "risk.max_sector": float(max_sector),
            # 对 act 场景，数量上限给到当前长度，避免被无端裁剪
            "risk.count_range": (1, max(1, len(weights))),
        }
        out = self.run(ctx)
        if not out.get("ok"):
            return {"ok": False, "weights": {}}

        data = out.get("data", {})
        kept = data.get("weights") or data.get("kept") or []
        # 单测期望 dict: {symbol: weight}
        mapped = {w["symbol"]: float(w["weight"]) for w in kept}
        return {"ok": True, "weights": mapped}

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        risk = self._norm_params(ctx)

        # --- 1) 组装候选 + 映射，确保能拿到 sector ---
        candidates: List[Dict[str, Any]] = ctx.get("candidates") or []
        sym2sector: Dict[str, str] = {}
        for x in candidates:
            sec = x.get("sector")
            if sec:
                sym2sector[str(x.get("symbol"))] = sec

        # --- 2) 准备初始权重（优先用 candidates；必要时用 proposal.items 并回填 sector） ---
        weights = ctx.get("weights")
        if not weights:
            proposal = ctx.get("proposal")

            if candidates:
                items = candidates[: risk["count_range"][1]]
            else:
                # 兼容 proposal: dict(list) 两种形态
                if isinstance(proposal, dict):
                    items = (proposal.get("items") or [])[: risk["count_range"][1]]
                elif isinstance(proposal, list):
                    items = proposal[: risk["count_range"][1]]
                else:
                    items = []

            if not items:
                return {"ok": False, "data": {}}

            w0 = 1.0 / len(items)
            weights = []
            for it in items:
                sym = it.get("symbol")
                sec = it.get("sector") or sym2sector.get(sym) or "Unknown"
                weights.append({"symbol": sym, "weight": w0, "sector": sec})
        else:
            # 外部传入的 weights 若没带 sector，则用 candidates 映射补齐
            fixed = []
            for w in weights:
                sym = w["symbol"]
                sec = w.get("sector") or sym2sector.get(sym) or "Unknown"
                fixed.append({"symbol": sym, "weight": float(w["weight"]), "sector": sec})
            weights = fixed

        # --- 3) 单票上限裁剪 ---
        per_capped = []
        for w in weights:
            v = min(float(w["weight"]), risk["max_stock"])
            per_capped.append({"symbol": w["symbol"], "weight": v, "sector": w["sector"] or "Unknown"})

        # --- 4) 行业集中度约束（保证任何行业 ≤ max_sector） ---
        # 4.1 统计行业原始权重
        sector_totals: Dict[str, float] = defaultdict(float)
        sector_to_stocks: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for x in per_capped:
            sector_totals[x["sector"]] += x["weight"]
            sector_to_stocks[x["sector"]].append(x)

        # 4.2 先把超限行业直接 Cap 到上限，未超限行业保留原总权重
        max_sec = risk["max_sector"]
        capped_sector_total: Dict[str, float] = {}
        removed = 0.0
        keepers_total = 0.0
        for sec, tot in sector_totals.items():
            if tot > max_sec:
                capped_sector_total[sec] = max_sec
                removed += (tot - max_sec)
            else:
                capped_sector_total[sec] = tot
                keepers_total += tot

        # 4.3 把"被削掉的权重"按照未超限行业的原始占比重新分配到它们
        if removed > 1e-12 and keepers_total > 1e-12:
            for sec, tot in sector_totals.items():
                if tot <= max_sec:
                    share = tot / keepers_total
                    capped_sector_total[sec] += removed * share
        # （如果所有行业都超限或只有一个行业，removed 会为 0 或 keepers_total=0，直接跳过即可）

        # 4.4 按"目标行业总权重"把行业内的股票等比缩放
        adjusted: List[Dict[str, Any]] = []
        for sec, stocks in sector_to_stocks.items():
            base = sum(s["weight"] for s in stocks) or 1.0
            target_sec_sum = capped_sector_total.get(sec, 0.0)
            for s in stocks:
                share = s["weight"] / base
                adjusted.append({"symbol": s["symbol"], "sector": sec, "weight": target_sec_sum * share})

        # --- 5) 只对"未被行业 Cap 的部分"做全局归一化（不会把被 Cap 的行业又抬回去） ---
        # 实际上 4.4 已经把每个行业精确分配到目标和；这里仅防数值误差统一归一
        total = sum(x["weight"] for x in adjusted) or 1.0
        kept = [{"symbol": x["symbol"], "sector": x["sector"], "weight": x["weight"] / total} for x in adjusted]

        # --- 6) 输出行业分布 & actions 占位 ---
        sector_dist: Dict[str, float] = defaultdict(float)
        for k in kept:
            sector_dist[k["sector"]] += k["weight"]

        concentration = {"sector_dist": dict(sector_dist)}
        actions: List[Dict[str, Any]] = []

        return {
            "ok": True,
            "data": {
                "kept": kept,
                "weights": kept,
                "concentration": concentration,
                "actions": actions,
            },
        }

# 确保可以被正确导入
__all__ = ['RiskManager']