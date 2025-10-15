# scripts/update_snapshot_metrics.py
"""
一次性脚本：为所有现有快照添加 metrics 数据
运行方式：python scripts/update_snapshot_metrics.py
"""

import sys
import json
import random
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.storage.db import SessionLocal
from backend.storage.models import PortfolioSnapshot


def update_all_snapshots():
    """为所有快照添加模拟的 metrics 数据"""
    db = SessionLocal()

    try:
        snapshots = db.query(PortfolioSnapshot).all()

        if not snapshots:
            print("❌ 数据库中没有快照")
            return

        print(f"📊 找到 {len(snapshots)} 个快照，开始更新...")

        updated_count = 0
        skipped_count = 0

        for snap in snapshots:
            try:
                # 解析现有 payload
                payload = json.loads(snap.payload) if snap.payload else {}

                # 检查是否已有非零 metrics
                existing_metrics = payload.get('metrics', {})
                if existing_metrics and (
                        existing_metrics.get('ann_return', 0) != 0 or
                        existing_metrics.get('mdd', 0) != 0
                ):
                    print(f"⏭️  跳过 {snap.snapshot_id} (已有metrics)")
                    skipped_count += 1
                    continue

                # 生成模拟 metrics
                payload['metrics'] = {
                    'ann_return': random.uniform(0.05, 0.20),
                    'mdd': random.uniform(-0.15, -0.05),
                    'sharpe': random.uniform(0.8, 1.5),
                    'winrate': random.uniform(0.55, 0.75)
                }

                # 更新回数据库
                snap.payload = json.dumps(payload, ensure_ascii=False)
                updated_count += 1

                print(f"✅ 更新 {snap.snapshot_id}: "
                      f"收益={payload['metrics']['ann_return'] * 100:.2f}%, "
                      f"回撤={payload['metrics']['mdd'] * 100:.2f}%")

            except Exception as e:
                print(f"❌ 处理快照 {snap.snapshot_id} 失败: {e}")
                continue

        # 提交所有更改
        db.commit()

        print(f"\n🎉 完成！")
        print(f"   ✅ 更新: {updated_count} 个")
        print(f"   ⏭️  跳过: {skipped_count} 个")

    except Exception as e:
        print(f"❌ 更新失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 开始更新快照 metrics...")
    update_all_snapshots()
    print("✨ 脚本执行完毕")