# backend/agents/executor.py
from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class ExecConfig:
    trading_cost: float = 0.001  # 单边千分之一
    cash_buffer: float = 0.0     # 允许的现金余量占净值

class ExecutorAgent:
    name = "executor"

    def plan_orders(self, current: Dict[str, float], target: Dict[str, float]) -> List[Dict[str, Any]]:
        # 以“目标权重 - 当前权重”近似订单，正=买、负=卖
        symbols = set(current) | set(target)
        orders = []
        for sym in sorted(symbols):
            w0 = float(current.get(sym, 0.0))
            w1 = float(target.get(sym, 0.0))
            delta = round(w1 - w0, 8)
            if abs(delta) < 1e-8:
                continue
            side = "BUY" if delta > 0 else "SELL"
            orders.append({"symbol": sym, "side": side, "weight_delta": delta})
        return orders

    def run(self, ctx: Dict[str, Any], **params) -> Dict[str, Any]:
        cfg = ExecConfig(**{k: v for k, v in params.items() if k in {"trading_cost", "cash_buffer"}})
        kept = ctx.get("kept") or []  # 来自 PM/RM
        # 当前持仓（最小实现：从 ctx.current_weights 读取，无则默认为空仓）
        cur = {k["symbol"]: float(k.get("weight", 0)) for k in (ctx.get("current_weights") or [])}
        tgt = {k["symbol"]: float(k["weight"]) for k in kept}
        orders = self.plan_orders(cur, tgt)
        meta = {"tcost": cfg.trading_cost, "cash_buffer": cfg.cash_buffer}
        return {"ok": True, "data": {"orders": orders}, "meta": meta}
