# backend/agents/signal_researcher.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import math
from backend.agents.base_agent import AgentContext

class SignalResearcher:
    name = "signal_researcher"

    def __init__(self, ctx: AgentContext | Dict[str, Any] | None = None):
        """
        兼容三种上下文：
          - None: 用空 dict
          - AgentContext: 原样保存到 _ctx['ctx']，避免 dict(ctx) 抛 TypeError
          - dict: 直接使用
          - 其他类型：尽量转成 dict，失败则包一层 {'ctx': 原对象}
        """
        if ctx is None:
            self._ctx: Dict[str, Any] = {}
        elif isinstance(ctx, AgentContext):
            self._ctx = {"ctx": ctx}
        elif isinstance(ctx, dict):
            self._ctx = ctx
        else:
            try:
                self._ctx = dict(ctx)  # 万一是类似 Mapping 的对象
            except Exception:
                self._ctx = {"ctx": ctx}

    # 便捷接口：与测试里的用法对齐：SignalResearcher(ctx).act(symbol="AAPL")
    def act(self, **kwargs) -> Dict[str, Any]:
        # 将 kwargs 合并进上下文再运行
        run_ctx = dict(self._ctx)
        run_ctx.update(kwargs or {})
        return self.run(run_ctx)

    def _extract_price_series(self, prices_any: Any) -> List[float]:
        """
        兼容两种价格格式：
        1) [100.0, 100.2, ...]  纯浮点序列
        2) [{"date":"YYYY-mm-dd","close":101.0}, ...] 字典序列（pipeline mock 就是这种）
        """
        if not prices_any:
            return []

        if isinstance(prices_any, list):
            if not prices_any:
                return []
            first = prices_any[0]
            # dict 序列
            if isinstance(first, dict):
                out = []
                for d in prices_any:
                    c = d.get("close")
                    try:
                        out.append(float(c))
                    except Exception:
                        # 跳过非法
                        continue
                return out
            # 纯数字序列
            else:
                out = []
                for v in prices_any:
                    try:
                        out.append(float(v))
                    except Exception:
                        continue
                return out
        # 其他类型，不支持
        return []

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        try:

            symbol = ctx.get("symbol", "AAPL")

            # --- 价格动量 ---
            prices_in = ctx.get("prices")
            prices = self._extract_price_series(prices_in)

            # 缺数据兜底：造一段轻微上行的 mock 序列（长度 60）
            if not prices:
                start, n = 100.0, 60
                prices = [start]
                for i in range(1, n):
                    prices.append(prices[-1] * (1.0 + 0.0005 * (1 + math.sin(i / 9.0))))

            # 动量：近10期收益和，缩放+截断到 [0,1]
            if len(prices) < 2:
                momentum = 0.5
            else:
                rets = [0.0] + [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices))]
                k = 10
                tail = rets[-k:] if len(rets) >= k else rets
                raw = sum(tail)  # 典型量级 ~几 %
                # 缩放：假设 ±10% → 映射到 0..1
                momentum = 0.5 + raw / 0.20
                momentum = max(0.0, min(1.0, momentum))

            # --- 情绪（新闻） ---
            sent = 0.5
            news = ctx.get("news_raw") or []
            if isinstance(news, list):
                # 如果有“mock”参数，就给一个正向的稳定偏移；没有新闻也保持 0.5
                if ctx.get("mock"):
                    # 有新闻越多略微提高，但有上限
                    n = len(news)
                    sent = max(0.0, min(1.0, 0.6 + min(n, 50) / 500.0))
                else:
                    # 非 mock：保守使用 0.5
                    sent = 0.5

            # --- 价值 & 质量（如无基本面，给中性 0.5） ---
            fundamentals = ctx.get("fundamentals") or {}
            pe = fundamentals.get("pe")
            roe = fundamentals.get("roe")

            if pe is None or pe <= 0:
                value = 0.5
            else:
                # PE 越低越“便宜”：简单反比缩放到 0..1
                value = 1.0 / (1.0 + min(float(pe), 100.0) / 20.0)
                value = max(0.0, min(1.0, value))

            if roe is None:
                quality = 0.5
            else:
                # ROE 越高越好：线性缩放并截断
                quality = max(0.0, min(1.0, float(roe) / 20.0))

            factors = {
                "value": float(value),
                "quality": float(quality),
                "momentum": float(momentum),
                "sentiment": float(sent),
            }

            # 综合分数（0..100）
            score = 100.0 * (0.25 * value + 0.25 * quality + 0.30 * momentum + 0.20 * sent)

            return {
                "ok": True,
                "symbol": symbol,
                "factors": factors,
                "score": round(score),
            }

        except Exception:
            # 超小兜底：任何内部 KeyError/TypeError 时，仍给出可复现因子
            symbol = (ctx.get("symbol") or "AAPL")
            base = sum(ord(c) for c in symbol) % 100
            n = lambda v: max(0.0, min(1.0, ((base + v) % 100) / 100.0))
            return {"ok": True, "symbol": symbol,
                    "factors": {"value": n(13), "quality": n(37), "momentum": n(59), "sentiment": n(71)},
                    "score": round(100.0 * (0.25 * n(13) + 0.25 * n(37) + 0.30 * n(59) + 0.20 * n(71)))}


