# AInvestorAgent 快速测试手册
## 给急着上线的你 - 3小时版

> **适用场景**: 你已经测试过基本功能，想尽快开始小额投资  
> **时间**: 约3小时  
> **风险**: 建议第一批投资 ≤ $10,000

---

## 🚀 第一步: 数据健康检查（30分钟）

### 1.1 运行自动验证脚本
```bash
# 创建并运行数据验证脚本
python scripts/validate_data.py
```

**必须看到的结果**:
```
========================================
AInvestorAgent 数据验证报告
========================================

【1】价格数据验证
   ✓ 价格数据量充足
   ✓ 价格数据新鲜 (最近更新: 0天前)
   ✓ AAPL: 252 个数据点
   ✓ MSFT: 252 个数据点
   ...
   ✓ SPY: 252 个数据点

【2】新闻数据验证
   ✓ 新闻数据量充足
   ✓ 新闻评分完整
   ...

========================================
验证总结
========================================
✓ 所有验证通过！数据质量良好。
✓ 系统已准备好进行测试投资。
```

**❌ 如果看到警告或失败**:
- 红色 ✗ = 必须修复
- 黄色 ⚠ = 记录但可继续

### 1.2 手工抽查3支股票
打开 Yahoo Finance，对比你的系统：

**AAPL**:
```bash
curl "http://localhost:8000/api/prices/AAPL?range=1M" | python -m json.tool
```
- [ ] 最新收盘价与Yahoo Finance误差 < 2%
- [ ] 日期是最近2天内

**MSFT**: 重复以上
- [ ] 误差 < 2%

**SPY**: 重复以上（这个是基准，必须准确）
- [ ] 误差 < 1%

---

## 🧮 第二步: 评分系统快检（15分钟）

### 2.1 测试单股分析
```bash
curl -X POST "http://localhost:8000/api/analyze/AAPL" | python -m json.tool
```

**检查**:
- [ ] 返回200状态码
- [ ] `score` 在 0-100 之间
- [ ] 四个因子都有值

### 2.2 批量评分
```bash
curl -X POST "http://localhost:8000/api/score/batch" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL","MSFT","GOOGL","NVDA","TSLA"]}' \
  | python -m json.tool
```

**检查**:
- [ ] 返回5个结果
- [ ] 响应时间 < 10秒
- [ ] 分数有差异（不是都一样）

---

## 📊 第三步: 组合生成测试（30分钟）

### 3.1 生成测试组合
```bash
curl -X POST "http://localhost:8000/api/portfolio/propose" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL","MSFT","GOOGL","TSLA","NVDA","AMZN","META","NFLX"]}' \
  | python -m json.tool > test_portfolio.json
```

### 3.2 手工检查结果
打开 `test_portfolio.json`，检查：

**权重检查**:
```python
# 在Python中快速检查
import json
with open('test_portfolio.json') as f:
    data = json.load(f)
    holdings = data['holdings']
    total = sum(h['weight'] for h in holdings)
    max_single = max(h['weight'] for h in holdings)
    print(f"持仓数: {len(holdings)}")
    print(f"权重总和: {total:.2f}%")
    print(f"最大单票: {max_single:.2f}%")
```

**必须满足**:
- [ ] 持仓数 5-15 支
- [ ] 权重总和 99-101%
- [ ] 单票 ≤ 30%

### 3.3 可复现性测试
```bash
# 运行两次完全相同的请求
curl -X POST "http://localhost:8000/api/portfolio/propose" \
  -d '{"symbols": ["AAPL","MSFT","GOOGL"]}' > run1.json

curl -X POST "http://localhost:8000/api/portfolio/propose" \
  -d '{"symbols": ["AAPL","MSFT","GOOGL"]}' > run2.json

# 对比
diff run1.json run2.json
```

- [ ] 两次结果完全相同（no output from diff）

---

## 🔄 第四步: 回测验证（45分钟）

