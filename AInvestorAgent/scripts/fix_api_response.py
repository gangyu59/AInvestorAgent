#!/usr/bin/env python3
"""修复并测试API响应"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
import json

db_url = "sqlite:///./db/stock.sqlite"
engine = create_engine(db_url)

print("🔍 检查最新快照的数据...")

with engine.connect() as conn:
    # 读取最新快照
    result = conn.execute(text("""
        SELECT snapshot_id, as_of, version_tag, payload, holdings_json
        FROM portfolio_snapshots
        ORDER BY created_at DESC
        LIMIT 1
    """))

    row = result.fetchone()

    if row:
        print(f"\n✅ 找到最新快照: {row[0]}")
        print(f"日期: {row[1]}")
        print(f"版本: {row[2]}")

        # 检查payload字段
        if row[3]:
            print("\n📦 payload字段 (有数据):")
            payload = json.loads(row[3])
            holdings = payload.get('holdings', [])
            print(f"  持仓数: {len(holdings)}")
            for h in holdings[:3]:
                print(f"  - {h['symbol']}: {h['weight']:.2%}")
        else:
            print("\n⚠️ payload字段为空")

        # 检查holdings_json字段
        if row[4]:
            print("\n📦 holdings_json字段 (有数据):")
            holdings = json.loads(row[4])
            print(f"  持仓数: {len(holdings)}")
        else:
            print("\n⚠️ holdings_json字段为空 (这就是问题所在！)")

        # 如果holdings_json是空的，复制payload到holdings_json
        if not row[4] and row[3]:
            print("\n🔧 修复: 将payload复制到holdings_json...")
            payload_data = json.loads(row[3])
            holdings = payload_data.get('holdings', [])

            conn.execute(text("""
                UPDATE portfolio_snapshots
                SET holdings_json = :holdings
                WHERE snapshot_id = :sid
            """), {
                'holdings': json.dumps(holdings),
                'sid': row[0]
            })
            conn.commit()
            print("✅ 修复完成！")
    else:
        print("❌ 没有找到快照")

print("\n" + "=" * 60)
print("现在测试API...")
print("=" * 60)

import requests

try:
    resp = requests.get("http://localhost:8000/api/portfolio/snapshots/latest", timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        holdings = data.get('holdings', [])

        print(f"\n✅ API返回成功")
        print(f"持仓数: {len(holdings)}")

        if holdings:
            print("\n前5只持仓:")
            for h in holdings[:5]:
                print(f"  {h['symbol']}: {h['weight']:.2%} (评分: {h['score']:.2f})")
        else:
            print("\n⚠️ holdings仍然是空的")
            print("完整响应:", json.dumps(data, indent=2))
    else:
        print(f"❌ API返回错误: {resp.status_code}")
except Exception as e:
    print(f"❌ 无法连接API: {e}")