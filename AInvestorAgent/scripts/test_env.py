# scripts/test_env.py
#!/usr/bin/env python3
import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv 加载成功")
except Exception as e:
    print(f"❌ dotenv 加载失败: {e}")

# 检查关键环境变量
env_vars = ['DEEPSEEK_API_KEY', 'DOUBAO_API_KEY', 'NEWS_API_KEY', 'ALPHAVANTAGE_KEY']

for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {value[:10]}...")  # 只显示前10个字符
    else:
        print(f"❌ {var}: 未设置")