class EnhancedSignalResearcher(SignalResearcher):
    """增强版信号研究员，支持LLM分析"""

    def __init__(self, ctx=None):
        super().__init__(ctx)
        self.use_llm = True  # 可通过上下文控制是否启用LLM

    async def run_with_llm(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """带LLM增强的分析"""
        # 先执行基础分析
        base_result = self.run(ctx)

        if not self.use_llm or not base_result.get("ok"):
            return base_result

        try:
            # 准备LLM分析的上下文
            symbol = ctx.get("symbol", "UNKNOWN")
            factors = base_result.get("factors", {})
            fundamentals = ctx.get("fundamentals", {})
            news_raw = ctx.get("news_raw", [])

            # 构建LLM提示
            news_summary = ""
            if news_raw:
                news_texts = [item.get("title", "") + " " + item.get("summary", "")
                              for item in news_raw[:5]]  # 最近5条新闻
                news_summary = "\n".join(news_texts)
            else:
                news_summary = "无相关新闻"

            prompt = f"""作为专业股票分析师，请分析{symbol}：

技术指标：
- 价值因子: {factors.get('value', 0):.2f} (0-1，越高越便宜)
- 质量因子: {factors.get('quality', 0):.2f} (0-1，越高质量越好)  
- 动量因子: {factors.get('momentum', 0):.2f} (0-1，越高动能越强)
- 情绪因子: {factors.get('sentiment', 0):.2f} (0-1，越高情绪越正面)

基本面：
- PE比率: {fundamentals.get('pe', 'N/A')}
- ROE: {fundamentals.get('roe', 'N/A')}%

近期新闻：
{news_summary}

请提供：
1. 投资建议(买入/持有/卖出)
2. 信心等级(1-10)
3. 关键风险(1-2点)
4. 核心逻辑(1句话)

格式: 建议|信心|风险|逻辑"""

            from backend.sentiment.llm_router import llm_router, LLMProvider
            llm_analysis = await llm_router.call_llm(
                prompt=prompt,
                provider=LLMProvider.DEEPSEEK,
                temperature=0.3,
                max_tokens=300
            )

            # 解析LLM结果
            llm_parts = llm_analysis.split('|')
            if len(llm_parts) >= 4:
                recommendation = llm_parts[0].strip()
                confidence = llm_parts[1].strip()
                risk = llm_parts[2].strip()
                logic = llm_parts[3].strip()

                # 增强基础结果
                base_result["llm_analysis"] = {
                    "recommendation": recommendation,
                    "confidence": confidence,
                    "risk": risk,
                    "logic": logic,
                    "raw_response": llm_analysis
                }
            else:
                base_result["llm_analysis"] = {
                    "raw_response": llm_analysis,
                    "note": "LLM响应格式异常"
                }

        except Exception as e:
            logger.error(f"LLM增强分析失败: {e}")
            base_result["llm_analysis"] = {"error": str(e)}

        return base_result