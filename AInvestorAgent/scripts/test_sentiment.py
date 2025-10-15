# scripts/test_sentiment_api.py
"""测试情绪API端点是否正常工作"""

import requests
import json

API_BASE = "http://127.0.0.1:8000"


def test_sentiment_brief():
    print("=== 测试 /api/sentiment/brief 端点 ===\n")

    # 使用数据库中有数据的股票
    symbols = "AAPL,AMZN,APP,ARM,AVGO"
    days = 14

    url = f"{API_BASE}/api/sentiment/brief?symbols={symbols}&days={days}"
    print(f"请求URL: {url}")

    try:
        response = requests.get(url, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.ok:
            data = response.json()
            print("\n✅ API响应成功！")
            print(f"\n情绪时间序列数据点: {len(data.get('series', []))}")
            print(f"最新新闻数量: {len(data.get('latest_news', []))}")

            # 显示前5条新闻
            if data.get('latest_news'):
                print("\n前5条新闻:")
                for i, news in enumerate(data['latest_news'][:5], 1):
                    print(f"  {i}. [{news.get('score', 0):.2f}] {news.get('title', '')[:60]}...")

            # 显示情绪趋势
            if data.get('series'):
                print("\n情绪趋势 (最近7天):")
                for point in data['series'][-7:]:
                    date = point.get('date', '')
                    score = point.get('score', 0)
                    bar = '█' * int((score + 1) * 10)  # -1到1映射到0-20个字符
                    print(f"  {date}: {score:+.2f} {bar}")

            # 保存完整响应到文件
            with open("reports/sentiment_test.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("\n📄 完整响应已保存到: reports/sentiment_test.json")

        else:
            print(f"\n❌ API返回错误: {response.status_code}")
            print(f"错误信息: {response.text}")

    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到后端服务")
        print("请确保后端正在运行: python run.py")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == "__main__":
    test_sentiment_brief()
