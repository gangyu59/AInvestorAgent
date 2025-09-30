# backend/api/routers/testing.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import subprocess
import time
import sys
from pathlib import Path

# -------------- 原有内容保留：BEGIN --------------
router = APIRouter(prefix="/api/testing", tags=["testing"])


class TestRunRequest(BaseModel):
    file: str  # 例如: "tests/agents/test_all_agents.py"
    test: Optional[str] = None


class TestResult(BaseModel):
    passed: bool
    duration: float
    stdout: str
    stderr: str
    summary: str


@router.post("/run", response_model=TestResult)
def run_test(request: TestRunRequest):
    """
    运行测试文件并返回完整输出
    """
    project_root = Path(__file__).parent.parent.parent.parent
    test_file = project_root / request.file

    if not test_file.exists():
        return TestResult(
            passed=False,
            duration=0.0,
            stdout="",
            stderr=f"❌ 测试文件不存在\n\n完整路径: {test_file}\n\n请检查:\n1. 文件是否存在\n2. 路径是否正确",
            summary=f"文件不存在: {request.file}"
        )

    # 使用 python -m pytest 代替直接调用 pytest
    # 这样可以确保使用正确的 Python 环境
    cmd = [
        sys.executable,  # 当前Python解释器
        "-m",
        "pytest",
        str(test_file),
        "-v",
        "--tb=short",
        "--color=no",
        "-p", "no:warnings"  # 禁用警告以简化输出
    ]

    if request.test:
        cmd.extend(["-k", request.test])

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project_root),
            encoding='utf-8',
            errors='replace'
        )

        duration = time.time() - start_time
        passed = result.returncode == 0

        # 提取摘要
        summary = extract_summary(result.stdout, result.stderr, passed)

        # 合并输出
        full_output = ""
        if result.stdout:
            full_output += result.stdout
        if result.stderr and result.stderr.strip():
            if full_output:
                full_output += "\n\n=== STDERR ===\n"
            full_output += result.stderr

        return TestResult(
            passed=passed,
            duration=round(duration, 2),
            stdout=full_output if full_output else "无输出",
            stderr="",
            summary=summary
        )

    except subprocess.TimeoutExpired:
        return TestResult(
            passed=False,
            duration=60.0,
            stdout="",
            stderr="❌ 测试超时（超过60秒）\n\n可能原因:\n- 测试陷入死循环\n- 网络请求超时\n- 数据库操作过慢",
            summary="测试超时"
        )
    except Exception as e:
        error_msg = str(e)

        # 检查是否是 pytest 未安装
        if "No module named pytest" in error_msg or "No module named 'pytest'" in error_msg:
            return TestResult(
                passed=False,
                duration=0.0,
                stdout="",
                stderr=f"❌ pytest 模块未安装\n\n当前Python: {sys.executable}\n\n请在此环境中运行:\npip install pytest",
                summary="pytest未安装"
            )

        return TestResult(
            passed=False,
            duration=0.0,
            stdout="",
            stderr=f"❌ 执行失败\n\n错误: {error_msg}\n\nPython路径: {sys.executable}\n\n命令: {' '.join(cmd)}",
            summary=f"执行失败: {error_msg}"
        )


def extract_summary(stdout: str, stderr: str, passed: bool) -> str:
    """
    从pytest输出中提取摘要信息
    """
    # 先检查stderr中是否有错误
    if stderr and "error" in stderr.lower():
        lines = stderr.split('\n')
        for line in lines:
            if line.strip():
                return line.strip()[:100]

    # 查找pytest的摘要行
    lines = stdout.split('\n')
    for line in reversed(lines):
        line = line.strip()
        if any(keyword in line.lower() for keyword in ['passed', 'failed', 'error', 'no tests']):
            return line

    if passed:
        return "测试通过"
    else:
        return "测试失败"


@router.get("/health")
def health_check():
    """
    健康检查
    """
    pytest_ok = False
    pytest_version = "未安装"
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        pytest_ok = result.returncode == 0
        if pytest_ok:
            pytest_version = result.stdout.strip()
    except:
        pass

    return {
        "status": "ok",
        "pytest_available": pytest_ok,
        "pytest_version": pytest_version,
        "python_version": python_version,
        "python_path": sys.executable
    }
