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


# 全局单例
llm_router = LLMRouter()