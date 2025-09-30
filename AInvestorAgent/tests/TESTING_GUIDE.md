# AInvestorAgent 测试系统使用指南

## 📋 目录

1. [快速开始](#快速开始)
2. [测试系统架构](#测试系统架构)
3. [运行测试](#运行测试)
4. [测试报告解读](#测试报告解读)
5. [30天实盘模拟](#30天实盘模拟)
6. [投资前检查清单](#投资前检查清单)

---

## 🚀 快速开始

### 前置条件

```bash
# 1. 确保后端运行中
python run.py

# 2. 安装测试依赖
pip install pytest pytest-html pytest-asyncio matplotlib pandas
```

### 一键运行所有测试

```bash
# 赋予执行权限
chmod +x tests/run_visual_tests.sh

# 运行完整测试（推荐）
./tests/run_visual_tests.sh --full

# 快速测试（仅核心功能，约5分钟）
./tests/run_visual_tests.sh --quick

# 仅启动可视化控制台
./tests/run_visual_tests.sh --visual
```

---

## 🏗️ 测试系统架构

```
tests/
├── test_runner.py              # 自动化测试执行器
├── test_cases_detailed.py      # 详细测试用例
├── paper_trading_simulator.py  # 30天实盘模拟
├── run_visual_tests.sh         # 测试启动脚本
├── visual_dashboard.html       # 可视化控制台
│
├── reports/                    # 测试报告输出
│   ├── TEST_REPORT.md          # Markdown报告
│   ├── detailed_report.html    # HTML详细报告
│   ├── test_results.json       # JSON结构化结果
│   └── paper_trading_*.{md,png,csv}  # 实盘模拟报告
│
└── logs/                       # 测试日志
    ├── backend.log
    └── paper_trading_log.jsonl
```

### 8大测试套件

| 优先级 | 测试套件 | 测试项 | 预计时间 |
|--------|----------|--------|----------|
| **P0** | 功能完整性测试 | 48项 | 3分钟 |
| **P0** | 数据质量测试 | 30项 | 2分钟 |
| **P0** | 回测有效性测试 | 35项 | 5分钟 |
| **P1** | 智能体能力测试 | 40项 | 4分钟 |
| **P1** | API性能测试 | 25项 | 2分钟 |
| **P1** | 可视化测试 | 45项 | 3分钟 |
| **P2** | 边界与容错测试 | 28项 | 2分钟 |
| **P2** | 生产就绪性测试 | 32项 | 4分钟 |

**总计**: 283个测试项，预计15分钟

---

## 🧪 运行测试

### 方法1: 使用Shell脚本（推荐）

```bash
# 完整测试 + 可视化控制台
./tests/run_visual_tests.sh --full

# 快速测试（仅P0关键项）
./tests/run_visual_tests.sh --quick

# 仅生成报告（基于已有结果）
./tests/run_visual_tests.sh --report
```

### 方法2: 直接运行Python

```bash
# 运行自动化测试
python tests/test_runner.py

# 运行详细测试用例
pytest tests/test_cases_detailed.py -v --html=tests/reports/detailed_report.html

# 运行特定测试类
pytest tests/test_cases_detailed.py::TestFunctionalCompleteness -v

# 运行特定测试方法
pytest tests/test_cases_detailed.py::TestFunctionalCompleteness::test_01_data_ingestion_prices -v
```

### 方法3: 使用可视化控制台

1. 启动控制台:
```bash
./tests/run_visual_tests.sh --visual
```

2. 在浏览器中打开 `tests/visual_dashboard.html`

3. 点击按钮:
   - **▶ 运行全部测试**: 执行所有283项测试
   - **⚡ 快速测试**: 仅运行P0关键测试
   - **📊 查看报告**: 打开测试报告

---

## 📊 测试报告解读

### 通过率评估标准

| 通过率 | 评级 | 建议 |
|--------|------|------|
| ≥ 95% | ✅ 就绪 | 可以进行真实投资 |
| 80-95% | ⚠️ 需优化 | 修复失败项后再投资 |
| < 80% | ❌ 未就绪 | 必须修复关键问题 |

### 关键指标解读

#### 1. 功能完整性 (P0)
- **通过标准**: 100%通过
- **失败影响**: 阻断性问题，系统无法正常使用
- **常见失败**:
  - 数据获取失败（API限额、网络问题）
  - 因子计算错误（数据缺失）
  - 组合约束未生效（权重超限）

#### 2. 数据质量 (P0)
- **通过标准**: ≥95%通过
- **失败影响**: 数据不可靠，决策可能错误
- **常见失败**:
  - 价格数据缺失（停牌、退市）
  - 情绪分数偏差过大（LLM不稳定）
  - 基本面数据过期（未及时更新）

#### 3. 回测有效性 (P0)
- **通过标准**: 100%通过
- **失败影响**: 无法验证策略有效性
- **关键指标**:
  - Alpha > 2%（超额收益）
  - Sharpe > 0.5（风险调整后收益）
  - 因子IC > 0.05（因子有效性）

#### 4. 智能体协同 (P1)
- **通过标准**: ≥90%通过
- **失败影响**: 决策质量下降
- **常见失败**:
  - 某智能体超时
  - 冲突解决机制失效
  - Trace记录不完整

#### 5. API性能 (P1)
- **通过标准**: ≥90%通过
- **失败影响**: 用户体验差
- **性能目标**:
  - 95%请求 ≤ 2秒
  - 99%请求 ≤ 5秒
  - 并发10 QPS无崩溃

---

## 🔄 30天实盘模拟

### 为什么需要30天模拟？

在真实投资前，必须验证系统在真实市场环境下的表现：
- 回测可能过拟合历史数据
- 实时决策可能遇到数据延迟、API故障等问题
- 需要观察系统在不同市场状态下的适应能力

### 运行实盘模拟

```bash
# 使用默认参数（10万初始资金，4周）
python tests/paper_trading_simulator.py

# 自定义参数
python tests/paper_trading_simulator.py --capital 50000 --weeks 8
```

### 模拟运行流程

```
第1周 (第1天)
├── 调用 /orchestrator/decide 生成组合
├── 执行虚拟买入（扣除0.1%成本）
├── 记录持仓与净值
└── 等待7天

第2周 (第8天)
├── 获取当前价格
├── 计算组合表现
├── 重新生成组合
├── 执行调仓（卖出/买入）
└── 记录净值变化

...（重复至第4周）

第4周 (第30天)
├── 最后一次调仓
├── 计算总收益
├── 生成完整报告
└── 输出净值曲线图
```

### 模拟报告内容

生成的报告包含：

1. **PAPER_TRADING_REPORT.md**: 完整业绩报告
   - 总收益率
   - 最大回撤
   - Sharpe比率
   - 调仓次数
   - 就绪度评估

2. **paper_trading_nav.png**: 净值与回撤曲线图

3. **paper_trading_history.csv**: 逐日详细数据
   ```csv
   date,week,nav,cash,positions,holdings
   2025-09-29,1,1.0000,100000,0,[]
   2025-10-06,2,1.0235,5000,8,[...]
   ...
   ```

4. **paper_trading_log.jsonl**: 完整操作日志
   ```json
   {"timestamp":"2025-09-29T10:00:00","event":"BUY","data":{"symbol":"AAPL","shares":100,"price":180.5}}
   {"timestamp":"2025-09-29T10:01:00","event":"BUY","data":{"symbol":"MSFT","shares":80,"price":350.2}}
   ```

### 通过标准

✅ **可以进行小额实盘**，如果：
- 30天收益 > 0
- 最大回撤 < 15%
- Sharpe > 0.5
- 无系统崩溃或严重错误

⚠️ **需要进一步优化**，如果：
- 收益为负但回撤可控
- Sharpe < 0.5
- 有频繁的技术故障

❌ **不建议实盘**，如果：
- 收益 < -5%
- 最大回撤 > 20%
- 系统频繁崩溃

---

## ✅ 投资前检查清单

### 阶段1: 基础测试（1-2天）

- [ ] 运行完整测试套件
  ```bash
  ./tests/run_visual_tests.sh --full
  ```
- [ ] 通过率 ≥ 95%
- [ ] 所有P0测试100%通过
- [ ] 查看详细报告，确认无阻断性问题

### 阶段2: 数据验证（1天）

- [ ] 手工验证10支股票的价格数据准确性
- [ ] 对比外部源（Yahoo Finance）确认一致性
- [ ] 检查新闻情绪分数是否合理
- [ ] 验证基本面数据时效性（≤90天）

### 阶段3: 回测验证（1-2天）

- [ ] 运行多个历史窗口回测（6M, 1Y, 2Y）
- [ ] 验证Alpha > 2%
- [ ] 验证Sharpe > 0.5
- [ ] 检查极端市场表现（2020年3月、2022年全年）

### 阶段4: 实盘模拟（30天）

- [ ] 运行30天实盘模拟
  ```bash
  python tests/paper_trading_simulator.py --capital 100000 --weeks 4
  ```
- [ ] 每周检查模拟日志，确认无技术故障
- [ ] 30天后查看报告，验证通过标准
- [ ] 对比模拟表现 vs 回测预期（误差≤20%）

### 阶段5: 人工审核（1-2天）

- [ ] 邀请至少2位金融专业人士审核组合
- [ ] 检查持仓是否合理（无明显错误）
- [ ] 验证风险控制有效（行业/个股集中度）
- [ ] 确认无已知重大风险（如财务造假公司）

### 阶段6: 合规与风险（1天）

- [ ] 添加免责声明到所有报告
  ```
  本系统仅供参考，不构成投资建议。
  投资有风险，决策需谨慎。
  ```
- [ ] 制定应急预案（系统故障时如何止损）
- [ ] 设定初始投资金额 ≤ 总资金的10%
- [ ] 设定止损线（如-15%强制平仓）
- [ ] 建立定期评估机制（每月复盘）

### 阶段7: 最终确认

- [ ] 我已完成上述所有检查项
- [ ] 我理解系统的局限性和风险
- [ ] 我已设定合理的预期收益（如年化10-15%）
- [ ] 我已准备好应对可能的损失
- [ ] 我确认系统可用于真实投资

**签字确认**: ________________  
**日期**: ________________

---

## 🛠️ 故障排查

### 常见问题

#### 1. 测试无法启动

**问题**: `./tests/run_visual_tests.sh` 提示 "Permission denied"

**解决**:
```bash
chmod +x tests/run_visual_tests.sh
```

#### 2. 后端连接失败

**问题**: 测试提示 "Connection refused"

**解决**:
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 如果未运行，启动后端
python run.py
```

#### 3. API超时

**问题**: 部分测试超时失败

**解决**:
- 检查网络连接
- 增加超时时间（修改 `TIMEOUT = 30` 为更大值）
- 检查AlphaVantage/News API限额

#### 4. 数据缺失

**问题**: 价格或新闻数据为空

**解决**:
```bash
# 重新拉取数据
python scripts/fetch_prices.py --symbols AAPL,MSFT,GOOGL
python scripts/fetch_news.py --symbols AAPL,MSFT,GOOGL --days 14 --noproxy
```

#### 5. 测试报告未生成

**问题**: `tests/reports/` 目录为空

**解决**:
```bash
# 手动创建目录
mkdir -p tests/reports tests/logs

# 重新运行测试
python tests/test_runner.py
```

---

## 📈 持续监控（投资后）

### 日常监控（每天）

```bash
# 检查系统健康状态
curl http://localhost:8000/health

# 查看最新组合快照
# 访问前端: http://localhost:3000
```

### 周度评估（每周一）

```bash
# 生成周报
curl -X POST http://localhost:8000/api/report/weekly

# 对比实际表现 vs 系统预测
# 记录偏差原因
```

### 月度复盘（每月1日）

1. 运行完整测试套件，确认通过率
2. 对比月度收益 vs 基准（SPY）
3. 分析超额收益来源（选股 vs 择时）
4. 检查因子有效性是否衰减
5. 必要时调整策略权重

### 预警阈值

立即停止投资，如果：
- 单日亏损 > 5%
- 周度亏损 > 10%
- 回撤 > 预设止损线
- 系统连续3天无法正常运行

---

## 📚 进阶主题

### 扩展测试覆盖

```bash
# 添加自定义测试用例
# 编辑 tests/test_cases_detailed.py，添加新方法

class TestCustom:
    def test_my_scenario(self):
        # 你的测试逻辑
        pass

# 运行自定义测试
pytest tests/test_cases_detailed.py::TestCustom -v
```

### 集成CI/CD

```yaml
# .github/workflows/test.yml
name: AInvestorAgent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements.txt
          python tests/test_runner.py
      - name: Upload reports
        uses: actions/upload-artifact@v2
        with:
          name: test-reports
          path: tests/reports/
```

### 性能压测

```bash
# 使用Locust进行压力测试
pip install locust

# 创建 tests/locustfile.py
# 运行压测
locust -f tests/locustfile.py --host=http://localhost:8000
```

---

## 🆘 获取帮助

- **文档**: 查看 `docs/` 目录下的详细文档
- **日志**: 检查 `tests/logs/` 目录
- **Issue**: 在GitHub上提交问题

---

## 📝 总结

这套测试系统确保你的AInvestorAgent在真实投资前：

✅ **功能完整** - 所有核心功能正常工作  
✅ **数据可靠** - 数据准确、及时、完整  
✅ **策略有效** - 回测和实盘模拟表现良好  
✅ **系统稳定** - 性能达标、容错健壮  
✅ **风险可控** - 约束有效、预警及时

**记住**: 测试通过只是第一步，持续监控和优化同样重要！

祝你投资顺利！🚀📈