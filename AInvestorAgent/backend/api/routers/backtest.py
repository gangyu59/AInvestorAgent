# backend/api/routers/backtest.py - 完整回测API（调用simulator）
"""
完整的历史回测API - 调用 HistoricalBacktestSimulator

功能:
- 真实调仓逻辑
- 完整税务计算（短期/长期资本利得）
- 交易成本
- 持仓管理
- 用户可调参数
- 前端完全兼容
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import sys
from pathlib import Path

# 确保能导入 scripts 模块
ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.historical_backtest_simulator import HistoricalBacktestSimulator

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


# ==================== 请求模型 ====================
class WeightItem(BaseModel):
    symbol: str
    weight: float


class RunBacktestReq(BaseModel):
    # 组合来源（三选一）
    snapshot_id: Optional[str] = None
    weights: Optional[List[WeightItem]] = None
    holdings: Optional[List[Dict[str, Any]]] = None

    # 回测时间窗口
    window: Optional[str] = None  # "1Y" | "6M" | "252D"
    window_days: Optional[int] = 252

    # 调仓频率
    rebalance: Optional[str] = "weekly"  # weekly | monthly | daily
    max_trades_per_week: Optional[int] = 3  # 暂未使用

    # 基准
    benchmark_symbol: Optional[str] = "SPY"

    # 成本参数
    trading_cost: Optional[float] = 0.001  # 交易成本 0.1%

    # 税务参数（用户可调）
    enable_tax: Optional[bool] = True  # 是否启用税务
    short_term_tax_rate: Optional[float] = 0.37  # 短期税率 37%
    long_term_tax_rate: Optional[float] = 0.20  # 长期税率 20%

    # 高级参数
    initial_capital: Optional[float] = 100000.0
    enable_factor_optimization: Optional[bool] = False
    optimization_objective: Optional[str] = "sharpe"

    # 兼容参数
    mock: Optional[bool] = False


# ==================== 工具函数 ====================
def parse_window_days(win: Optional[str], fallback: int = 252) -> int:
    """解析窗口期: 1Y→252, 6M→126, 90D→90"""
    if not win:
        return fallback
    w = win.strip().upper()
    try:
        if w.endswith("Y"):
            return int(round(float(w[:-1]) * 252))
        if w.endswith("M"):
            return int(round(float(w[:-1]) * 21))
        if w.endswith("W"):
            return int(round(float(w[:-1]) * 5))
        if w.endswith("D"):
            return max(int(float(w[:-1])), 5)
        return max(int(float(w)), 5)
    except Exception:
        return fallback


def parse_rebalance_freq(rebalance: str) -> str:
    """转换调仓频率: weekly→W-MON, monthly→MS"""
    mapping = {
        "weekly": "W-MON",
        "monthly": "MS",
        "daily": "D",
        "biweekly": "2W-MON"
    }
    return mapping.get(rebalance.lower(), "W-MON")


def extract_watchlist(req: RunBacktestReq) -> List[str]:
    """
    从请求中提取股票池
    优先级: weights > holdings > snapshot_id
    """
    merged: Dict[str, float] = {}

    # 处理 weights
    if req.weights:
        for w in req.weights:
            if isinstance(w, dict):
                s = (w.get("symbol") or "").upper().strip()
                v = float(w.get("weight") or 0.0)
            else:
                s = (w.symbol or "").upper().strip()
                v = float(w.weight or 0.0)
            if s:
                merged[s] = merged.get(s, 0.0) + v

    # 处理 holdings
    if req.holdings:
        for h in req.holdings:
            s = str(h.get("symbol", "")).upper().strip()
            v = float(h.get("weight") or 0.0)
            if s:
                merged[s] = merged.get(s, 0.0) + v

    # TODO: 处理 snapshot_id
    # if req.snapshot_id and not merged:
    #     from backend.storage.db import Session, engine
    #     from backend.storage.models import PortfolioSnapshot
    #     # 查询数据库...

    if not merged:
        raise HTTPException(
            status_code=422,
            detail="请提供 weights、holdings 或 snapshot_id"
        )

    # 归一化权重（虽然simulator会重新计算，但这里验证一下）
    total = sum(max(0.0, v) for v in merged.values())
    if total <= 0:
        raise HTTPException(
            status_code=422,
            detail="权重总和必须大于0"
        )

    return list(merged.keys())


# ==================== 主路由 ====================
@router.post("/run")
def run_backtest(req: RunBacktestReq):
    """
    运行完整历史回测

    返回格式兼容前端，包含:
    - dates: 日期序列
    - nav: 净值序列
    - benchmark_nav: 基准净值
    - drawdown: 回撤序列
    - metrics: 性能指标（含税务）
    - trades: 交易明细
    - params: 回测参数
    """
    try:
        # 1. 解析参数
        window_days = parse_window_days(req.window, req.window_days or 252)
        rebalance_freq = parse_rebalance_freq(req.rebalance or "weekly")
        watchlist = extract_watchlist(req)

        # 2. 计算日期范围
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")

        # 3. 打印回测配置
        print(f"\n{'=' * 60}")
        print(f"🚀 开始完整回测")
        print(f"{'=' * 60}")
        print(f"📊 股票池: {', '.join(watchlist)} ({len(watchlist)}只)")
        print(f"📅 期间: {start_date} → {end_date} ({window_days}天)")
        print(f"🔄 调仓: {req.rebalance} ({rebalance_freq})")
        print(f"💰 初始资金: ${req.initial_capital:,.2f}")
        print(f"💵 交易成本: {req.trading_cost * 100:.2f}%")
        print(f"📈 因子优化: {'启用' if req.enable_factor_optimization else '禁用'}")

        if req.enable_tax:
            print(f"💸 税务计算: 启用")
            print(f"   短期税率: {req.short_term_tax_rate * 100:.1f}% (持有≤1年)")
            print(f"   长期税率: {req.long_term_tax_rate * 100:.1f}% (持有>1年)")
        else:
            print(f"💸 税务计算: 禁用")

        # 4. 创建模拟器
        simulator = HistoricalBacktestSimulator(
            watchlist=watchlist,
            initial_capital=req.initial_capital or 100000.0,
            start_date=start_date,
            end_date=end_date,
            short_term_tax_rate=req.short_term_tax_rate if req.enable_tax else 0.0,
            long_term_tax_rate=req.long_term_tax_rate if req.enable_tax else 0.0,
            enable_factor_optimization=req.enable_factor_optimization or False,
            optimization_objective=req.optimization_objective or "sharpe"
        )

        # 5. 运行回测
        simulator.run_backtest(rebalance_frequency=rebalance_freq)

        # 6. 获取性能指标
        metrics = simulator.get_performance_metrics()

        # 7. 格式化历史数据
        history_df = pd.DataFrame(simulator.history)

        # 8. 格式化交易记录（最多返回200笔）
        trades_formatted = []
        for t in simulator.trades[:200]:
            trades_formatted.append({
                "date": t["date"].strftime("%Y-%m-%d") if hasattr(t["date"], "strftime") else str(t["date"]),
                "symbol": t["symbol"],
                "action": t["action"],
                "shares": round(t["shares"], 4),
                "price": round(t["price"], 2),
                "value": round(t["value"], 2),
                "tax": round(t.get("tax", 0), 2),
                "net_value": round(t.get("net_value", t["value"]), 2),
                "capital_gain": round(t.get("capital_gain", 0), 2) if "capital_gain" in t else None
            })

        # 9. 构建响应（完全兼容前端）
        response = {
            "success": True,

            # 时间序列数据
            "dates": [d.strftime("%Y-%m-%d") for d in history_df["date"]],
            "nav": [round(float(x), 6) for x in history_df["nav"].tolist()],
            "benchmark_nav": [],  # TODO: 添加基准对比
            "drawdown": [round(float(x), 2) for x in history_df["drawdown"].tolist()],

            # 性能指标（包含税务）
            "metrics": {
                # 收益指标
                "total_return_before_tax": round(metrics["total_return_before_tax"], 2),
                "total_return_after_tax": round(metrics["total_return_after_tax"], 2),
                "annualized_return_before_tax": round(metrics["annualized_return_before_tax"], 2),
                "annualized_return_after_tax": round(metrics["annualized_return_after_tax"], 2),

                # 风险指标
                "sharpe": round(metrics["sharpe_ratio"], 3),
                "sharpe_ratio": round(metrics["sharpe_ratio"], 3),  # 兼容两种命名
                "max_drawdown": round(metrics["max_drawdown"], 2),

                # 交易指标
                "total_trades": metrics["total_trades"],
                "win_rate": round(metrics["win_rate"], 2),

                # 税务指标
                "tax_impact_pct": round(metrics["tax_impact_pct"], 2),
                "total_tax_paid": round(metrics["total_tax_paid"], 2),
                "total_capital_gains": round(metrics["total_capital_gains"], 2),
                "total_capital_losses": round(metrics["total_capital_losses"], 2),

                # 最终价值
                "final_value_before_tax": round(metrics["final_value_before_tax"], 2),
                "final_value_after_tax": round(metrics["final_value_after_tax"], 2),
            },

            # 交易记录
            "trades": trades_formatted,

            # 回测参数（记录用户设置）
            "params": {
                "window": req.window or f"{window_days}D",
                "window_days": window_days,
                "cost": req.trading_cost,
                "trading_cost": req.trading_cost,  # 兼容
                "rebalance": req.rebalance or "weekly",
                "max_trades_per_week": req.max_trades_per_week or 3,
                "benchmark": req.benchmark_symbol or "SPY",
                "enable_tax": req.enable_tax,
                "short_term_tax_rate": req.short_term_tax_rate if req.enable_tax else 0,
                "long_term_tax_rate": req.long_term_tax_rate if req.enable_tax else 0,
                "initial_capital": req.initial_capital,
                "start_date": start_date,
                "end_date": end_date,
            },

            # 版本标识
            "version_tag": "full_backtest_with_tax_v1.0",
            "backtest_id": f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",

            # 调试信息
            "debug": {
                "watchlist": watchlist,
                "total_days": len(history_df),
                "total_trades": len(simulator.trades),
                "final_positions": len(simulator.holdings),
                "rebalance_frequency": rebalance_freq,
            }
        }

        # 10. 打印结果摘要
        print(f"\n{'=' * 60}")
        print(f"✅ 回测完成")
        print(f"{'=' * 60}")
        print(f"📊 总交易: {metrics['total_trades']}笔")
        print(f"💰 税前收益率: {metrics['total_return_before_tax']:.2f}%")
        print(f"💰 税后收益率: {metrics['total_return_after_tax']:.2f}%")
        print(f"💸 税务影响: {metrics['tax_impact_pct']:.2f}%")
        print(f"📉 最大回撤: {metrics['max_drawdown']:.2f}%")
        print(f"📈 夏普比率: {metrics['sharpe_ratio']:.3f}")
        print(f"🎯 胜率: {metrics['win_rate']:.1f}%")

        return response

    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"无法导入回测模块: {str(e)}\n请检查 scripts/historical_backtest_simulator.py 是否存在"
        )
    except Exception as e:
        import traceback
        error_msg = f"回测失败: {str(e)}\n{traceback.format_exc()}"
        print(f"\n❌ {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


# ==================== 健康检查 ====================
@router.get("/health")
def backtest_health():
    """检查回测模块是否正常"""
    try:
        # 尝试导入
        from scripts.historical_backtest_simulator import HistoricalBacktestSimulator
        return {
            "status": "ok",
            "simulator": "available",
            "version": "1.0"
        }
    except ImportError as e:
        return {
            "status": "error",
            "simulator": "unavailable",
            "error": str(e)
        }