# -------------- 原有内容保留：END --------------

# -------------- 新增：Locust 压测控制 & 性能报告 --------------

import threading
import requests  # 在 requirements.txt 中应已包含；若无请补上
import json
from datetime import datetime

# 统一常量
_LOCUST_HOST = "127.0.0.1"
_LOCUST_PORT = 8089
_LOCUST_BASE = f"http://{_LOCUST_HOST}:{_LOCUST_PORT}"
_LOCUST_STATS = f"{_LOCUST_BASE}/stats/requests"
_LOCUST_SWARM = f"{_LOCUST_BASE}/swarm"
_LOCUST_STOP = f"{_LOCUST_BASE}/stop"

# 进程与状态
_LOCUST_PROC: Optional[subprocess.Popen] = None
_LOCUST_LOCK = threading.Lock()

def _project_root() -> Path:
    return Path(__file__).parent.parent.parent.parent

def _reports_dir() -> Path:
    return _project_root() / "reports"

def _default_locustfile() -> Path:
    # 文件树 tests/performance/locustfile.py
    return _project_root() / "tests" / "performance" / "locustfile.py"

class LocustStartRequest(BaseModel):
    users: int = 100
    spawn_rate: int = 10
    run_time: int = 60  # 秒，可选：仅作为自动停止的提示

