"""Locust压测脚本"""
from locust import HttpUser, task, between

class StockUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task(3)
    def get_prices(self):
        self.client.get("/api/prices/AAPL?range=1M")
