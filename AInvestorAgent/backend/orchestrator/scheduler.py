# backend/orchestrator/scheduler.py
from datetime import datetime, time
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.api.routers.decide import decide_now, DecideRequest
import logging

logger = logging.getLogger(__name__)


class InvestmentScheduler:
    """投资决策调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def daily_decision_task(self):
        """每日决策任务"""
        try:
            logger.info("🎯 开始执行每日智能决策...")

            # 默认股票池（你可以从配置文件读取）
            default_symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA", "META", "GOOG"]

            # 构造决策请求
            request = DecideRequest(
                symbols=default_symbols,
                topk=8,
                min_score=60,
                refresh_prices=True,
                use_llm=True
            )

            # 执行决策
            result = await decide_now(request)

            logger.info(f"✅ 每日决策完成: {len(result.holdings)} 只股票")
            if result.reasoning:
                logger.info(f"📊 AI理由: {result.reasoning}")

            # 这里可以添加通知逻辑
            await self._notify_decision(result)

        except Exception as e:
            logger.error(f"❌ 每日决策失败: {e}")

    async def _notify_decision(self, result):
        """通知决策结果（预留接口）"""
        # 这里可以实现邮件、微信等通知
        pass

    def start_scheduler(self):
        """启动调度器"""
        if self.is_running:
            return

        # 每个交易日早上 9:30 执行决策（美股开盘前）
        self.scheduler.add_job(
            self.daily_decision_task,
            'cron',
            hour=9,
            minute=30,
            day_of_week='mon-fri',
            id='daily_decision',
            timezone='America/New_York'  # 美东时间
        )

        # 可选：每4小时检查一次市场变化
        self.scheduler.add_job(
            self.daily_decision_task,
            'interval',
            hours=4,
            id='periodic_check',
            max_instances=1  # 防止重复执行
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("📅 投资决策调度器已启动")

    def stop_scheduler(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.is_running = False
        logger.info("📅 投资决策调度器已停止")


# 全局调度器实例
investment_scheduler = InvestmentScheduler()