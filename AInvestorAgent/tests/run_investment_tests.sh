#!/bin/bash
# AInvestorAgent 投资就绪测试 - 一键启动脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 打印标题
print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

# 检查后端服务
check_backend() {
    print_info "检查后端服务..."

    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "后端服务运行正常"
        return 0
    else
        print_error "后端服务未运行"
        return 1
    fi
}

# 启动后端服务
start_backend() {
    print_info "启动后端服务..."

    if [ -f "run.py" ]; then
        python run.py > logs/backend.log 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > .backend.pid

        # 等待服务启动
        print_info "等待服务启动 (最多30秒)..."
        for i in {1..30}; do
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                print_success "后端服务已启动 (PID: $BACKEND_PID)"
                return 0
            fi
            sleep 1
            echo -n "."
        done

        print_error "后端服务启动超时"
        return 1
    else
        print_error "找不到 run.py 文件"
        return 1
    fi
}

# 更新数据
update_data() {
    print_info "更新系统数据..."

    if [ "$SKIP_UPDATE" == "true" ]; then
        print_warning "跳过数据更新 (--skip-update)"
        return 0
    fi

    # 更新价格数据
    if [ -f "scripts/fetch_prices.py" ]; then
        print_info "更新价格数据..."
        python scripts/fetch_prices.py AAPL MSFT GOOGL NVDA AMZN TSLA META SPY || print_warning "价格数据更新失败"
    fi

    # 更新新闻数据
    if [ -f "scripts/fetch_news.py" ]; then
        print_info "更新新闻数据..."
        python scripts/fetch_news.py --symbols AAPL,MSFT,GOOGL --days 7 --noproxy || print_warning "新闻数据更新失败"
    fi

    # 重算因子
    if [ -f "scripts/rebuild_factors.py" ]; then
        print_info "重新计算因子..."
        python scripts/rebuild_factors.py --symbols AAPL,MSFT,GOOGL || print_warning "因子计算失败"
    fi

    print_success "数据更新完成"
}

# 运行测试
run_tests() {
    print_info "开始执行投资就绪测试..."

    if [ ! -f "tests/investment_test_executor.py" ]; then
        print_error "找不到测试执行器: tests/investment_test_executor.py"
        return 1
    fi

    # 构建测试命令
    TEST_CMD="python tests/investment_test_executor.py"

    if [ "$QUICK_MODE" == "true" ]; then
        TEST_CMD="$TEST_CMD --quick"
        print_info "运行快速测试 (仅P0级别)"
    else
        print_info "运行完整测试 (全部310项)"
    fi

    if [ -n "$TEST_SUITE" ]; then
        TEST_CMD="$TEST_CMD --suite $TEST_SUITE"
        print_info "仅测试套件: $TEST_SUITE"
    fi

    # 执行测试
    $TEST_CMD
    TEST_EXIT_CODE=$?

    if [ $TEST_EXIT_CODE -eq 0 ]; then
        print_success "测试完成 - 系统就绪"
        return 0
    else
        print_warning "测试完成 - 系统未就绪 (需要修复)"
        return 1
    fi
}

# 打开Web界面
open_web_ui() {
    if [ "$NO_BROWSER" == "true" ]; then
        return 0
    fi

    print_info "打开Web测试界面..."

    # 判断操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "http://localhost:8000/tests/investment_readiness.html" 2>/dev/null || \
        open "tests/investment_readiness.html" 2>/dev/null
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open "http://localhost:8000/tests/investment_readiness.html" 2>/dev/null || \
        xdg-open "tests/investment_readiness.html" 2>/dev/null
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        start "http://localhost:8000/tests/investment_readiness.html" 2>/dev/null || \
        start "tests/investment_readiness.html" 2>/dev/null
    fi

    print_success "Web界面已打开"
}

# 生成最终报告
generate_final_report() {
    print_info "生成最终投资决策报告..."

    REPORT_FILE="tests/reports/investment_readiness_report.json"

    if [ ! -f "$REPORT_FILE" ]; then
        print_warning "未找到测试报告文件"
        return 1
    fi

    # 提取关键信息
    PASS_RATE=$(cat "$REPORT_FILE" | python -c "import sys, json; print(json.load(sys.stdin)['summary']['pass_rate'])" 2>/dev/null || echo "N/A")
    WEIGHTED_RATE=$(cat "$REPORT_FILE" | python -c "import sys, json; print(json.load(sys.stdin)['summary']['weighted_pass_rate'])" 2>/dev/null || echo "N/A")
    READY=$(cat "$REPORT_FILE" | python -c "import sys, json; print('true' if json.load(sys.stdin)['summary']['investment_ready'] else 'false')" 2>/dev/null || echo "false")

    print_header "投资决策报告"

    echo "📊 测试摘要"
    echo "   - 通过率: $PASS_RATE%"
    echo "   - 加权通过率: $WEIGHTED_RATE%"
    echo ""

    if [ "$READY" == "true" ]; then
        print_success "投资决策: ✅ 系统就绪,可以开始投资"
        echo ""
        echo "📋 建议:"
        echo "   1. 从小额资金开始 (建议总资金的10%)"
        echo "   2. 设置止损线 (单笔-10%, 总-15%)"
        echo "   3. 持续监控实盘表现"
        echo "   4. 每周运行回归测试"
        echo ""
        return 0
    else
        print_warning "投资决策: ⚠️  系统未就绪,建议修复失败项"
        echo ""
        echo "📋 下一步:"
        echo "   1. 查看详细报告: $REPORT_FILE"
        echo "   2. 修复失败的测试项"
        echo "   3. 重新运行测试"
        echo ""
        return 1
    fi
}

