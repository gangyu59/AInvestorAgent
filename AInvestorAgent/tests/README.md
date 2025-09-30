# 🧪 AInvestorAgent 测试系统

> **专业、全面、可视化的测试框架** - 确保系统在真实投资前达到生产就绪状态

---

## 🎯 测试目标

在进行真实投资前，验证系统的：
- ✅ **功能完整性** - 所有核心功能正常工作
- ✅ **数据质量** - 数据准确、及时、完整
- ✅ **策略有效性** - 回测和实盘模拟表现良好
- ✅ **系统稳定性** - 性能达标、容错健壮
- ✅ **风险控制** - 约束有效、预警及时

---

## 🚀 快速开始（3步）

### 1️⃣ 确保后端运行

```bash
python run.py
# 访问 http://localhost:8000/health 应返回 {"status":"ok"}
```

### 2️⃣ 运行完整测试

```bash
chmod +x tests/run_visual_tests.sh
./tests/run_visual_tests.sh --full
```

### 3️⃣ 查看报告

测试完成后，查看：
- 📊 **HTML报告**: `tests/reports/detailed_report.html`
- 📝 **Markdown报告**: `tests/reports/TEST_REPORT.md`
- 💾 **JSON数据**: `tests/reports/test_results.json`

---

## 📦 测试系统组件

```
tests/
│
├── 🎮 可视化控制台
│   ├── visual_dashboard.html      # Web控制台界面
│   └── run_visual_tests.sh        # 一键启动脚本
│
├── 🤖 自动化测试引擎
│   ├── test_runner.py              # 核心测试执行器
│   └── test_cases_detailed.py      # 283个详细测试用例
│
├── 📈 实盘模拟器
│   └── paper_trading_simulator.py  # 30天虚拟交易模拟
│
├── 📊 测试报告
│   └── reports/
│       ├── TEST_REPORT.md          # 主报告
│       ├── detailed_report.html    # 详细HTML
│       ├── test_results.json       # 结构化数据
│       └── paper_trading_*.{md,png,csv}
│
└── 📖 文档
    ├── README.md                   # 本文件
    └── TESTING_GUIDE.md            # 完整使用指南
```

---

## 🎯 8大测试套件概览

| 优先级 | 套件名称 | 测试项 | 时长 | 说明 |
|--------|----------|--------|------|------|
| **P0** | 功能完整性 | 48 | 3分钟 | 数据获取、因子计算、评分、组合、回测 |
| **P0** | 数据质量 | 30 | 2分钟 | 完整性、准确性、一致性 |
| **P0** | 回测有效性 | 35 | 5分钟 | IC测试、Alpha生成、极端市场 |
| **P1** | 智能体能力 | 40 | 4分钟 | 单智能体、协同、冲突解决 |
| **P1** | API性能 | 25 | 2分钟 | 响应时间、并发、错误处理 |
| **P1** | 可视化 | 45 | 3分钟 | 首页、个股、组合、模拟器页面 |
| **P2** | 边界容错 | 28 | 2分钟 | 数据缺失、异常输入、网络故障 |
| **P2** | 生产就绪 | 32 | 4分钟 | 性能基准、可靠性、可观测性 |

**总计**: 283个测试项 | 预计15分钟 | 涵盖全部关键路径

---

## 💻 使用方法

### 方式1: 一键测试（推荐）

```bash
# 完整测试 + 可视化控制台
./tests/run_visual_tests.sh --full

# 快速测试（仅P0，约5分钟）
./tests/run_visual_tests.sh --quick

# 仅启动可视化控制台
./tests/run_visual_tests.sh --visual
```

### 方式2: 单独运行

```bash
# Python自动化测试
python tests/test_runner.py

# Pytest详细测试
pytest tests/test_cases_detailed.py -v --html=tests/reports/detailed_report.html

# 30天实盘模拟
python tests/paper_trading_simulator.py --capital 100000 --weeks 4
```

### 方式3: 运行特定测试

```bash
# 仅测试功能完整性
pytest tests/test_cases_detailed.py::TestFunctionalCompleteness -v

# 仅测试数据质量
pytest tests/test_cases_detailed.py::TestDataQuality -v

# 仅测试某个具体功能
pytest tests/test_cases_detailed.py::TestFunctionalCompleteness::test_01_data_ingestion_prices -v
```

---

## 📊 测试结果解读

### 通过率标准

| 通过率 | 状态 | 说明 | 建议 |
|--------|------|------|------|
| ≥ 95% | 🟢 **就绪** | 系统表现优秀 | ✅ 可以进行真实投资 |
| 80-95% | 🟡 **需优化** | 大部分功能正常 | ⚠️ 修复失败项后再投资 |
| < 80% | 🔴 **未就绪** | 存在严重问题 | ❌ 必须修复关键问题 |

### 关键指标

测试报告会显示：

```
📊 测试总结
============================================================
总测试项: 283
通过: 269
失败: 14
通过率: 95.1%

💼 投资就绪度评估:
   ✅ 系统就绪 - 可以进行投资
```

---

## 🔄 30天实盘模拟

### 为什么需要？

