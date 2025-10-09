# backend/api/routers/symbols.py
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os

router = APIRouter(prefix="/api/symbols", tags=["symbols"])


class SymbolResult(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None


class SymbolSearchResponse(BaseModel):
    results: List[SymbolResult]


# 常见美股列表 (可扩展到数据库)
COMMON_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 2800000000000},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 2500000000000},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 1700000000000},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer", "exchange": "NASDAQ",
     "market_cap": 1500000000000},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 1200000000000},
    {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 900000000000},
    {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Automotive", "exchange": "NASDAQ", "market_cap": 800000000000},
    {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc.", "sector": "Financial", "exchange": "NYSE",
     "market_cap": 750000000000},
    {"symbol": "V", "name": "Visa Inc.", "sector": "Financial", "exchange": "NYSE", "market_cap": 500000000000},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "exchange": "NYSE",
     "market_cap": 450000000000},
    {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Consumer", "exchange": "NYSE", "market_cap": 400000000000},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial", "exchange": "NYSE",
     "market_cap": 450000000000},
    {"symbol": "MA", "name": "Mastercard Inc.", "sector": "Financial", "exchange": "NYSE", "market_cap": 380000000000},
    {"symbol": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer", "exchange": "NYSE",
     "market_cap": 360000000000},
    {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "sector": "Healthcare", "exchange": "NYSE",
     "market_cap": 450000000000},
    {"symbol": "HD", "name": "The Home Depot Inc.", "sector": "Consumer", "exchange": "NYSE",
     "market_cap": 350000000000},
    {"symbol": "DIS", "name": "The Walt Disney Company", "sector": "Media", "exchange": "NYSE",
     "market_cap": 200000000000},
    {"symbol": "BAC", "name": "Bank of America Corp.", "sector": "Financial", "exchange": "NYSE",
     "market_cap": 280000000000},
    {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Media", "exchange": "NASDAQ", "market_cap": 180000000000},
    {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology", "exchange": "NASDAQ", "market_cap": 250000000000},
    {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology", "exchange": "NYSE",
     "market_cap": 220000000000},
    {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 180000000000},
    {"symbol": "AVGO", "name": "Broadcom Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 500000000000},
    {"symbol": "ORCL", "name": "Oracle Corporation", "sector": "Technology", "exchange": "NYSE",
     "market_cap": 280000000000},
    {"symbol": "CSCO", "name": "Cisco Systems Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 200000000000},
    {"symbol": "INTC", "name": "Intel Corporation", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 180000000000},
    {"symbol": "QCOM", "name": "QUALCOMM Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 190000000000},
    {"symbol": "TXN", "name": "Texas Instruments Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 170000000000},
    {"symbol": "IBM", "name": "International Business Machines", "sector": "Technology", "exchange": "NYSE",
     "market_cap": 160000000000},
    {"symbol": "UBER", "name": "Uber Technologies Inc.", "sector": "Technology", "exchange": "NYSE",
     "market_cap": 120000000000},
    {"symbol": "ABNB", "name": "Airbnb Inc.", "sector": "Consumer", "exchange": "NASDAQ", "market_cap": 80000000000},
    {"symbol": "SNOW", "name": "Snowflake Inc.", "sector": "Technology", "exchange": "NYSE", "market_cap": 60000000000},
    {"symbol": "SPOT", "name": "Spotify Technology S.A.", "sector": "Media", "exchange": "NYSE",
     "market_cap": 50000000000},
    {"symbol": "SQ", "name": "Block Inc.", "sector": "Financial", "exchange": "NYSE", "market_cap": 40000000000},
    {"symbol": "SHOP", "name": "Shopify Inc.", "sector": "Technology", "exchange": "NYSE", "market_cap": 80000000000},
    {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Financial", "exchange": "NASDAQ",
     "market_cap": 70000000000},
    {"symbol": "COIN", "name": "Coinbase Global Inc.", "sector": "Financial", "exchange": "NASDAQ",
     "market_cap": 50000000000},
    {"symbol": "RBLX", "name": "Roblox Corporation", "sector": "Technology", "exchange": "NYSE",
     "market_cap": 30000000000},
    {"symbol": "ZM", "name": "Zoom Video Communications", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 20000000000},
    {"symbol": "DOCU", "name": "DocuSign Inc.", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 15000000000},
    # 关键：添加 AppLovin
    {"symbol": "APP", "name": "AppLovin Corporation", "sector": "Technology", "exchange": "NASDAQ",
     "market_cap": 30000000000},
]


def search_symbols(query: str, max_results: int = 10) -> List[SymbolResult]:
    """
    搜索股票代码和名称
    支持模糊匹配代码和公司名称
    """
    query_upper = query.upper()
    query_lower = query.lower()

    results = []

    for stock in COMMON_STOCKS:
        # 精确匹配代码
        if stock["symbol"] == query_upper:
            results.insert(0, SymbolResult(**stock))
            continue

        # 代码前缀匹配
        if stock["symbol"].startswith(query_upper):
            results.append(SymbolResult(**stock))
            continue

        # 公司名称包含匹配 (不区分大小写)
        if query_lower in stock["name"].lower():
            results.append(SymbolResult(**stock))
            continue

    return results[:max_results]


@router.get("", response_model=SymbolSearchResponse)
def search_stock_symbols(
        q: str = Query(..., min_length=1, description="搜索关键词(股票代码或公司名称)"),
        limit: int = Query(10, ge=1, le=50, description="返回结果数量")
):
    """
    搜索股票代码

    - **q**: 搜索关键词，可以是股票代码(如 AAPL)或公司名称(如 Apple)
    - **limit**: 最多返回的结果数量

    示例:
    - /api/symbols?q=APP
    - /api/symbols?q=apple
    - /api/symbols?q=tech
    """
    try:
        results = search_symbols(q, limit)
        return SymbolSearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/popular", response_model=SymbolSearchResponse)
def get_popular_symbols(limit: int = Query(20, ge=1, le=100)):
    """
    获取热门股票列表
    """
    results = [SymbolResult(**stock) for stock in COMMON_STOCKS[:limit]]
    return SymbolSearchResponse(results=results)