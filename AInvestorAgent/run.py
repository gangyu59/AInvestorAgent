#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AInvestorAgent 统一入口

用法：
  1) 启动服务（默认 8000 端口）：
     py -3.13 run.py
     或
     py -3.13 run.py serve --host 0.0.0.0 --port 8000 --reload

  2) 冒烟测试（需服务已在运行）：
     py -3.13 run.py test --host 127.0.0.1 --port 8000 --symbol AAPL --limit 5 --fetch

  3) 查看数据库信息：
     py -3.13 run.py info
"""

import argparse
import sys
from pathlib import Path

# —— 让 import backend.* 在任何地方都能工作 —— #
ROOT = Path(__file__).resolve().parent           # …/AInvestorAgent
PARENT = ROOT.parent                              # …/（上一级）
for p in (str(ROOT), str(PARENT)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from dotenv import load_dotenv  # 可选
    load_dotenv()
except Exception:
    pass

import uvicorn
import requests


def serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """启动 FastAPI 服务"""
    uvicorn.run("backend.app:app", host=host, port=port, reload=reload, factory=False)


def smoke_test(host: str, port: int, symbol: str, limit: int, do_fetch: bool):
    """对已运行的服务做冒烟测试"""
    base = f"http://{host}:{port}"

    def _get(p: str, **kwargs):
        r = requests.get(base + p, timeout=30, **kwargs)
        if r.status_code >= 400:
            print(f"      ERROR {r.status_code} GET {p}")
            # 尝试输出 json 的 detail，否则原文
            try:
                print("      BODY:", r.json())
            except Exception:
                print("      BODY:", r.text)
            # 仍然抛出让测试中断
            r.raise_for_status()
        return r.json()

    def _post(p: str, **kwargs):
        r = requests.post(base + p, timeout=90, **kwargs)
        if r.status_code >= 400:
            print(f"      ERROR {r.status_code} POST {p}")
            try:
                print("      BODY:", r.json())
            except Exception:
                print("      BODY:", r.text)
            r.raise_for_status()
        return r.json()

    # —— 健康检查：自动尝试多条路径 —— #
    print("[1/3] 健康检查 ...", flush=True)
    health_paths = ["/api/health", "/health", "/"]
    last_err = None
    for p in health_paths:
        try:
            h = _get(p)
            print(f"      OK: GET {p} -> {h}")
            break
        except Exception as e:
            last_err = e
    else:
        raise last_err  # 三条都失败才抛

    # —— 可选：先触发一次入库 —— #
    if do_fetch:
        print(f"[2/3] 拉取并入库 POST /api/prices/fetch?symbol={symbol} ...", flush=True)
        f = _post(f"/api/prices/fetch?symbol={symbol}&adjusted=true&outputsize=compact")
        print("      返回：", f)
    else:
        print("[2/3] 跳过拉取（未传 --fetch）")

    # —— 读取日线 —— #
    print(f"[3/3] 读取日线 GET /api/prices/daily?symbol={symbol}&limit={limit} ...", flush=True)
    d = _get(f"/api/prices/daily?symbol={symbol}&limit={limit}")
    items = d.get("items") or []
    print(f"      共 {len(items)} 条，示例：")
    if items:
        print("      最后一条：", items[-1])
    else:
        print("      暂无数据（可能需要先 --fetch）")

    print("\n✅ 冒烟测试完成。")


def show_info():
    """打印当前数据库 URL 与 SQLite 文件存在性"""
    from backend.storage.db import engine
    url = str(engine.url)
    print("Database URL:", url)
    if url.startswith("sqlite:///"):
        p = Path(url.replace("sqlite:///", "", 1))
        print("SQLite 文件存在：", p.exists())
        print("SQLite 文件路径：", p)
    else:
        print("非 SQLite 数据库。")


def main(argv=None):
    parser = argparse.ArgumentParser(description="AInvestorAgent Runner")
    sub = parser.add_subparsers(dest="cmd")

    # serve
    p_serve = sub.add_parser("serve", help="启动 API 服务（默认命令）")
    p_serve.add_argument("--host", type=str, default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")

    # test
    p_test = sub.add_parser("test", help="对已运行服务做冒烟测试")
    p_test.add_argument("--host", type=str, default="127.0.0.1")
    p_test.add_argument("--port", type=int, default=8000)
    p_test.add_argument("--symbol", type=str, default="AAPL")
    p_test.add_argument("--limit", type=int, default=5)
    p_test.add_argument("--fetch", action="store_true")

    # info
    sub.add_parser("info", help="打印数据库配置等信息")

    args = parser.parse_args(argv)

    if args.cmd is None:
        return serve()

    if args.cmd == "serve":
        return serve(host=args.host, port=args.port, reload=args.reload)

    if args.cmd == "test":
        return smoke_test(host=args.host, port=args.port, symbol=args.symbol, limit=args.limit, do_fetch=args.fetch)

    if args.cmd == "info":
        return show_info()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
