# backend/api/routers/testing.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import subprocess
import time
import sys
from pathlib import Path

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