# backend/api/schemas/portfolio.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Candidate(BaseModel):
    """单个候选股票"""
    symbol: str = Field(..., description="股票代码")
    score: float = Field(..., description="打分 0-100")
    sector: Optional[str] = Field(None, description="所属行业")

class ProposeParams(BaseModel):
    """组合建议参数"""
    risk_max_stock: Optional[float] = Field(None, alias="risk.max_stock", description="单票权重上限")
    risk_max_sector: Optional[float] = Field(None, alias="risk.max_sector", description="行业权重上限")
    risk_count_range: Optional[List[int]] = Field(None, alias="risk.count_range", description="持仓数范围 [min,max]")

    class Config:
        populate_by_name = True  # 允许通过 "risk.max_stock" 这种 key 填充

class ProposeRequest(BaseModel):
    """组合提案请求"""
    candidates: List[Candidate]
    params: Optional[Dict[str, Any]] = None

class Weight(BaseModel):
    symbol: str
    weight: float
    sector: Optional[str] = None

class ProposeResponse(BaseModel):
    """组合提案响应"""
    kept: List[Weight]
    concentration: Dict[str, Any]
    actions: List[Dict[str, Any]] = []