### 4.1 运行1年回测
```bash
curl -X POST "http://localhost:8000/api/backtest/run" \
  -H "Content-Type: application/json" \
  -d '{
    "holdings": [
      {"symbol": "AAPL", "weight": 20},
      {"symbol": "MSFT", "weight": 20},
      {"symbol": "GOOGL", "weight": 20},
      {"symbol": "NVDA", "weight": 20},
      {"symbol": "AMZN", "weight": 20}
    ],
    "window": "1Y",
    "rebalance": "weekly"
  }' | python -m json.tool > backtest_result.json
```

### 4.2 分析回测结果
```python
import json
with open('backtest_result.json') as f:
    data = json.load(f)
    metrics = data['metrics']
    final_nav = data['nav'][-1]
    
    print(f"最终净值: {final_nav:.4f}")
    print(f"年化收益: {metrics['annualized_return']*100:.2f}%")
    print(f"Sharpe: {metrics['sharpe']:.3f}")
    print(f"最大回撤: {metrics['max_dd']*100:.2f}%")
    print(f"胜率: {metrics['win_rate']*100:.2f}%")
```

**合理性检查**:
- [ ] 最终净值 > 0.5 且 < 3.0
- [ ] 年化收益 在 -30% 到 +80% 之间
- [ ] Sharpe 在 -1 到 +3 之间
- [ ] 最大回撤 在 -5% 到 -40% 之间
- [ ] 胜率 在 35% 到 70% 之间

**❌ 如果指标异常**:
- Sharpe > 3: 可能过拟合，降低期望
- 回撤 > -40%: 风险太高，考虑降低权重
- 最终净值 < 0.8: 策略可能亏损，谨慎投资

---

## 🤖 第五步: 完整决策链测试（30分钟）

### 5.1 运行完整决策
```bash
curl -X POST "http://localhost:8000/api/orchestrator/decide" \
  -H "Content-Type: application/json" \
  -d '{"topk": 10, "mock": false}' \
  | python -m json.tool > full_decision.json
```

**检查**:
- [ ] 响应时间 < 2分钟
- [ ] 包含 `trace_id`
- [ ] 包含 `holdings`
- [ ] 持仓 5-15 支

### 5.2 验证决策质量
打开 `full_decision.json`：

**人工审核清单**:
1. 选出的股票都认识吗？
   - [ ] 是知名公司，不是垃圾股
2. 入选理由合理吗？
   - [ ] 查看每支股票的 `reasons` 字段
   - [ ] 理由应该类似 "高质量因子（ROE=25%）+ 强劲动量（3M+15%）"
3. 权重分配合理吗？
   - [ ] 没有某支股票占比特别大
   - [ ] 没有全是科技股或全是某个行业

**❌ 如果觉得不合理**:
- 记下来，但不一定是bug
- 可以尝试调整策略权重再试

---

## 🖥️ 第六步: 前端快速验证（15分钟）

### 6.1 访问仪表盘
打开 `http://localhost:3000`

**快速检查**:
- [ ] 能看到数据（不是全空白）
- [ ] 日期是最近的
- [ ] 没有JavaScript错误（F12看控制台）

### 6.2 测试组合页面
点击 "Decide Now" 按钮：
- [ ] 能生成组合
- [ ] 能看到饼图
- [ ] 能看到持仓表
- [ ] 能导出CSV

### 6.3 测试模拟器页面
点击 "Run Backtest" 按钮：
- [ ] 能看到净值曲线
- [ ] 能看到回撤图
- [ ] 能看到指标（年化、Sharpe等）

---

## 📝 第七步: 7天实盘模拟（必做！）

> **重要**: 不要跳过这一步！至少模拟7天再投入真金。

### 7.1 创建模拟记录表
创建一个Excel或Google Sheets文件：

| 日期 | 操作 | 股票 | 虚拟价格 | 权重 | 虚拟金额 | 当前价格 | 当前金额 | 盈亏 |
|------|------|------|----------|------|----------|----------|----------|------|
| 2025-10-20 | 买入 | AAPL | $175.00 | 25% | $2,500 | - | - | - |
| 2025-10-20 | 买入 | MSFT | $380.00 | 25% | $2,500 | - | - | - |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

