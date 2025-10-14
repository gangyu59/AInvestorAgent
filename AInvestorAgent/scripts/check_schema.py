#!/usr/bin/env python3
"""检查表结构"""
import sqlite3

db_path = "db/stock.sqlite"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['scores_daily', 'portfolio_snapshots', 'news_scores']

for table in tables:
    print(f"\n{'=' * 60}")
    print(f"📋 表: {table}")
    print('=' * 60)

    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()

    if columns:
        print("列名:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        # 显示前3行数据
        try:
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            rows = cursor.fetchall()
            if rows:
                print(f"\n前3行数据:")
                for i, row in enumerate(rows, 1):
                    print(f"  {i}. {row}")
            else:
                print(f"\n⚠️ 表是空的")
        except Exception as e:
            print(f"\n⚠️ 无法读取数据: {e}")
    else:
        print("⚠️ 表不存在")

conn.close()