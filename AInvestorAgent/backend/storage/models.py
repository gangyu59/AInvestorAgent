# backend/storage/models.py
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, UTC
from sqlalchemy import Column, String, Date, Float, Integer, UniqueConstraint, Index, DateTime
from .db import Base

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Index, func
from sqlalchemy.orm import relationship
import datetime as dt


try:
    JSONType = sa.JSON
except AttributeError:
    from sqlalchemy.types import JSON as JSONType

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


class TraceRecord(Base):
    __tablename__ = "traces"
    trace_id   = sa.Column(sa.String, primary_key=True)
    scene      = sa.Column(sa.String, nullable=False)
    req_json   = sa.Column(JSONType, nullable=True)
    context    = sa.Column(JSONType, nullable=True)
    trace      = sa.Column(JSONType, nullable=True)
    created_at = sa.Column(sa.DateTime, default=lambda: datetime.now(UTC), nullable=False)


class RunHistory(Base):
    """
    运行历史，用于实现“每周≤3次”的限频控制或任务审计。
    复合主键(job, ts)；按需也可只用自增主键。
    """
    __tablename__ = "run_history"
    job = Column(String(64), primary_key=True)
    ts = Column(DateTime, primary_key=True, default=dt.datetime.utcnow)


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


class Watchlist(Base):
    """用户关注列表"""
    __tablename__ = "watchlist"

    symbol = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    

# 在 backend/storage/models.py 中添加以下表定义

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# 模拟账户表
class SimAccount(Base):
    __tablename__ = "sim_accounts"

    account_id = Column(String, primary_key=True)
    account_name = Column(String, nullable=False)
    initial_cash = Column(Float, default=100000.0)  # 初始资金
    current_cash = Column(Float, default=100000.0)  # 当前现金
    total_value = Column(Float, default=100000.0)  # 总资产价值
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 模拟持仓表
class SimPosition(Base):
    __tablename__ = "sim_positions"

    position_id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("sim_accounts.account_id"))
    symbol = Column(String, nullable=False)
    quantity = Column(Float, default=0)  # 持有数量
    avg_cost = Column(Float, default=0)  # 平均成本
    market_value = Column(Float, default=0)  # 市值
    unrealized_pnl = Column(Float, default=0)  # 浮动盈亏
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 模拟交易表
class SimTrade(Base):
    __tablename__ = "sim_trades"

    trade_id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("sim_accounts.account_id"))
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False)  # BUY/SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)  # 总金额
    commission = Column(Float, default=0)  # 手续费
    trade_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="FILLED")  # PENDING/FILLED/CANCELLED
    source = Column(String, default="MANUAL")  # MANUAL/AUTO/DECISION
    decision_id = Column(String, nullable=True)  # 关联的决策ID

# 每日P&L记录表
class SimDailyPnL(Base):
    __tablename__ = "sim_daily_pnl"

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("sim_accounts.account_id"))
    trade_date = Column(String, nullable=False)  # YYYY-MM-DD
    total_value = Column(Float, nullable=False)
    cash_value = Column(Float, nullable=False)
    position_value = Column(Float, nullable=False)
    daily_pnl = Column(Float, default=0)  # 当日盈亏
    cumulative_pnl = Column(Float, default=0)  # 累计盈亏
    return_pct = Column(Float, default=0)  # 当日收益率
    created_at = Column(DateTime, default=datetime.utcnow)