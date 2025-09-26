# backend/api/routers/llm.py
from fastapi import APIRouter, Query
from backend.sentiment.llm_router import llm_router, LLMProvider

router = APIRouter(prefix="/api/llm", tags=["llm"])

@router.get("/ping")
async def llm_ping(provider: str = Query("deepseek", pattern="^(deepseek|doubao)$")):
    prov = LLMProvider.DEEPSEEK if provider == "deepseek" else LLMProvider.DOUBAO
    text = await llm_router.call_llm(
        prompt="返回一个很短的中文字符串：'OK'",
        provider=prov,
        system_prompt="你是一个严格输出的工具。",
        temperature=0.0,
        max_tokens=10,
    )
    return {"provider": provider, "result": text}
