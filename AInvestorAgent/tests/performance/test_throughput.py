"""吞吐量测试"""
import pytest
import requests
import time

class TestThroughput:
    def test_requests_per_second(self, base_url):
        print("\n测试: 吞吐量")
        start = time.time()
        count = 0
        while time.time() - start < 10:
            try:
                requests.get(f"{base_url}/health", timeout=1)
                count += 1
            except:
                pass
        rps = count / 10
        print(f"   📊 吞吐量: {rps:.2f} req/s")
