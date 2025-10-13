# backend/agents/portfolio_manager.py
from __future__ import annotations
from typing import Dict, Any
import re
import logging
logger = logging.getLogger(__name__)


# --- sector lookup (轻量缓存；后续可替换为从 DB/基本面表查询) ---
_SECTOR_CACHE = {
    # --- Technology / Comm ---
    "AAPL":"Technology","MSFT":"Technology","NVDA":"Technology","AMD":"Technology","AVGO":"Technology","ORCL":"Technology",
    "GOOGL":"Communication Services","GOOG":"Communication Services","META":"Communication Services",
    # --- Consumer Discretionary / Staples ---
    "AMZN":"Consumer Discretionary","TSLA":"Consumer Discretionary","PDD":"Consumer Discretionary","BABA":"Consumer Discretionary",
    "HD":"Consumer Discretionary","NKE":"Consumer Discretionary","COST":"Consumer Staples",
    # --- Financials ---
    "JPM":"Financials","BAC":"Financials","WFC":"Financials","C":"Financials","V":"Financials","MA":"Financials",
    # --- Industrials ---
    "CAT":"Industrials","HON":"Industrials","UNP":"Industrials",
    # --- Energy ---
    "XOM":"Energy","CVX":"Energy","COP":"Energy","SLB":"Energy","EOG":"Energy",
    # --- Materials ---
    "BHP":"Materials","RIO":"Materials","FCX":"Materials","NEM":"Materials","SCCO":"Materials","LIN":"Materials",
    # --- Utilities / REITs ---
    "NEE":"Utilities","DUK":"Utilities","SO":"Utilities","D":"Utilities","EXC":"Utilities","AMT":"Real Estate",
    "JNJ": "Health Care",
    "PFE": "Health Care",
    "LYFT": "Industrials",
}


def lookup_sector(symbol: str) -> str:
    if not symbol:
        return "Unknown"
    return _SECTOR_CACHE.get(symbol.upper(), "Unknown")


def _attach_sector(weights: list[dict]) -> list[dict]:
    """
    给每个 weight dict 补全 sector 字段；已存在且非 Unknown 的不覆盖
    """
    for w in weights:
        sec = (w.get("sector") or "").strip()
        if not sec or sec.lower() == "unknown":
            w["sector"] = lookup_sector(w.get("symbol"))
    return weights


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
        # ✅ 补全 sector
        weights = _attach_sector(weights)
        return {"ok": True, "weights": weights}


class EnhancedPortfolioManager(PortfolioManager):
    """增强版投资组合管理器，支持LLM决策"""

    async def smart_allocate(self, analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """使用LLM进行智能资产配置"""

        from backend.sentiment.llm_router import llm_router, LLMProvider

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

            llm_response = await llm_router.call_llm(
                prompt=prompt,
                provider=LLMProvider.DEEPSEEK,  # 使用 DEEPSEEK
                temperature=0.2,
                max_tokens=500
            )

            # 解析LLM响应
            # 解析LLM响应（先做全角->半角标准化）
            import re  # 若文件顶部没有，请在文件顶部的 import 区域补上一行：import re

            resp = (llm_response or "")
            resp = resp.replace('％', '%').replace('：', ':').replace('，', ',')
            lines = resp.strip().split('\n')

            weights = []
            reasoning = ""

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if ':' in line and '%' in line and '理由' not in line:
                    # 解析权重行：AAPL:25%,MSFT:20%,...
                    pairs = [p.strip() for p in line.split(',')]
                    for pair in pairs:
                        if ':' in pair and '%' in pair:
                            symbol, weight_str = pair.split(':', 1)
                            try:
                                weight = float(weight_str.replace('%', '').strip()) / 100.0
                                weights.append({
                                    "symbol": symbol.strip().upper(),
                                    "weight": min(0.3, max(0.0, weight))  # 单票上限先在这里夹一下
                                })
                            except ValueError:
                                continue

                elif '理由' in line:
                    m = re.search(r'理由[:：]\s*(.*)$', line)
                    if m:
                        reasoning = m.group(1).strip()

            # 权重标准化
            total_weight = sum(w["weight"] for w in weights)
            if total_weight > 0:
                for w in weights:
                    w["weight"] /= total_weight

            weights = _attach_sector(weights)

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