@router.post("/locust/start")
def start_locust(req: LocustStartRequest):
    """
    启动 Locust（Web UI 模式）。若已在运行，直接返回 started。
    随后尝试调用 /swarm 以 users/spawn_rate 开始压测（如 UI 尚未就绪会自动忽略）。
    """
    global _LOCUST_PROC
    with _LOCUST_LOCK:
        # 若已在运行
        if _LOCUST_PROC and _LOCUST_PROC.poll() is None:
            _try_swarm(req.users, req.spawn_rate)
            return {"status": "started", "message": "Locust 已在运行", "ui": _LOCUST_BASE}

        locustfile = _default_locustfile()
        if not locustfile.exists():
            raise HTTPException(status_code=404, detail=f"未找到 locustfile: {locustfile}")

        cmd = [
            sys.executable, "-m", "locust",
            "-f", str(locustfile),
            "--host", "http://127.0.0.1:8000",  # 目标后端
            "--web-host", _LOCUST_HOST,
            "--web-port", str(_LOCUST_PORT),
        ]
        try:
            _LOCUST_PROC = subprocess.Popen(
                cmd,
                cwd=str(_project_root()),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        except FileNotFoundError:
            # 可能未安装 locust
            raise HTTPException(status_code=500, detail="未安装 locust，请先 pip install locust")

    # 等待 Web UI 就绪后尝试 swarm（最多尝试 10 次，每次 0.5s）
    for _ in range(10):
        time.sleep(0.5)
        if _try_swarm(req.users, req.spawn_rate):
            break

    return {"status": "started", "ui": _LOCUST_BASE}

def _try_swarm(users: int, spawn_rate: int) -> bool:
    try:
        r = requests.post(_LOCUST_SWARM, data={"user_count": users, "spawn_rate": spawn_rate}, timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False

@router.post("/locust/stop")
def stop_locust():
    """
    停止压测；若 Locust 进程在跑，也会尝试优雅退出。
    """
    global _LOCUST_PROC
    # 先尝试停止 swarm
    try:
        requests.get(_LOCUST_STOP, timeout=1.0)
    except Exception:
        pass

    with _LOCUST_LOCK:
        if _LOCUST_PROC and _LOCUST_PROC.poll() is None:
            try:
                _LOCUST_PROC.terminate()
                try:
                    _LOCUST_PROC.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    _LOCUST_PROC.kill()
            finally:
                _LOCUST_PROC = None

    return {"status": "stopped"}

@router.get("/locust/status")
def locust_status():
    """
    返回 Locust 运行状态与关键统计
    """
    running = False
    with _LOCUST_LOCK:
        running = _LOCUST_PROC is not None and _LOCUST_PROC.poll() is None

    stats: Dict[str, Any] = {}
    try:
        r = requests.get(_LOCUST_STATS, timeout=1.5)
        if r.status_code == 200:
            payload = r.json()
            # 取总览字段（Locust 提供 current_response_time_percentile 等）
            totals = payload.get("stats_total", {})
            stats = {
                "num_requests": totals.get("num_requests", 0),
                "num_failures": totals.get("num_failures", 0),
                "current_rps": totals.get("current_rps", 0.0),
                "avg_response_time": totals.get("avg_response_time", 0.0),
            }
    except Exception:
        # 无法获取 Web UI 状态时返回空统计
        pass

    return {"running": running, "stats": stats}

# ---------- 性能报告：列出/查看/生成 ----------

class ReportInfo(BaseModel):
    name: str
    filename: str
    timestamp: float
    size: int

def _safe_filename(name: str) -> str:
    # 防路径穿越
    return name.replace("/", "").replace("\\", "")

@router.get("/reports", response_model=List[ReportInfo])
def list_reports():
    """
    列出 reports/ 目录下的报告文件（.html/.json）
    """
    d = _reports_dir()
    d.mkdir(parents=True, exist_ok=True)
    items: List[ReportInfo] = []
    for p in sorted(d.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file() and p.suffix.lower() in {".html", ".json", ".txt"}:
            st = p.stat()
            items.append(ReportInfo(
                name=p.stem,
                filename=p.name,
                timestamp=st.st_mtime,
                size=st.st_size
            ))
    return items

@router.get("/reports/{filename}")
def get_report_file(filename: str):
    """
    返回报告文件内容（HTML 内嵌 iframe 时用）
    """
    safe = _safe_filename(filename)
    path = _reports_dir() / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")
    # 若是文本类，直接发送文件；由前端决定 iframe 还是 <pre>
    media_type = "text/html" if path.suffix.lower() == ".html" else "text/plain"
    return FileResponse(str(path), media_type=media_type, filename=path.name)

class GenerateReportRequest(BaseModel):
    type: str = "full"
    include_charts: bool = True

@router.post("/generate-report")
def generate_report(req: GenerateReportRequest):
    """
    生成一个性能/测试报告：
    1) 若存在 tests/performance/performance_report.py 则优先运行之；
    2) 否则生成一份简易 HTML 报告（含时间戳与环境信息）。
    """
    reports_dir = _reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    outfile = reports_dir / f"test_report_{ts}.html"

    perf_report = _project_root() / "tests" / "performance" / "performance_report.py"
    if perf_report.exists():
        # 调用性能报告脚本（建议脚本把输出写到 reports/ 并返回 0）
        cmd = [sys.executable, str(perf_report), "--out", str(outfile)]
        try:
            r = subprocess.run(cmd, cwd=str(_project_root()), capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                # 脚本异常则降级为简单报告
                _write_fallback_report(outfile, extra=f"<pre>{_escape_html(r.stdout + '\n' + r.stderr)}</pre>")
        except subprocess.TimeoutExpired:
            _write_fallback_report(outfile, extra="<p>报告脚本超时，生成占位报告。</p>")
        except Exception as e:
            _write_fallback_report(outfile, extra=f"<p>报告脚本错误：{_escape_html(str(e))}</p>")
    else:
        _write_fallback_report(outfile, extra="<p>未找到 performance_report.py，已生成占位报告。</p>")

    return {"success": True, "filename": outfile.name}

def _escape_html(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))

def _write_fallback_report(path: Path, extra: str = ""):
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>AInvestorAgent 报告</title></head>
<body style="font-family:Segoe UI,Arial,sans-serif;background:#0b1020;color:#e0e0e0">
<h2>📊 AInvestorAgent 自动报告</h2>
<p>时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<ul>
  <li>Python: {sys.version.split()[0]}</li>
  <li>路径: {_escape_html(sys.executable)}</li>
</ul>
{extra}
<hr>
<p style="color:#888">此为占位报告（fallback）。后续可替换为更完整的性能汇总。</p>
</body></html>"""
    path.write_text(html, encoding="utf-8")
