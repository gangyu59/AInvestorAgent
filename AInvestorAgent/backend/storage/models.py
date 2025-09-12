# backend/storage/models.py
from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from sqlalchemy import Column, String, Date, Float, Integer, UniqueConstraint, Index, DateTime
from .db import Base


class Symbol(Base):
    __tablename__ = "symbols"
    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)

class PriceDaily(Base):
    __tablename__ = "prices_daily"
    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[Date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    close: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer)


class RunHistory(Base):
    """
    运行历史，用于实现“每周≤3次”的限频控制或任务审计。
    复合主键(job, ts)；按需也可只用自增主键。
    """
    __tablename__ = "run_history"
    job = Column(String(64), primary_key=True)
    ts = Column(DateTime, primary_key=True, default=datetime.utcnow)
