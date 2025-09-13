# backend/storage/models.py
from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from sqlalchemy import Column, String, Date, Float, Integer, UniqueConstraint, Index, DateTime
from .db import Base

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Index, func
from sqlalchemy.orm import relationship

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


class NewsRaw(Base):
    __tablename__ = "news_raw"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(String, nullable=False)
    source = Column(String)
    published_at = Column(DateTime(timezone=True), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("uq_news_symbol_url", "symbol", "url", unique=True),)
    scores = relationship("NewsScore", back_populates="news", cascade="all, delete-orphan")

class NewsScore(Base):
    __tablename__ = "news_scores"
    id = Column(Integer, primary_key=True)
    news_id = Column(Integer, ForeignKey("news_raw.id", ondelete="CASCADE"), index=True, nullable=False)
    sentiment = Column(Float, nullable=False)  # -1..1
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    news = relationship("NewsRaw", back_populates="scores")


class ScoreDaily(Base):
    __tablename__ = "scores_daily"
    id = Column(Integer, primary_key=True)
    as_of = Column(Date, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    f_value = Column(Float, nullable=True)      # 0..1
    f_quality = Column(Float, nullable=True)    # 0..1
    f_momentum = Column(Float, nullable=True)   # 0..1
    f_sentiment = Column(Float, nullable=True)  # 0..1
    score = Column(Float, nullable=False)       # 0..100
    version_tag = Column(String, default="v0.1", index=True)
    __table_args__ = (Index("uq_scores_asof_symbol", "as_of", "symbol", unique=True),)