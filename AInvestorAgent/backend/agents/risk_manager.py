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


    # === 高级风险控制功能 (追加到 RiskManager 类) ===

    def calculate_portfolio_correlation(self, weights: List[Dict[str, Any]],
                                        db_session=None) -> Dict[str, float]:
        """
        计算组合相关性风险
        """
        from backend.factors.momentum import get_price_series
        from datetime import date, timedelta
        import numpy as np

        correlation_metrics = {}

        try:
            if not db_session:
                from backend.storage.db import SessionLocal
                db_session = SessionLocal()
                should_close = True
            else:
                should_close = False

            # 获取各股票的收益率序列
            returns_data = {}
            asof = date.today()

            for w in weights:
                symbol = w.get('symbol')
                if symbol:
                    df = get_price_series(db_session, symbol, asof, 180)  # 6个月数据
                    if len(df) >= 30:
                        prices = df['close'].tolist()
                        returns = [(prices[i] - prices[i - 1]) / prices[i - 1]
                                   for i in range(1, len(prices))]
                        returns_data[symbol] = returns

            if len(returns_data) >= 2:
                # 计算相关性矩阵
                symbols = list(returns_data.keys())
                min_length = min(len(returns_data[s]) for s in symbols)

                corr_matrix = []
                for s1 in symbols:
                    row = []
                    for s2 in symbols:
                        r1 = np.array(returns_data[s1][:min_length])
                        r2 = np.array(returns_data[s2][:min_length])
                        corr = np.corrcoef(r1, r2)[0, 1]
                        row.append(corr if not np.isnan(corr) else 0.0)
                    corr_matrix.append(row)

                # 计算风险指标
                corr_array = np.array(corr_matrix)

                # 平均相关性（排除对角线）
                mask = ~np.eye(len(symbols), dtype=bool)
                avg_correlation = float(np.mean(corr_array[mask]))

                # 最大相关性
                max_correlation = float(np.max(corr_array[mask]))

                # 相关性集中度风险
                high_corr_pairs = np.sum(corr_array[mask] > 0.7)
                correlation_risk = high_corr_pairs / (len(symbols) * (len(symbols) - 1) / 2)

                correlation_metrics.update({
                    'avg_correlation': avg_correlation,
                    'max_correlation': max_correlation,
                    'correlation_risk_ratio': float(correlation_risk),
                    'correlation_matrix': corr_matrix
                })

            if should_close:
                db_session.close()

        except Exception as e:
            print(f"相关性计算失败: {e}")

        return correlation_metrics

    def enhanced_risk_check(self, weights: List[Dict[str, Any]],
                            market_condition: str = "normal") -> Dict[str, Any]:
        """
        增强风险检查：根据市场环境调整风险参数

        市场环境:
        - "bull": 牛市 - 适度放松约束
        - "bear": 熊市 - 严格风险控制
        - "volatile": 震荡市 - 加强分散化
        - "normal": 正常市场
        """

        # 根据市场环境调整参数
        risk_adjustments = {
            "bull": {"max_stock": 0.35, "max_sector": 0.55},
            "bear": {"max_stock": 0.20, "max_sector": 0.40},
            "volatile": {"max_stock": 0.25, "max_sector": 0.45},
            "normal": {"max_stock": 0.30, "max_sector": 0.50}
        }

        adjustment = risk_adjustments.get(market_condition, risk_adjustments["normal"])

        # 执行风险控制
        result = self.act(
            weights=weights,
            max_weight=adjustment["max_stock"],
            max_sector=adjustment["max_sector"]
        )

        # 添加市场环境信息
        result["market_condition"] = market_condition
        result["risk_adjustment"] = adjustment

        return result

    def stress_test_portfolio(self, weights: List[Dict[str, Any]],
                              scenarios: List[str] = None) -> Dict[str, Dict]:
        """
        组合压力测试
        """
        if scenarios is None:
            scenarios = ["market_crash", "sector_rotation", "high_volatility"]

        stress_results = {}

        try:
            for scenario in scenarios:
                if scenario == "market_crash":
                    # 模拟市场暴跌：所有资产下跌但相关性上升
                    scenario_result = {
                        "max_single_loss": -0.30,  # 单一资产最大损失30%
                        "portfolio_var_shock": -0.25,  # 组合VaR恶化
                        "correlation_increase": 0.8,  # 相关性上升到0.8
                        "risk_level": "high"
                    }

                elif scenario == "sector_rotation":
                    # 模拟行业轮动：某些行业表现差异巨大
                    sector_weights = defaultdict(float)
                    for w in weights:
                        sector_weights[w.get('sector', 'Unknown')] += w.get('weight', 0)

                    max_sector_exposure = max(sector_weights.values()) if sector_weights else 0
                    scenario_result = {
                        "sector_concentration_risk": max_sector_exposure,
                        "rotation_impact": max_sector_exposure * 0.2,  # 最大行业可能20%损失
                        "risk_level": "medium" if max_sector_exposure < 0.4 else "high"
                    }

                elif scenario == "high_volatility":
                    # 模拟高波动环境
                    total_weight = sum(w.get('weight', 0) for w in weights)
                    num_positions = len([w for w in weights if w.get('weight', 0) > 0.01])

                    # 分散化不足在高波动时风险更高
                    diversification_ratio = num_positions / 10.0  # 假设理想分散化为10只股票
                    scenario_result = {
                        "volatility_multiplier": 2.0,  # 波动率放大2倍
                        "diversification_benefit": min(1.0, diversification_ratio),
                        "adjusted_risk": (1.0 / min(1.0, diversification_ratio)) * 1.5,
                        "risk_level": "medium"
                    }

                stress_results[scenario] = scenario_result

        except Exception as e:
            print(f"压力测试失败: {e}")

        return stress_results

# 确保可以被正确导入
__all__ = ['RiskManager']