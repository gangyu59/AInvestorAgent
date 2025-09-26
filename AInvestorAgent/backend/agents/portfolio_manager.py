# backend/agents/portfolio_manager.py
from __future__ import annotations
from typing import Dict, Any

class PortfolioManager:
    name = "portfolio_manager"

    def __init__(self, ctx: Any | None = None):
        if ctx is None:
            self._ctx = {}
        elif isinstance(ctx, dict):
            self._ctx = ctx
        else:
            # 兼容 AgentContext 或其他对象，直接存引用
            self._ctx = {"ctx": ctx}

    def act(self, scores: Dict[str, Dict[str, Any]], max_positions: int = 5) -> Dict[str, Any]:
        """
        从 scores 中挑选 topN 股票并分配等权重。
        """
        if not scores:
            return {"ok": False, "weights": []}

        # 按 score 排序
        ranked = sorted(scores.items(), key=lambda kv: kv[1].get("score", 0), reverse=True)
        top = ranked[:max_positions]

        n = len(top)
        if n == 0:
            return {"ok": False, "weights": []}

        w = 1.0 / n
        weights = [{"symbol": sym, "weight": w} for sym, _ in top]

        return {"ok": True, "weights": weights}


class EnhancedPortfolioManager(PortfolioManager):
    """增强版投资组合管理器，支持LLM决策"""

    async def smart_allocate(self, analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """使用LLM进行智能资产配置"""
        try:
            # 构建分析摘要
            summary_parts = []
            for symbol, analysis in analyses.items():
                factors = analysis.get("factors", {})
                llm_info = analysis.get("llm_analysis", {})

                summary_parts.append(f"""
{symbol}:
- 综合评分: {analysis.get('score', 0)}
- 价值/质量/动量/情绪: {factors.get('value', 0):.2f}/{factors.get('quality', 0):.2f}/{factors.get('momentum', 0):.2f}/{factors.get('sentiment', 0):.2f}
- AI建议: {llm_info.get('recommendation', 'N/A')}
- 信心度: {llm_info.get('confidence', 'N/A')}
- 核心逻辑: {llm_info.get('logic', 'N/A')}""")

            analysis_text = "\n".join(summary_parts)

            prompt = f"""作为投资组合经理，基于以下股票分析构建投资组合：

{analysis_text}

要求：
1. 选择5-10只股票构建组合
2. 单只股票权重≤30%
3. 权重总和=100%
4. 考虑风险分散

请按格式返回：
股票代码:权重%,股票代码:权重%,...
理由：简述选择逻辑"""

            from backend.sentiment.llm_router import llm_router, LLMProvider
            llm_response = await llm_router.call_llm(
                prompt=prompt,
                provider=LLMProvider.DOUBAO,  # 用豆包做组合决策
                temperature=0.2,
                max_tokens=500
            )

            # 解析LLM响应
            lines = llm_response.strip().split('\n')
            weights = []
            reasoning = ""

            for line in lines:
                if ':' in line and '%' in line and '理由' not in line:
                    # 解析权重行：AAPL:25%,MSFT:20%,...
                    pairs = line.split(',')
                    for pair in pairs:
                        if ':' in pair and '%' in pair:
                            symbol, weight_str = pair.split(':')
                            try:
                                weight = float(weight_str.replace('%', '')) / 100.0
                                weights.append({
                                    "symbol": symbol.strip().upper(),
                                    "weight": min(0.3, max(0.0, weight))  # 限制权重范围
                                })
                            except ValueError:
                                continue
                elif '理由' in line:
                    reasoning = line.split('理由：')[-1].strip()

            # 权重标准化
            total_weight = sum(w["weight"] for w in weights)
            if total_weight > 0:
                for w in weights:
                    w["weight"] /= total_weight

            # 如果LLM解析失败，回退到原有逻辑
            if not weights:
                return self.act(analyses, max_positions=8)

            return {
                "ok": True,
                "weights": weights,
                "reasoning": reasoning,
                "method": "llm_enhanced",
                "llm_response": llm_response
            }

        except Exception as e:
            logger.error(f"智能资产配置失败: {e}")
            # 回退到基础逻辑
            return self.act(analyses, max_positions=8)