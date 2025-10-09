# list_routes.py - 放在项目根目录
"""
调试脚本：列出所有已注册的路由
用法: python list_routes.py
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.app import app

print("=" * 60)
print("已注册的路由列表:")
print("=" * 60)

routes = []
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        methods = ','.join(route.methods) if route.methods else 'N/A'
        routes.append((route.path, methods, route.name))

# 按路径排序
routes.sort(key=lambda x: x[0])

for path, methods, name in routes:
    print(f"{methods:8s} {path:40s} ({name})")

print("=" * 60)
print(f"总计: {len(routes)} 个路由")
print("=" * 60)

# 检查关键路由
key_routes = ['/api/symbols', '/api/health', '/api/prices/daily']
print("\n关键路由检查:")
for key_route in key_routes:
    exists = any(r[0] == key_route for r in routes)
    status = "✅" if exists else "❌"
    print(f"{status} {key_route}")