# 清理函数
cleanup() {
    print_info "清理中..."

    if [ -f ".backend.pid" ]; then
        BACKEND_PID=$(cat .backend.pid)
        if kill -0 $BACKEND_PID 2>/dev/null; then
            print_info "停止后端服务 (PID: $BACKEND_PID)"
            kill $BACKEND_PID 2>/dev/null || true
        fi
        rm -f .backend.pid
    fi
}

# 显示帮助
show_help() {
    cat << EOF
AInvestorAgent 投资就绪测试 - 一键启动脚本

用法:
    ./run_investment_tests.sh [选项]

选项:
    --quick              快速测试模式 (仅P0级别, 约5分钟)
    --full               完整测试模式 (全部310项, 约20分钟) [默认]
    --suite <name>       仅运行指定测试套件
    --skip-update        跳过数据更新
    --no-browser         不自动打开浏览器
    --web-only           仅打开Web界面,不运行命令行测试
    --check-only         仅检查系统状态,不运行测试
    -h, --help           显示此帮助信息

示例:
    # 运行完整测试
    ./run_investment_tests.sh

    # 快速测试
    ./run_investment_tests.sh --quick

    # 仅测试功能完整性
    ./run_investment_tests.sh --suite functional

    # 跳过数据更新
    ./run_investment_tests.sh --skip-update

    # 仅打开Web界面
    ./run_investment_tests.sh --web-only

测试套件列表:
    - functional         功能完整性 (48项)
    - dataQuality        数据质量 (30项)
    - agentIntelligence  智能体能力 (40项)
    - apiStability       API性能 (25项)
    - visualization      可视化 (45项)
    - backtestQuality    回测有效性 (35项)
    - multiAgent         多智能体协同 (28项)
    - edgeCases          边界容错 (32项)
    - production         生产就绪性 (27项)

EOF
}

# 主函数
main() {
    # 解析参数
    QUICK_MODE=false
    SKIP_UPDATE=false
    NO_BROWSER=false
    WEB_ONLY=false
    CHECK_ONLY=false
    TEST_SUITE=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --full)
                QUICK_MODE=false
                shift
                ;;
            --suite)
                TEST_SUITE="$2"
                shift 2
                ;;
            --skip-update)
                SKIP_UPDATE=true
                shift
                ;;
            --no-browser)
                NO_BROWSER=true
                shift
                ;;
            --web-only)
                WEB_ONLY=true
                NO_BROWSER=false
                shift
                ;;
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 打印标题
    print_header "🎯 AInvestorAgent 投资就绪测试"

    # 创建必要的目录
    mkdir -p logs
    mkdir -p tests/reports

    # 注册清理函数
    trap cleanup EXIT

    # 检查后端服务
    if ! check_backend; then
        print_warning "后端服务未运行,尝试启动..."
        if ! start_backend; then
            print_error "无法启动后端服务,请手动启动: python run.py"
            exit 1
        fi
    fi

    # 仅检查模式
    if [ "$CHECK_ONLY" == "true" ]; then
        print_success "系统状态检查完成"
        exit 0
    fi

    # 仅Web界面模式
    if [ "$WEB_ONLY" == "true" ]; then
        open_web_ui
        print_info "Web界面已打开,请在浏览器中查看"
        print_info "按 Ctrl+C 停止后端服务"

        # 保持脚本运行
        while true; do
            sleep 1
        done
    fi

    # 更新数据
    update_data

    # 运行测试
    if run_tests; then
        TEST_PASSED=true
    else
        TEST_PASSED=false
    fi

    # 生成最终报告
    generate_final_report
    REPORT_EXIT=$?

    # 打开Web界面
    if [ "$TEST_PASSED" == "true" ]; then
        open_web_ui
    fi

    # 返回退出码
    if [ "$TEST_PASSED" == "true" ] && [ $REPORT_EXIT -eq 0 ]; then
        print_header "🎉 投资就绪测试完成 - 系统就绪"
        exit 0
    else
        print_header "⚠️  投资就绪测试完成 - 系统未就绪"
        exit 1
    fi
}

# 执行主函数
main "$@"