### 7.2 第1天（今天）
**上午操作**:
1. 更新数据：
```bash
python scripts/fetch_prices.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,SPY --range 1Y
python scripts/fetch_news.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,SPY --days 14 --noproxy
python scripts/rebuild_factors.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,SPY
python scripts/recompute_scores.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,SPY
```

2. 生成组合：
```bash
curl -X POST "http://localhost:8000/api/orchestrator/decide" \
  -d '{"topk": 10}' > simulation_day1.json
```

3. 记录虚拟持仓到Excel
   - 假设总资金 $10,000
   - 按系统建议的权重分配
   - 记录每支股票的虚拟买入价（今日开盘价或当前价）

**下午收盘后**:
- 记录每支股票的收盘价
- 计算账户总值
- 计算当日盈亏

### 7.3 第2-6天
每天收盘后：
- 更新价格：`python scripts/fetch_prices.py ...`
- 更新Excel中的当前价格和盈亏
- 记录系统是否有异常

### 7.4 第7天（周末）
**完整周度操作**:
1. 重新生成组合建议：
```bash
curl -X POST "http://localhost:8000/api/orchestrator/decide" \
  -d '{"topk": 10}' > simulation_day7.json
```

2. 对比 day1 和 day7 的建议
   - 如果有调仓，记录虚拟调仓
   - 计算虚拟换手率

3. 计算本周绩效：
   - 周收益率 = (期末总值 - 期初总值) / 期初总值
   - 最大回撤 = 本周最低点相对期初的跌幅
   - 对比SPY: 你的收益 vs SPY本周收益

### 7.5 模拟通过标准
- [ ] 7天内系统无崩溃
- [ ] 7天收益率 > -5%（可接受小亏）
- [ ] 最大回撤 < 10%
- [ ] 无明显不合理建议

**✅ 如果通过，可以考虑投入$5,000-$10,000真金**  
**❌ 如果不通过，延长模拟至14天或30天**

---

## 💰 第八步: 真实投资准备（15分钟）

### 8.1 最后确认
- [ ] 我已完成上述所有测试
- [ ] 实盘模拟表现可接受
- [ ] 我理解可能会亏损
- [ ] 我设置了止损线（-15%）

### 8.2 资金计划
**第一批投资**:
- 金额: $_________ （建议$5,000-$10,000）
- 占总资金比例: _____% （建议≤10%）
- 如果亏损达到-15%（即$_______），立即止损

**后续计划**:
- 如果第一批1个月表现良好（盈利或小亏<5%）
  - 第二批: +$10,000
  - 第三批: +$30,000
  - 最终上限: $50,000
- 如果触发止损
  - 暂停投资
  - 全面检查系统
  - 重新模拟至少2周

### 8.3 监控计划
**每日**:
- [ ] 早上检查 `curl http://localhost:8000/health`
- [ ] 晚上记录持仓盈亏

**每周**:
- [ ] 周一早上更新数据（价格+新闻）
- [ ] 周一上午生成新组合建议
- [ ] 对比系统建议 vs 自己判断
- [ ] 记录周度收益与回撤
- [ ] 对比SPY表现

**每月**:
- [ ] 运行完整测试套件（`python scripts/validate_data.py`）
- [ ] 回顾决策质量
- [ ] 生成月度报告
- [ ] 决定是否增加/减少投资

### 8.4 应急预案
**触发条件**（满足任一条立即执行）:
1. 单周亏损 > 10%
2. 累计回撤达到 -15%（止损线）
3. 系统连续2天崩溃
4. 出现明显不合理建议

**应急操作**:
1. 🛑 **暂停自动决策**
2. 📊 **人工审核所有持仓**
3. 💼 **考虑减仓50%或清仓**
4. 🔍 **排查系统问题**
5. ⏸️ **暂停至少1周，重新模拟后再启动**

