# tests/ui/conftest.py
"""
为 UI 测试提供本地 Playwright fixtures：
- 不依赖 pytest-playwright 插件
- 如未安装浏览器，自动执行: python -m playwright install <browser>
- 在测试开始前等待前端 dev server 就绪
环境变量（可选）：
  FRONTEND_BASE  默认 http://127.0.0.1:5173
  HEADLESS       默认 1（无头）；设为 0 可看见浏览器
  PW_BROWSER     默认 chromium（可选 firefox/webkit）
  UI_SERVER_WAIT 等待前端就绪的秒数，默认 20
"""
import os
import time
import subprocess
import sys
import pytest

FRONTEND_BASE = os.environ.get("FRONTEND_BASE", "http://127.0.0.1:5173")
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
BROWSER = os.environ.get("PW_BROWSER", "chromium")  # chromium/firefox/webkit
SERVER_WAIT_SECS = int(os.environ.get("UI_SERVER_WAIT", "20"))

# ------- 0) 基础依赖检查 -------
try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    pytest.skip(
        "Playwright 未安装：请先执行\n"
        "  pip install playwright requests\n"
        "（dashboard 环境只需一次即可）\n\n"
        f"详细错误：{e}",
        allow_module_level=True
    )

def _ensure_browsers_installed(browser: str) -> None:
    """
    尝试快速启动一次浏览器；若失败则用 `python -m playwright install <browser>` 安装。
    """
    try:
        with sync_playwright() as p:
            getattr(p, browser)  # 访问以触发可用性检查
            # 试开->关，确认驱动完整
            b = getattr(p, browser).launch(headless=True)
            b.close()
        return
    except Exception:
        # 安装浏览器（Windows 下 PATH 不含 playwright.exe 也没关系）
        cmd = [sys.executable, "-m", "playwright", "install", browser]
        try:
            subprocess.run(cmd, check=True, timeout=300)
        except Exception as ie:
            pytest.skip(
                f"自动安装浏览器失败：{' '.join(cmd)}\n"
                f"{ie}\n请手动运行同样命令后重试。",
                allow_module_level=True
            )

def _wait_frontend_alive(url: str, seconds: int) -> None:
    import requests
    deadline = time.time() + seconds
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            # 200/3xx/4xx 都算“端口活着”；只要能连通就行
            if r.status_code < 600:
                return
        except Exception as e:
            last_err = e
        time.sleep(0.5)
    pytest.skip(f"前端未就绪：{url}（等待 {seconds}s）\n最后错误：{last_err}", allow_module_level=True)

# ------- 1) 会话级准备：安装浏览器 + 等待前端 -------
@pytest.fixture(scope="session", autouse=True)
def _bootstrap_ui():
    _ensure_browsers_installed(BROWSER)
    _wait_frontend_alive(FRONTEND_BASE, SERVER_WAIT_SECS)

# ------- 2) Playwright fixtures -------
@pytest.fixture(scope="session")
def _playwright():
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def _browser(_playwright):
    browser = getattr(_playwright, BROWSER).launch(headless=HEADLESS)
    yield browser
    browser.close()

@pytest.fixture(scope="function")
def context(_browser):
    ctx = _browser.new_context(viewport={"width": 1440, "height": 900})
    yield ctx
    ctx.close()

@pytest.fixture(scope="function")
def page(context):
    pg = context.new_page()
    yield pg
    pg.close()
