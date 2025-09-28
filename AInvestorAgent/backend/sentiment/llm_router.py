# backend/sentiment/llm_router.py
import os
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"


class LLMRouter:
    """统一的LLM路由器，支持DeepSeek和豆包(ARK)"""

    def __init__(self):
        self.deepseek_config = {
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "api_url": os.getenv("DEEPSEEK_API_URL"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        }
        self.doubao_config = {
            "api_key": os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY"),
            "api_url": os.getenv("DOUBAO_API_URL") or os.getenv("ARK_API_URL"),
            "model": os.getenv("DOUBAO_MODEL") or os.getenv("ARK_API_MODEL")
        }

    async def call_llm(self,
                       prompt: str,
                       provider: LLMProvider = LLMProvider.DEEPSEEK,
                       system_prompt: str = None,
                       temperature: float = 0.7,
                       max_tokens: int = 1000) -> str:
        """调用指定的LLM提供商"""

        config = self.deepseek_config if provider == LLMProvider.DEEPSEEK else self.doubao_config

        if not config["api_key"]:
            logger.warning(f"LLM {provider.value} API密钥未配置")
            return f"LLM {provider.value} 未配置"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(config["api_url"],
                                        json=payload,
                                        headers=headers,
                                        timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        logger.error(f"LLM API错误 {response.status}: {error_text}")
                        return f"LLM调用失败: HTTP {response.status}"
        except Exception as e:
            logger.error(f"LLM调用异常: {e}")
            return f"LLM调用失败: {str(e)}"

    async def analyze_sentiment_with_llm(self, news_texts: List[str], provider: LLMProvider = LLMProvider.DEEPSEEK) -> \
    List[float]:
        """使用LLM分析新闻情绪"""
        if not news_texts:
            return []

        # 批量分析，每次最多10条新闻
        batch_size = 10
        results = []

        for i in range(0, len(news_texts), batch_size):
            batch = news_texts[i:i + batch_size]
            batch_text = "\n".join([f"{j + 1}. {text}" for j, text in enumerate(batch)])

            prompt = f"""请分析以下新闻的市场情绪，对每条新闻给出-1到1之间的情绪分数：
-1表示极度负面(大跌、危机、亏损)
0表示中性
1表示极度正面(大涨、突破、利好)

新闻内容：
{batch_text}

请只返回数字分数，每行一个，格式如下：
0.3
-0.5
0.8"""

            try:
                response = await self.call_llm(prompt, provider, temperature=0.3, max_tokens=200)
                scores = []
                for line in response.strip().split('\n'):
                    try:
                        score = float(line.strip())
                        scores.append(max(-1.0, min(1.0, score)))  # 确保在[-1,1]范围内
                    except ValueError:
                        scores.append(0.0)  # 解析失败时给中性分

                # 补齐批次大小
                while len(scores) < len(batch):
                    scores.append(0.0)

                results.extend(scores)
            except Exception as e:
                logger.error(f"情绪分析失败: {e}")
                # 失败时给所有新闻中性分
                results.extend([0.0] * len(batch))

        return results

    async def analyze_stock_comprehensive(self, symbol: str,
                                          factors: Dict[str, float],
                                          fundamentals: Dict[str, any],
                                          technical_indicators: Dict[str, float],
                                          news_summary: str = "",
                                          provider: LLMProvider = LLMProvider.DEEPSEEK) -> Dict[str, any]:
        """综合分析股票"""

        prompt = f"""作为专业股票分析师，请分析 {symbol}：

基本面因子：
- 价值因子: {factors.get('value', 0):.2f} (0-1，越高越便宜)
- 质量因子: {factors.get('quality', 0):.2f} (0-1，越高质量越好)  
- 动量因子: {factors.get('momentum', 0):.2f} (0-1，越高动能越强)
- 情绪因子: {factors.get('sentiment', 0):.2f} (0-1，越高情绪越正面)

技术指标：
- RSI: {technical_indicators.get('rsi', 0):.1f}
- 5日均线: {technical_indicators.get('ma5', 0):.2f}
- 20日均线: {technical_indicators.get('ma20', 0):.2f}
- 年化波动率: {technical_indicators.get('annual_volatility', 0):.1%}
- 动量评分: {technical_indicators.get('momentum_score', 0):.2f}

基本面数据：
- PE比率: {fundamentals.get('pe', 'N/A')}
- ROE: {fundamentals.get('roe', 'N/A')}%
- 市值: {fundamentals.get('market_cap', 'N/A')}

近期新闻摘要：
{news_summary or '无相关新闻'}

请提供：
1. 投资建议(强烈买入/买入/持有/卖出/强烈卖出)
2. 信心等级(1-10)
3. 关键风险点(最多2点)
4. 投资逻辑(1句话概括)

格式: 建议|信心|风险|逻辑"""

        try:
            response = await self.call_llm(
                prompt=prompt,
                provider=provider,
                temperature=0.3,
                max_tokens=400
            )

            # 解析响应
            parts = response.replace('｜', '|').split('|')
            if len(parts) >= 4:
                return {
                    "recommendation": parts[0].strip(),
                    "confidence": parts[1].strip(),
                    "risks": parts[2].strip(),
                    "logic": parts[3].strip(),
                    "raw_response": response
                }
            else:
                return {
                    "raw_response": response,
                    "note": "LLM响应格式需要调整"
                }

        except Exception as e:
            logger.error(f"综合分析失败: {e}")
            return {"error": str(e)}

    async def generate_portfolio_reasoning(self,
                                           analyses: Dict[str, Dict],
                                           selected_symbols: List[str],
                                           provider: LLMProvider = LLMProvider.DOUBAO) -> str:
        """生成组合选择理由"""

        summary_parts = []
        for symbol in selected_symbols:
            analysis = analyses.get(symbol, {})
            factors = analysis.get("factors", {})
            llm_analysis = analysis.get("llm_analysis", {})

            summary_parts.append(f"""
{symbol}: 评分{analysis.get('score', 0)}, 建议{llm_analysis.get('recommendation', 'N/A')}
因子: 价值{factors.get('value', 0):.2f} 质量{factors.get('quality', 0):.2f} 动量{factors.get('momentum', 0):.2f}
逻辑: {llm_analysis.get('logic', '数据驱动选择')}""")

        analysis_text = "\n".join(summary_parts)

        prompt = f"""作为投资组合经理，基于以下分析解释组合构建逻辑：

选中股票分析：
{analysis_text}

请用1-2句话概括选择这些股票的核心逻辑，重点说明：
1. 选择标准
2. 风险考虑
3. 预期表现"""

        try:
            reasoning = await self.call_llm(
                prompt=prompt,
                provider=provider,
                temperature=0.4,
                max_tokens=200
            )
            return reasoning.strip()
        except Exception as e:
            logger.error(f"组合理由生成失败: {e}")
            return f"基于多因子模型选择评分最高的{len(selected_symbols)}只股票，兼顾价值、质量、动量和情绪因子。"

# 全局单例
llm_router = LLMRouter()