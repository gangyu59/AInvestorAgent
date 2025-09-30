"""Locust压测脚本 - 用于高负载测试"""
from locust import HttpUser, task, between, events
import random


class StockUser(HttpUser):
    """模拟股票查询用户"""
    wait_time = between(1, 3)

    def on_start(self):
        """用户启动时执行"""
        self.symbols = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "META", "AMZN"]

    @task(10)
    def health_check(self):
        """健康检查（高频）"""
        self.client.get("/health")

    @task(5)
    def get_prices(self):
        """获取价格"""
        symbol = random.choice(self.symbols)
        self.client.get(f"/api/prices/daily?symbol={symbol}&limit=30")

    @task(3)
    def analyze_stock(self):
        """分析股票"""
        symbol = random.choice(self.symbols)
        self.client.get(f"/api/analyze/{symbol}")

    @task(2)
    def batch_scores(self):
        """批量评分"""
        symbols = random.sample(self.symbols, 3)
        self.client.post("/api/scores/batch", json={"symbols": symbols})

    @task(1)
    def propose_portfolio(self):
        """组合建议"""
        candidates = [
            {"symbol": sym, "sector": "Technology", "score": random.uniform(60, 90)}
            for sym in random.sample(self.symbols, 3)
        ]
        self.client.post(
            "/api/orchestrator/propose",
            json={"candidates": candidates, "params": {"mock": True}}
        )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时"""
    print("🚀 开始压力测试...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时"""
    print("✅ 压力测试完成")
    stats = environment.stats
    print(f"\n总请求: {stats.total.num_requests}")
    print(f"失败: {stats.total.num_failures}")
    print(f"平均响应时间: {stats.total.avg_response_time:.2f}ms")