- 回测可能过拟合历史数据
- 验证系统在真实环境下的表现
- 发现实时决策中的潜在问题
- 建立对系统的信心

### 运行方式

```bash
# 默认：10万资金，4周
python tests/paper_trading_simulator.py

# 自定义
python tests/paper_trading_simulator.py --capital 50000 --weeks 8
```

### 模拟流程

```
第1周 → 生成组合 → 虚拟买入 → 记录净值
  ↓
第2周 → 获取价格 → 重新决策 → 执行调仓
  ↓
第3周 → ...
  ↓
第4周 → 最终调仓 → 生成报告 → 评估就绪度
```

### 通过标准

✅ **可以小额实盘**:
- 30天收益 > 0
- 最大回撤 < 15%
- Sharpe > 0.5
- 无系统崩溃

⚠️ **需要优化**:
- 收益为负但可控
- Sharpe < 0.5
- 偶尔技术故障

❌ **不建议实盘**:
- 收益 < -5%
- 回撤 > 20%
- 频繁崩溃

---

## ✅ 投资前检查清单

### 阶段1: 基础测试（1-2天）
- [ ] 运行完整测试套件，通过率 ≥ 95%
- [ ] 所有P0测试100%通过
- [ ] 无阻断性问题

### 阶段2: 数据验证（1天）
- [ ] 手工验证10支股票数据准确性
- [ ] 对比外部源确认一致性
- [ ] 检查新闻情绪合理性

### 阶段3: 回测验证（1-2天）
- [ ] 多窗口回测（6M, 1Y, 2Y）
- [ ] Alpha > 2%, Sharpe > 0.5
- [ ] 极端市场表现测试

### 阶段4: 实盘模拟（30天）
- [ ] 完成30天实盘模拟
- [ ] 每周检查无技术故障
- [ ] 验证通过标准

### 阶段5: 人工审核（1-2天）
- [ ] 至少2位专业人士审核
- [ ] 验证持仓合理性
- [ ] 确认无已知重大风险

### 阶段6: 合规与风险（1天）
- [ ] 添加免责声明
- [ ] 制定应急预案
- [ ] 设定投资金额 ≤ 总资金10%
- [ ] 设定止损线（如-15%）

### 阶段7: 最终确认
- [ ] 我已完成上述所有检查
- [ ] 我理解系统局限性和风险
- [ ] 我已设定合理预期
- [ ] 我确认系统可用于真实投资

---

## 🛠️ 常见问题

<details>
<summary><b>Q1: 测试失败了怎么办？</b></summary>

1. 查看 `tests/reports/TEST_REPORT.md` 了解失败详情
2. 检查失败的测试属于哪个优先级（P0最关键）
3. 根据错误信息修复问题
4. 重新运行测试验证修复

P0测试失败 = 阻断性问题，必须修复  
P1测试失败 = 重要问题，建议修复  
P2测试失败 = 次要问题，可后续优化
</details>

<details>
<summary><b>Q2: 为什么有些测试很慢？</b></summary>

- 回测测试需要处理大量历史数据（约5分钟）
- 实盘模拟需要实际运行30天
- 可使用 `--quick` 模式仅运行快速测试
</details>

<details>
<summary><b>Q3: 能否跳过某些测试？</b></summary>

**不建议跳过P0测试**，这些是关键路径。

如果需要：
```bash
# 跳过慢速测试
pytest tests/test_cases_detailed.py -v -m "not slow"

# 仅运行特定套件
pytest tests/test_cases_detailed.py::TestFunctionalCompleteness -v
```
</details>

<details>
<summary><b>Q4: 如何持续监控投资后的表现？</b></summary>

建议：
- **每天**: 检查系统健康状态
- **每周**: 生成周报，对比实际 vs 预测
- **每月**: 运行完整测试，评估因子有效性
- **每季度**: 重新运行实盘模拟，验证策略仍有效
</details>

---

## 📚 更多资源

- 📖 **完整使用指南**: [TESTING_GUIDE.md](TESTING_GUIDE.md)
- 🏗️ **系统架构**: `docs/ARCHITECTURE.md`
- 📋 **API文档**: `docs/API_REFERENCE.md`
- 💡 **功能说明**: `docs/FUNCTIONAL_SPEC.md`

---

## 🎓 测试最佳实践

1. **定期测试**: 每次代码改动后运行快速测试
2. **版本管理**: 保存每次测试报告，对比趋势
3. **持续优化**: 根据失败项持续改进系统
4. **审慎投资**: 从小额开始，逐步增加
5. **风险控制**: 永远设置止损，定期复盘

---

## 📞 获取帮助

- **查看日志**: `tests/logs/` 目录
- **详细文档**: `tests/TESTING_GUIDE.md`
- **报告错误**: 在GitHub上提Issue

---

## 🎯 总结

这套测试系统通过 **283个自动化测试** + **30天实盘模拟**，全方位验证你的AInvestorAgent：

✅ 功能完整 | ✅ 数据可靠 | ✅ 策略有效  
✅ 系统稳定 | ✅ 风险可控

**记住**: 测试通过是第一步，审慎投资、持续监控同样重要！

祝你投资成功！🚀📈💰

---

*最后更新: 2025-09-29 | 版本: v1.0*