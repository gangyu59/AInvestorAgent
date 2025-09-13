# -*- coding: utf-8 -*-
"""
运行 pytest，生成统计并记录到 reports/test_runs.jsonl（追加）。
可选：如果安装了 pytest-html，会生成 reports/last_report.html 供前端查看。
用法：
  python tools/run_tests_and_log.py
  python tools/run_tests_and_log.py backend/tests
"""
import sys, os, json, time, subprocess, shutil, datetime as dt
from xml.etree import ElementTree as ET

# ---- 路径与目录 ----
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # tools/ 的上一级
# ▶️ 如果已经是 AInvestorAgent，就不要再拼一次
if os.path.basename(ROOT) == "AInvestorAgent":
    PROJ = ROOT
else:
    PROJ = os.path.join(ROOT, "AInvestorAgent")

REPORT_DIR = os.path.join(PROJ, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

import webbrowser, socket

def _is_port_open(host="127.0.0.1", port=8000):
    s = socket.socket()
    s.settimeout(0.2)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()

_uvicorn_proc = None

def ensure_server(PROJ):
    global _uvicorn_proc
    if _is_port_open("127.0.0.1", 8000):
        return False  # 已在跑
    # Windows 后台启动（不堵塞当前进程）
    cmd = [sys.executable, "-m", "uvicorn", "backend.app:app", "--reload", "--port", "8000"]
    creationflags = 0
    if platform.system() == "Windows":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    _uvicorn_proc = subprocess.Popen(
        cmd, cwd=PROJ,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )
    # 简单等 0.8s
    for _ in range(8):
        if _is_port_open("127.0.0.1", 8000):
            return True
        time.sleep(0.1)
    return True  # 尽量不阻塞，就算没起来也继续

def run_pytest(target="backend/tests"):
    # ▶️ 目标目录自检：如果当前 PROJ 下没有这个目录，尝试在上层找一次
    candidate = os.path.join(PROJ, target)
    if not os.path.exists(candidate):
        alt = os.path.join(ROOT, target)
        if os.path.exists(alt):
            print(f"[info] target adjusted to: {alt}")
            target = alt
        else:
            print(f"[warn] target not found: {candidate}")

    junit_file = os.path.join(REPORT_DIR, "pytest_junit.xml")
    html_file  = os.path.join(REPORT_DIR, "last_report.html")

    cmd = [sys.executable, "-m", "pytest", "-q", target, f"--junitxml={junit_file}"]
    try:
        import pytest_html  # noqa
        cmd += [f"--html={html_file}", "--self-contained-html"]
    except Exception:
        pass

    print("[cwd]", PROJ)
    print("[cmd]", " ".join(cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=PROJ, capture_output=True, text=True)
    dt_sec = time.time() - t0
    return junit_file, html_file, dt_sec, proc.returncode, proc.stdout, proc.stderr

def parse_junit(junit_file):
    tree = ET.parse(junit_file)
    root = tree.getroot()
    # 兼容性：pytest 生成的根可能是 <testsuite> 或 <testsuites>
    suites = []
    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = root.findall("testsuite")

    total = passed = failed = skipped = xfailed = xpassed = errors = 0
    for s in suites:
        total += int(s.attrib.get("tests", "0"))
        failures = int(s.attrib.get("failures", "0"))
        errors   = errors + int(s.attrib.get("errors", "0"))
        skipped  += int(s.attrib.get("skipped", "0"))
        # 额外统计：从 <testcase> 的子节点里推测 xfail/xpass
        for tc in s.findall("testcase"):
            # 统计失败/成功
            fail_node = tc.find("failure")
            err_node  = tc.find("error")
            skip_node = tc.find("skipped")
            if fail_node is not None:
                failed += 1
            elif err_node is not None:
                # 已计入 errors
                pass
            elif skip_node is not None:
                # 已计入 skipped
                pass
            else:
                passed += 1
            # xfail/xpass 标记：pytest 会在 skipped 的 message 或失败里携带标记，这里只做占位
            # 真正需要可在代码里用 pytest markers 产出自定义 junit 属性，这里先留 0
        # failures 已经在 failed 中体现；errors 在 errors 中

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "xfailed": xfailed,
        "xpassed": xpassed,
        "errors": errors,
    }

def append_jsonl(record):
    jsonl = os.path.join(REPORT_DIR, "test_runs.jsonl")
    with open(jsonl, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "backend/tests"
    junit_file, html_file, dt_sec, rc, out, err = run_pytest(target)
    stats = parse_junit(junit_file) if os.path.exists(junit_file) else {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0, "xfailed": 0, "xpassed": 0, "errors": 0
    }
    ts = dt.datetime.now().isoformat(timespec="seconds")
    pass_rate = (stats["passed"] / stats["total"] * 100.0) if stats["total"] else 0.0
    record = {
        "timestamp": ts,
        "duration_sec": round(dt_sec, 3),
        "target": target,
        "stats": stats,
        "pass_rate": round(pass_rate, 2),
        "return_code": rc,
        "junit_xml": os.path.relpath(junit_file, PROJ) if os.path.exists(junit_file) else None,
        "html_report": os.path.relpath(html_file, PROJ) if os.path.exists(html_file) else None,
    }
    append_jsonl(record)
    # ---- 自动确保服务在跑 & 自动打开报告 ----
    ensure_server(PROJ)
    if record.get("html_report"):
        report_rel = record["html_report"]
        report_abs = os.path.join(PROJ, report_rel).replace("\\", "/")
        if _is_port_open("127.0.0.1", 8000):
            webbrowser.open("http://localhost:8000/reports/last_report.html")
        else:
            webbrowser.open("file:///" + report_abs)

    print(json.dumps(record, ensure_ascii=False, indent=2))
    # 也顺手保存 latest.json，便于前端快速读取
    with open(os.path.join(REPORT_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
