# backend/api/routers/watchlist.py
"""Watchlist管理 - 配合前端endpoints.ts"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from backend.storage.db import get_db
from backend.storage.models import Watchlist

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistUpdateRequest(BaseModel):
    symbols: List[str]


@router.get("")
async def get_watchlist(db: Session = Depends(get_db)):
    """
    获取watchlist (返回symbols数组,配合前端getWatchlist)
    前端期望: string[] 或 {items: string[]} 或 {data: string[]}
    """
    items = db.query(Watchlist.symbol).order_by(Watchlist.added_at.desc()).all()
    symbols = [item.symbol for item in items]
    return symbols  # 直接返回数组,前端会自动处理


@router.put("")
async def update_watchlist(
        request: WatchlistUpdateRequest,
        db: Session = Depends(get_db)
):
    """
    更新整个watchlist (替换式更新,配合前端saveWatchlist)
    """
    # 清空现有
    db.query(Watchlist).delete()

    # 添加新的
    for symbol in request.symbols:
        if symbol.strip():
            item = Watchlist(symbol=symbol.upper().strip())
            db.add(item)

    db.commit()

    return {"ok": True, "count": len(request.symbols)}


@router.post("/add/{symbol}")
async def add_symbol(symbol: str, db: Session = Depends(get_db)):
    """单个添加 (供管理页面使用)"""
    symbol = symbol.upper().strip()

    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if existing:
        return {"ok": False, "message": f"{symbol} 已存在"}

    item = Watchlist(symbol=symbol)
    db.add(item)
    db.commit()

    return {"ok": True, "symbol": symbol}


@router.delete("/remove/{symbol}")
async def remove_symbol(symbol: str, db: Session = Depends(get_db)):
    """单个删除 (供管理页面使用)"""
    symbol = symbol.upper().strip()

    item = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if not item:
        raise HTTPException(404, f"{symbol} 不在列表中")

    db.delete(item)
    db.commit()

    return {"ok": True, "symbol": symbol}