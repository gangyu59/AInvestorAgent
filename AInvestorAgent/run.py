#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AInvestorAgent 统一入口（最终版）

用法：
  python run.py                # 一键启动，自动打开监控页
  python run.py serve --reload # 开发模式热重载
  python run.py test --fetch   # 对已运行服务做冒烟测试
  python run.py info           # 查看数据库信息
"""
import argparse
import sys
import subprocess
import time
import threading
import webbrowser
from pathlib import Path

# 让 import backend.* 在任何地方都能工作
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 可选 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

REQUIRED_PKGS = ["uvicorn", "fastapi", "sqlalchemy", "pydantic", "requests"]

def _ensure_packages(pkgs):
    missing = []
    for name in pkgs:
        try:
            __import__(name)
        except Exception:
            missing.append(name)
    if missing:
        print(f"📦 缺少依赖：{missing}，正在自动安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        except Exception:
            print("❌ 依赖安装失败，请手动执行：",
                  f"{sys.executable} -m pip install " + " ".join(missing))
            raise

def _banner(title):
    print("\n" + "="*70)
    print(title)
    print("="*70)

def _spawn_uvicorn(host: str, port: int, reload: bool):
    cmd = [sys.executable, "-m", "uvicorn", "backend.app:app",
           "--host", host, "--port", str(port)]
    if reload:
        cmd.append("--reload")
    return subprocess.Popen(cmd, cwd=str(ROOT))

# ---------------------- 监控页落盘目录（固定：backend/reports） ----------------------
def _reports_dir() -> Path:
    d = ROOT / "backend" / "reports"
    d.mkdir(parents=True, exist_ok=True)  # 必要时自动创建
    return d

SMOKE_HTML = r"""<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AInvestorAgent · 运行监控 & 行情可视化</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
  body{font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;margin:16px}
  .card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
  .row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
  label{font-size:14px;color:#374151}
  select,input,button{height:36px;padding:0 10px;border:1px solid #d1d5db;border-radius:8px;background:#fff}
  button{cursor:pointer}
  #log{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;white-space:pre-wrap;background:#f9fafb;padding:10px;border-radius:8px;max-height:200px;overflow:auto}
  #chart{width:100%;height:520px}
  .ok{color:#059669}.bad{color:#dc2626}
</style>
</head><body>
<h2>🛠️ 服务监控</h2>
<div class="card">
  <div class="row">
    <div>健康状态：<span id="health" class="bad">未知</span></div>
    <div>端点：<code id="endpoint">/api/health</code></div>
    <button id="ping">立即Ping</button>
  </div>
</div>

<h2>📈 行情可视化</h2>
<div class="card">
  <div class="row">
    <label>Symbol</label>
    <select id="symbol">
      <option value="AAPL">AAPL</option><option value="MSFT">MSFT</option>
      <option value="TSLA">TSLA</option><option value="NVDA">NVDA</option>
    </select>
    <label>Adjusted</label>
    <select id="adjusted"><option value="true" selected>true</option><option value="false">false</option></select>
    <label>Outputsize</label>
    <select id="outputsize"><option value="compact" selected>compact</option><option value="full">full</option></select>
    <label>Limit</label><input id="limit" type="number" value="120" min="10" max="1000"/>
    <button id="run">🚀 拉取并画图</button>
    <button id="onlyQuery">🔎 仅查询并画图</button>
  </div>
</div>

<div class="card"><div id="chart"></div></div>
<div class="card"><strong>Logs</strong><div id="log"></div></div>

<script>
const apiBase = location.origin;
const healthEl = document.getElementById('health');
const endpointEl = document.getElementById('endpoint');
const logEl = document.getElementById('log');
const chart = echarts.init(document.getElementById('chart'));

function log(m){const ts=new Date().toLocaleTimeString();logEl.textContent+=`[${ts}] ${m}\n`;logEl.scrollTop=logEl.scrollHeight;}

async function ping(){
  const paths=["/api/health","/health","/"];
  for (const p of paths){
    try{ const r=await fetch(apiBase+p,{cache:"no-store"});
      if(r.ok){healthEl.textContent="OK";healthEl.className="ok";endpointEl.textContent=p;return}
    }catch(e){}
  }
  healthEl.textContent="DOWN";healthEl.className="bad";
}

async function fetchAndStore(symbol, adjusted, outputsize){
  const url=`${apiBase}/api/prices/fetch?symbol=${encodeURIComponent(symbol)}&adjusted=${adjusted}&outputsize=${outputsize}`;
  const r=await fetch(url,{method:"POST"}); if(!r.ok){throw new Error("fetch失败 "+r.status)}; return r.json();
}
async function queryDaily(symbol, limit){
  const url=`${apiBase}/api/prices/daily?symbol=${encodeURIComponent(symbol)}&limit=${limit}`;
  const r=await fetch(url); if(!r.ok){throw new Error("daily失败 "+r.status)}; return r.json();
}

function render(data){
  const dates=data.items.map(d=>d.date), closes=data.items.map(d=>d.close??0), vols=data.items.map(d=>d.volume??0);
  const opt={ title:{text:`${data.symbol} · Close`}, tooltip:{trigger:"axis"},
    grid:[{left:50,right:25,top:50,height:280},{left:50,right:25,top:360,height:100}],
    xAxis:[{type:"category",boundaryGap:false,data:dates},{type:"category",boundaryGap:true,data:dates,gridIndex:1}],
    yAxis:[{type:"value",scale:true,name:"Price"},{type:"value",scale:true,name:"Volume",gridIndex:1}],
    dataZoom:[{type:"inside",xAxisIndex:[0,1]},{type:"slider",xAxisIndex:[0,1]}],
    series:[{name:"Close",type:"line",smooth:true,showSymbol:false,data:closes},{name:"Volume",type:"bar",data:vols,xAxisIndex:1,yAxisIndex:1}]};
  chart.setOption(opt);
}
document.getElementById('ping').onclick=()=>ping();
document.getElementById('run').onclick=async()=>{
  const s=document.getElementById('symbol').value,a=document.getElementById('adjusted').value,o=document.getElementById('outputsize').value,l=document.getElementById('limit').value;
  try{log(`拉取 ${s} ...`);const f=await fetchAndStore(s,a,o);log("入库："+JSON.stringify(f));const d=await queryDaily(s,l);log(`查询：${d.items.length} 条`);render(d);}catch(e){log("❌ "+e.message);alert(e.message);}
};
document.getElementById('onlyQuery').onclick=async()=>{
  const s=document.getElementById('symbol').value,l=document.getElementById('limit').value;
  try{const d=await queryDaily(s,l);log(`查询：${d.items.length} 条`);render(d);}catch(e){log("❌ "+e.message);alert(e.message);}
};
ping(); setInterval(ping, 5000);
</script>
</body></html>
"""

def _ensure_monitor_page() -> Path | None:
    """将监控页写入 backend/reports/price_smoketest.html"""
    reports = _reports_dir()
    try:
        path = reports / "price_smoketest.html"
        path.write_text(SMOKE_HTML, encoding="utf-8")
        return path
    except Exception:
        return None

def _wait_for_http(base: str, paths=("/api/health", "/health", "/"), timeout=60):
    import requests
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        for p in paths:
            try:
                r = requests.get(base + p, timeout=3)
                if r.ok:
                    ctype = r.headers.get("content-type", "")
                    body = r.json() if "application/json" in ctype else r.text
                    return True, p, body
            except Exception as e:
                last_err = e
        time.sleep(1.0)
    return False, None, last_err

def _serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = False, auto_open: bool = True):
    _banner("启动 AInvestorAgent API 服务")
    _ensure_packages(REQUIRED_PKGS)

    monitor = _ensure_monitor_page()
    if monitor:
        print(f"🖼️ 监控页已就绪：{monitor}")

    print("🚀 正在启动 uvicorn 服务 ...")
    proc = _spawn_uvicorn(host, port, reload)

    client_host = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    base = f"http://{client_host}:{port}"

    ok, ep, info = _wait_for_http(base)
    if ok:
        print(f"✅ 服务已就绪：GET {ep} -> {info}")
        if auto_open:
            url = f"{base}/reports/price_smoketest.html" if monitor else f"{base}/docs"
            def _open():
                time.sleep(1.0)
                try: webbrowser.open(url)
                except Exception: pass
            threading.Thread(target=_open, daemon=True).start()
            print(f"🌐 已尝试在浏览器打开：{url}")
    else:
        print("⚠️ 无法在预期时间内通过健康检查，服务可能仍在拉起中。")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，正在关闭服务...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

def _smoke_test(host: str, port: int, symbol: str, limit: int, do_fetch: bool):
    import requests
    base = f"http://{host}:{port}"

    def _get(p: str):
        r = requests.get(base + p, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {p} -> {r.status_code}: {r.text}")
        return r.json()

    def _post(p: str):
        r = requests.post(base + p, timeout=90)
        if r.status_code >= 400:
            raise RuntimeError(f"POST {p} -> {r.status_code}: {r.text}")
        return r.json()

    print("[1/3] 健康检查 ...")
    for p in ("/api/health", "/health", "/"):
        try:
            h = _get(p)
            print(f"      OK: GET {p} -> {h}")
            break
        except Exception:
            pass
    else:
        raise RuntimeError("健康检查失败（/api/health, /health, / 均不可达）")

    if do_fetch:
        print(f"[2/3] 拉取并入库 POST /api/prices/fetch?symbol={symbol} ...")
        f = _post(f"/api/prices/fetch?symbol={symbol}&adjusted=true&outputsize=compact")
        print("      返回：", f)
    else:
        print("[2/3] 跳过拉取（未传 --fetch）")

    print(f"[3/3] 读取日线 GET /api/prices/daily?symbol={symbol}&limit={limit} ...")
    d = _get(f"/api/prices/daily?symbol={symbol}&limit={limit}")
    items = d.get("items") or []
    print(f"      共 {len(items)} 条")
    if items:
        print("      最后一条：", items[-1])
    print("\n✅ 冒烟测试完成。")

def _show_info():
    try:
        from backend.storage.db import engine
        url = str(engine.url)
        print("Database URL:", url)
        if url.startswith("sqlite:///"):
            p = Path(url.replace("sqlite:///", "", 1))
            print("SQLite 文件存在：", p.exists())
            print("SQLite 文件路径：", p)
        else:
            print("非 SQLite 数据库。")
    except Exception as e:
        print("读取数据库信息失败：", e)

# --- 放在其它函数旁边：在线自测新闻API ---
def _test_news(host: str, port: int, symbol: str, days: int, do_fetch: bool):
    import requests, json
    base = f"http://{host}:{port}"
    def _get(p):
        r = requests.get(base+p, timeout=60); r.raise_for_status(); return r.json()
    def _post(p):
        r = requests.post(base+p, timeout=120); r.raise_for_status(); return r.json()

    print("[1/3] 健康检查…", _get("/api/health"))
    if do_fetch:
        print(f"[2/3] 拉取并入库: {symbol} {days}天")
        print(json.dumps(_post(f"/api/news/fetch?symbol={symbol}&days={days}"), ensure_ascii=False))
    else:
        print("[2/3] 跳过拉取（--no-fetch）")
    print(f"[3/3] 查询时间轴: {symbol} {days}天")
    data = _get(f"/api/news/series?symbol={symbol}&days={days}")
    print("timeline天数:", len(data.get("timeline", [])), " items:", len(data.get("items", [])))
    if data.get("timeline"): print("样例:", data["timeline"][-1])


def main(argv=None):
    parser = argparse.ArgumentParser(description="AInvestorAgent Runner")
    sub = parser.add_subparsers(dest="cmd")

    p_serve = sub.add_parser("serve", help="启动 API 服务（默认命令）")
    p_serve.add_argument("--host", type=str, default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.add_argument("--no-open", action="store_true")

    p_test = sub.add_parser("test", help="对已运行服务做冒烟测试")
    p_test.add_argument("--host", type=str, default="127.0.0.1")
    p_test.add_argument("--port", type=int, default=8000)
    p_test.add_argument("--symbol", type=str, default="AAPL")
    p_test.add_argument("--limit", type=int, default=5)
    p_test.add_argument("--fetch", action="store_true")

    p_test_news = sub.add_parser("test-news", help="在线自测新闻接口")
    p_test_news.add_argument("--host", type=str, default="127.0.0.1")
    p_test_news.add_argument("--port", type=int, default=8000)
    p_test_news.add_argument("--symbol", type=str, default="AAPL")
    p_test_news.add_argument("--days", type=int, default=7)
    p_test_news.add_argument("--no-fetch", action="store_true")

    sub.add_parser("info", help="打印数据库配置等信息")

    args = parser.parse_args(argv)
    if args.cmd is None:
        return _serve()
    if args.cmd == "serve":
        return _serve(host=args.host, port=args.port, reload=args.reload, auto_open=not args.no_open)
    if args.cmd == "test":
        return _smoke_test(host=args.host, port=args.port, symbol=args.symbol, limit=args.limit, do_fetch=args.fetch)
    if args.cmd == "info":
        return _show_info()
    if args.cmd == "test-news":
        return _test_news(host=args.host, port=args.port, symbol=args.symbol, days=args.days,
                          do_fetch=not args.no_fetch)
    parser.print_help()
    return 0

if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
