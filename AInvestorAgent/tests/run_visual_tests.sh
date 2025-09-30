#!/bin/bash

# AInvestorAgent 可视化测试启动脚本
# 用法: ./tests/run_visual_tests.sh [选项]
# 选项:
#   --full      运行完整测试（包括慢速测试）
#   --quick     仅运行快速测试
#   --report    仅生成测试报告

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_header "检查依赖"

    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    print_success "Python3: $(python3 --version)"

    if ! command -v node &> /dev/null; then
        print_error "Node.js 未安装"
        exit 1
    fi
    print_success "Node.js: $(node --version)"

    # 检查Python包
    python3 -c "import pytest" 2>/dev/null || {
        print_error "pytest 未安装，正在安装..."
        pip3 install pytest pytest-html pytest-asyncio
    }
    print_success "pytest 已安装"

    # 检查后端是否运行
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "后端服务运行中 (http://localhost:8000)"
    else
        print_warning "后端服务未运行，将尝试启动..."
        start_backend
    fi

    echo ""
}

# 启动后端
start_backend() {
    print_header "启动后端服务"

    cd "$(dirname "$0")/.."

    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_warning "虚拟环境不存在，创建中..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi

    # 启动后端（后台运行）
    nohup python run.py > tests/logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > tests/logs/backend.pid

    # 等待后端启动
    print_warning "等待后端启动..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "后端启动成功 (PID: $BACKEND_PID)"
            return 0
        fi
        sleep 1
    done

    print_error "后端启动超时"
    exit 1
}

# 停止后端
stop_backend() {
    if [ -f tests/logs/backend.pid ]; then
        PID=$(cat tests/logs/backend.pid)
        if ps -p $PID > /dev/null; then
            print_warning "停止后端服务 (PID: $PID)"
            kill $PID
            rm tests/logs/backend.pid
        fi
    fi
}

# 运行Python测试
run_python_tests() {
    print_header "运行Python测试套件"

    cd "$(dirname "$0")/.."
    mkdir -p tests/reports

    # 运行测试并生成HTML报告
    python3 tests/test_runner.py | tee tests/reports/test_output.txt

    # 运行详细测试用例
    if [ "$1" == "--full" ]; then
        pytest tests/test_cases_detailed.py -v \
            --html=tests/reports/detailed_report.html \
            --self-contained-html \
            --tb=short
    fi

    print_success "测试报告已生成: tests/reports/"
}

