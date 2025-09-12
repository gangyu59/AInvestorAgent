# backend/ingestion/alpha_vantage_client.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, TypedDict

from ..core.config import get_settings
from .utils import http_get_json

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageError(Exception):
    """AlphaVantage 相关错误（含速率限制/参数错误等）"""
    pass


class PriceRow(TypedDict):
    symbol: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: int
    dividend_amount: float
    split_coefficient: float


def _apikey() -> str:
    key = get_settings().ALPHAVANTAGE_KEY
    if not key:
        raise AlphaVantageError("缺少环境变量 ALPHAVANTAGE_KEY")
    return key


def _request(params: Dict[str, str]) -> Dict:
    """统一 GET 请求 + 基本错误处理"""
    data = http_get_json(BASE_URL, {**params, "apikey": _apikey()})
    if "Note" in data:
        # 免费版：~5 req/min，~500 req/day
        raise AlphaVantageError("AlphaVantage 速率限制：请稍后再试或升级账号。")
    if "Error Message" in data:
        raise AlphaVantageError(data["Error Message"])
    return data


def av_daily_raw(symbol: str, *, adjusted: bool = True, outputsize: str = "compact") -> Dict:
    """
    函数式：获取【日线】原始响应。
    adjusted=True 使用 TIME_SERIES_DAILY_ADJUSTED；否则 TIME_SERIES_DAILY
    outputsize: "compact" | "full"
    """
    fn = "TIME_SERIES_DAILY_ADJUSTED" if adjusted else "TIME_SERIES_DAILY"
    return _request({
        "function": fn,
        "symbol": symbol.upper(),
        "outputsize": outputsize,
        "datatype": "json",
    })


def normalize_daily(raw: Dict, symbol: str) -> List[PriceRow]:
    """
    将原始日线规约为列表（日期升序）。
    字段：symbol, date, open, high, low, close, volume, dividend_amount, split_coefficient
    """
    ts = raw.get("Time Series (Daily)") or {}
    rows: List[PriceRow] = []
    for d, ohlc in ts.items():
        rows.append({
            "symbol": symbol.upper(),
            "date": datetime.strptime(d, "%Y-%m-%d").date(),
            "open": float(ohlc.get("1. open", 0) or 0),
            "high": float(ohlc.get("2. high", 0) or 0),
            "low":  float(ohlc.get("3. low", 0) or 0),
            "close": float(ohlc.get("4. close", 0) or 0),
            "volume": int(float(ohlc.get("6. volume", 0) or 0)),
            "dividend_amount": float(ohlc.get("7. dividend amount", 0) or 0),
            "split_coefficient": float(ohlc.get("8. split coefficient", 1) or 1),
        })
    rows.sort(key=lambda x: x["date"])
    return rows


# —— 面向对象封装（可选用）———————————————————————————————

class AlphaVantageClient:
    """
    轻量客户端：封装常用端点。保持无状态，便于在 loader/脚本中复用。
    """
    def __init__(self, api_key: Optional[str] = None):
        # 允许显式传 key；默认从 get_settings() 读取
        self._api_key = api_key or _apikey()

    def _get(self, params: Dict[str, str]) -> Dict:
        data = http_get_json(BASE_URL, {**params, "apikey": self._api_key})
        if "Note" in data:
            raise AlphaVantageError("AlphaVantage 速率限制：请稍后再试或升级账号。")
        if "Error Message" in data:
            raise AlphaVantageError(data["Error Message"])
        return data

    # 日线
    def get_daily_raw(self, symbol: str, *, adjusted: bool = True, outputsize: str = "compact") -> Dict:
        fn = "TIME_SERIES_DAILY_ADJUSTED" if adjusted else "TIME_SERIES_DAILY"
        return self._get({
            "function": fn,
            "symbol": symbol.upper(),
            "outputsize": outputsize,
            "datatype": "json",
        })

    def normalize_daily(self, raw: Dict, symbol: str) -> List[PriceRow]:
        return normalize_daily(raw, symbol)

    # 如需扩展：可继续加 quote/overview 等端点
    # def get_quote_raw(self, symbol: str) -> Dict: ...
    # def normalize_quote(self, raw: Dict) -> Dict: ...