---

## 📋 快速检查清单（打印出来）

### 数据质量 ✓
- [ ] 价格数据新鲜（≤2天）
- [ ] 主要股票数据完整（AAPL/MSFT/SPY等）
- [ ] 新闻数据充足

### 功能测试 ✓
- [ ] 评分系统正常
- [ ] 组合生成正常
- [ ] 回测功能正常
- [ ] 完整决策链正常

### 前端验证 ✓
- [ ] 仪表盘可用
- [ ] 组合页面可用
- [ ] 模拟器页面可用

### 实盘模拟 ✓
- [ ] 至少7天无重大问题
- [ ] 收益率可接受
- [ ] 回撤可控

### 最终准备 ✓
- [ ] 设置止损线（-15%）
- [ ] 制定监控计划
- [ ] 制定应急预案
- [ ] 心理准备完成

---

## 🎯 立即开始的简化流程

**如果你时间紧迫，至少做这5件事**:

```bash
# 1. 数据验证（5分钟）
python scripts/validate_data.py

# 2. 组合测试（5分钟）
curl -X POST "http://localhost:8000/api/portfolio/propose" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL","MSFT","GOOGL","NVDA","TSLA"]}' \
  | python -m json.tool

# 3. 回测验证（10分钟）
curl -X POST "http://localhost:8000/api/backtest/run" \
  -H "Content-Type: application/json" \
  -d '{"holdings": [{"symbol":"AAPL","weight":33},{"symbol":"MSFT","weight":33},{"symbol":"GOOGL","weight":34}], "window": "1Y"}' \
  | python -m json.tool

# 4. 完整决策（10分钟）
curl -X POST "http://localhost:8000/api/orchestrator/decide" \
  -d '{"topk": 10}' | python -m json.tool

# 5. 前端检查（5分钟）
# 访问 http://localhost:3000，点击所有主要功能
```

**如果以上5个都通过，可以开始7天实盘模拟**。

---

## 🚨 风险提示

### 你必须知道的事实：

1. **这是实验性系统**
   - 你是第一个真实投资用户
   - 可能存在未发现的bug
   - 回测表现不代表未来收益

2. **市场风险**
   - 股市有风险，可能亏损
   - 黑天鹅事件无法预测
   - 系统不能保证盈利

3. **技术风险**
   - 系统可能崩溃
   - 数据可能延迟或错误
   - API密钥可能失效

4. **你的责任**
   - 系统只是辅助工具
   - 你必须自己做最终决策
   - 不要盲目跟随系统建议

### 建议原则：

✅ **DO**:
- 从小额开始（≤$10,000）
- 设置明确止损线
- 定期监控
- 保持理性

❌ **DON'T**:
- 梭哈全部资金
- 借钱投资
- 不设止损
- 盲目信任系统

---

## 📞 需要帮助？

**如果遇到问题**:

1. **系统报错**:
   - 查看 `logs/` 目录的日志文件
   - 检查 `.env` 配置是否正确
   - 重启后端和前端

2. **数据问题**:
   - 重新拉取数据
   - 检查API密钥是否有效
   - 查看数据库文件大小

3. **结果异常**:
   - 检查是否是Mock数据
   - 对比外部数据源
   - 查看trace日志

4. **决策疑惑**:
   - 查看入选理由
   - 对比多次决策结果
   - 相信自己的判断优先于系统

---

## ✅ 最终清单

**在投入真金之前，请确认**:

- [x] 我已阅读完整检查清单
- [x] 我至少完成了7天实盘模拟
- [x] 我理解所有风险
- [x] 我设置了止损线（-15%）
- [x] 我有应急预案
- [x] 我不会投入超出承受范围的资金

**初始投资金额**: $__________  
**止损金额**: $__________（初始 × 0.85）  
**开始日期**: __________  

**签名**: ________________  

---

**祝投资顺利！记住：理性投资，风险自负。** 🚀