# 启动可视化测试控制台
start_visual_dashboard() {
    print_header "启动可视化测试控制台"

    # 创建临时HTML文件
    cat > tests/visual_dashboard.html << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AInvestorAgent 测试控制台</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 3em;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
        }
        .stat-value {
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }
        .stat-label {
            font-size: 0.9em;
            color: rgba(255, 255, 255, 0.6);
        }
        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            justify-content: center;
        }
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: white;
        }
        .test-suite {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .suite-header {
            padding: 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .suite-title {
            font-size: 1.2em;
            font-weight: 600;
        }
        .priority {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .priority-p0 { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .priority-p1 { background: rgba(251, 146, 60, 0.2); color: #fb923c; }
        .priority-p2 { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .iframe-container {
            margin-top: 40px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        iframe {
            width: 100%;
            height: 800px;
            border: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 AInvestorAgent 测试控制台</h1>
            <p style="color: rgba(255,255,255,0.6);">全面的可视化测试系统 - 确保系统投资就绪</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">测试套件</div>
                <div class="stat-value">8</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">总测试项</div>
                <div class="stat-value" id="total-tests">283</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">预计时间</div>
                <div class="stat-value">~15min</div>
            </div>
        </div>

        <div class="controls">
            <button class="btn btn-primary" onclick="runTests()">▶ 运行全部测试</button>
            <button class="btn btn-secondary" onclick="runQuickTests()">⚡ 快速测试</button>
            <button class="btn btn-secondary" onclick="viewReports()">📊 查看报告</button>
        </div>

        <div class="iframe-container">
            <iframe src="about:blank" id="test-frame"></iframe>
        </div>
    </div>

    <script>
        function runTests() {
            document.getElementById('test-frame').src = 'http://localhost:8000/tests/dashboard';
            alert('正在启动完整测试...\n这将需要约15分钟');
        }

        function runQuickTests() {
            alert('快速测试模式\n仅运行核心P0测试项（约5分钟）');
        }

        function viewReports() {
            window.open('reports/test_report.html', '_blank');
        }
    </script>
</body>
</html>
EOF

    print_success "可视化控制台已创建: tests/visual_dashboard.html"

    # 在浏览器中打开
    if command -v open &> /dev/null; then
        open tests/visual_dashboard.html
    elif command -v xdg-open &> /dev/null; then
        xdg-open tests/visual_dashboard.html
    else
        print_warning "请手动打开: tests/visual_dashboard.html"
    fi
}

# 生成测试报告
generate_report() {
    print_header "生成测试报告"

    python3 << 'EOF'
import json
import sys
from pathlib import Path
from datetime import datetime

# 读取测试结果
results_file = Path("tests/reports/test_results.json")
if not results_file.exists():
    print("❌ 测试结果文件不存在，请先运行测试")
    sys.exit(1)

with open(results_file) as f:
    data = json.load(f)

# 生成Markdown报告
report = f"""# AInvestorAgent 测试报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 测试概览

| 指标 | 数值 |
|------|------|
| 总测试项 | {data['summary']['total_tests']} |
| 通过项 | {data['summary']['total_passed']} |
| 失败项 | {data['summary']['total_failed']} |
| 通过率 | {data['summary']['pass_rate']:.1f}% |

## 🎯 投资就绪度评估

"""

pass_rate = data['summary']['pass_rate']
if pass_rate >= 95:
    report += "✅ **系统就绪** - 可以进行真实投资\n\n"
elif pass_rate >= 80:
    report += "⚠️ **需要优化** - 建议修复失败项后再投资\n\n"
else:
    report += "❌ **未就绪** - 必须修复关键问题\n\n"

report += "## 📦 测试套件详情\n\n"

for suite in data['suites']:
    status_emoji = "✅" if suite['status'] == 'passed' else "❌"
    report += f"### {status_emoji} {suite['name']} ({suite['priority']})\n\n"
    report += f"- 通过: {suite['passed']}/{suite['total']}\n"
    report += f"- 失败: {suite['failed']}/{suite['total']}\n\n"

    # 列出失败的测试
    failed_tests = [t for t in suite['tests'] if t['status'] == 'failed']
    if failed_tests:
        report += "**失败的测试:**\n\n"
        for test in failed_tests:
            report += f"- ❌ {test['name']}\n"
            if test.get('error'):
                report += f"  ```\n  {test['error']}\n  ```\n"
        report += "\n"

# 保存Markdown报告
report_file = Path("tests/reports/TEST_REPORT.md")
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report)

print(f"✓ 测试报告已生成: {report_file}")

EOF
}

# 清理测试环境
cleanup() {
    print_header "清理测试环境"
    stop_backend
    print_success "清理完成"
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p tests/logs tests/reports

    MODE=${1:-"--full"}

    case $MODE in
        --quick)
            print_header "快速测试模式"
            check_dependencies
            run_python_tests
            ;;
        --report)
            print_header "仅生成报告"
            generate_report
            ;;
        --full)
            print_header "完整测试模式"
            check_dependencies
            run_python_tests --full
            generate_report
            start_visual_dashboard
            ;;
        --visual)
            print_header "可视化测试控制台"
            check_dependencies
            start_visual_dashboard
            ;;
        *)
            echo "用法: $0 [--full|--quick|--report|--visual]"
            echo ""
            echo "选项:"
            echo "  --full     运行完整测试（默认）"
            echo "  --quick    快速测试（仅核心功能）"
            echo "  --report   仅生成测试报告"
            echo "  --visual   启动可视化测试控制台"
            exit 1
            ;;
    esac

    # 捕获退出信号，确保清理
    trap cleanup EXIT

    echo ""
    print_success "测试完成！"
    echo ""
    echo "📄 查看报告:"
    echo "   - Markdown: tests/reports/TEST_REPORT.md"
    echo "   - HTML: tests/reports/detailed_report.html"
    echo "   - JSON: tests/reports/test_results.json"
    echo ""
}

# 运行主函数
main "$@"