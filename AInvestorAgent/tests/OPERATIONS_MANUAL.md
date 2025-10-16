# AInvestorAgent 每日/每周操作手册

> **目的**: 规范化日常操作，确保系统稳定运行  
> **适用**: 真实投资开始后的持续运营

---

## 📅 每日操作清单（5-10分钟）

### ⏰ 时间: 每天早上市场开盘前（9:00 AM）

### 步骤1: 系统健康检查（1分钟）
```bash
# 检查后端
curl http://localhost:8000/health

# 预期结果
{"status":"ok"}
```

**✅ 正常**: 继续下一步  
**❌ 异常**: 
1. 重启后端: `python run.py`
2. 再次检查
3. 如仍失败，查看日志: `cat logs/app.log | tail -50`

### 步骤2: 数据新鲜度检查（1分钟）
```bash
curl "http://localhost:8000/api/prices/SPY?range=1W" | python -m json.tool | head -20
```

**检查最新日期**:
- ✅ 如果是昨天或更近：数据新鲜
- ⚠️ 如果是2-3天前：今天需要更新数据（见周度操作）
- ❌ 如果超过5天：立即更新数据

### 步骤3: 持仓快速核对（3分钟）
打开你的投资记录Excel/表格：

**对比清单**:
1. 系统建议的持仓 vs 实际持仓
   - [ ] 股票列表一致
   - [ ] 权重偏差 < 5%（正常市场波动）

2. 记录当前价格
   - [ ] 更新每支股票的当前价格
   - [ ] 计算当日盈亏

### 步骤4: 快速浏览新闻（5分钟）
访问前端 Monitor 页面：`http://localhost:3000/#/monitor`

**关注**:
- 持仓股票是否有重大新闻
- 情绪分数是否有异常波动
- 是否有黑天鹅事件

### 步骤5: 记录日志（1分钟）
在你的交易日记中记录：

```
日期: 2025-10-20
系统状态: ✓ 正常
数据新鲜: ✓ 最新
持仓状态: ✓ 正常
当日盈亏: +$XX / -$XX
累计收益率: XX%
最大回撤: XX%
备注: [如果有异常情况记录在这里]
```

---

## 📊 每周操作清单（30-45分钟）

### ⏰ 时间: 每周一早上（或周末）

### 步骤1: 完整数据更新（10分钟）

#### 1.1 更新价格数据
```bash
# 更新主要股票池
python scripts/fetch_prices.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,COST,SPY --range 1Y

# 检查是否成功
echo "最新价格日期:"
python -c "
from backend.storage.db import SessionLocal
from backend.storage.models import PriceDaily
from sqlalchemy import func

db = SessionLocal()
latest = db.query(func.max(PriceDaily.date)).scalar()
print(f'最新: {latest}')
db.close()
"
```

**预期**: 最新日期应该是上个交易日

#### 1.2 更新新闻数据
```bash
# 拉取最近14天新闻
python scripts/fetch_news.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,COST,SPY --days 14 --noproxy --pages 1 --timeout 35

# 检查是否成功
python -c "
from backend.storage.db import SessionLocal
from backend.storage.models import NewsRaw
from sqlalchemy import func
from datetime import datetime, timedelta

db = SessionLocal()
one_week_ago = datetime.now() - timedelta(days=7)
count = db.query(NewsRaw).filter(NewsRaw.published_at >= one_week_ago).count()
print(f'最近7天新闻: {count} 条')
db.close()
"
```

**预期**: 至少50条新闻

#### 1.3 重算因子和评分
```bash
# 重算所有股票的因子
python scripts/rebuild_factors.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,COST,SPY

# 重算评分
python scripts/recompute_scores.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,COST,SPY
```

**预期**: 无报错

### 步骤2: 生成新组合建议（5分钟）
```bash
# 生成本周建议
curl -X POST "http://localhost:8000/api/orchestrator/decide" \
  -H "Content-Type: application/json" \
  -d '{"topk": 10, "mock": false}' \
  | python -m json.tool > weekly_decision_$(date +%Y%m%d).json

# 备份到专门目录
mkdir -p decisions/
cp weekly_decision_*.json decisions/
```

### 步骤3: 对比与决策（10分钟）

#### 3.1 对比上周 vs 本周
```python
# 简单对比脚本
import json
from glob import glob

files = sorted(glob('decisions/weekly_decision_*.json'))
if len(files) >= 2:
    with open(files[-2]) as f:
        last_week = json.load(f)
    with open(files[-1]) as f:
        this_week = json.load(f)
    
    last_symbols = {h['symbol'] for h in last_week['holdings']}
    this_symbols = {h['symbol'] for h in this_week['holdings']}
    
    print("新增:", this_symbols - last_symbols)
    print("移除:", last_symbols - this_symbols)
    print("保留:", last_symbols & this_symbols)
```

#### 3.2 人工判断
打开 `weekly_decision_YYYYMMDD.json`，审阅：

**问题清单**:
1. 新增的股票为什么入选？
   - [ ] 查看 `reasons` 字段
   - [ ] 是否合理？

2. 移除的股票为什么出局？
   - [ ] 对比上周和本周的评分
   - [ ] 是否有重大利空？

3. 权重变化是否合理？
   - [ ] 某只股票权重突然从10%→30%？
   - [ ] 是否符合市场情况？

#### 3.3 做出决策
**选项A: 完全跟随系统**
- 适用: 系统建议合理，无异常
- 操作: 按建议调仓

**选项B: 部分跟随**
- 适用: 大部分合理，个别股票存疑
- 操作: 调整可疑部分的权重

**选项C: 暂不调仓**
- 适用: 系统建议异常，或市场剧烈波动
- 操作: 维持当前持仓，下周再看

### 步骤4: 执行调仓（如需要）（10分钟）

**⚠️ 重要提醒**:
- 不要在市场开盘后立即交易（滑点大）
- 优先使用限价单
- 单次调仓不超过总仓位的30%

**调仓步骤**:
1. 计算需要买入/卖出的数量
2. 下限价单
3. 等待成交
4. 记录成交价格和手续费
5. 更新Excel记录

### 步骤5: 周度绩效分析（10分钟）

#### 5.1 计算周度指标
```python
# 在你的Excel或脚本中计算
本周收益率 = (期末总值 - 期初总值) / 期初总值
累计收益率 = (当前总值 - 初始投资) / 初始投资
最大回撤 = 历史最高点到当前的最大跌幅
```

#### 5.2 与基准对比
```python
# 查询SPY本周涨跌幅
import yfinance as yf
from datetime import datetime, timedelta

spy = yf.Ticker("SPY")
one_week_ago = datetime.now() - timedelta(days=7)
hist = spy.history(start=one_week_ago)

spy_return = (hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0]
print(f"SPY本周收益: {spy_return*100:.2f}%")

# 对比你的组合
your_return = ...  # 从Excel中获取
alpha = your_return - spy_return
print(f"超额收益(Alpha): {alpha*100:.2f}%")
```

#### 5.3 记录周报
```markdown
# 周报 - 第X周 (YYYY-MM-DD)

## 绩效表现
- 本周收益: XX%
- 累计收益: XX%
- 最大回撤: XX%
- vs SPY: Alpha = XX%

## 持仓变化
- 新增: [股票列表]
- 移除: [股票列表]
- 调整: [权重变化]

## 系统状态
- 数据更新: ✓
- 系统稳定: ✓
- 异常情况: [如果有]

## 下周计划
- [是否需要调整策略]
- [是否需要增减投资]
```

---

## 🚨 紧急情况处理流程

### 情况1: 系统崩溃
**现象**: `/health` 返回错误或无响应

**处理**:
1. 重启后端: `Ctrl+C` 然后 `python run.py`
2. 检查日志: `cat logs/app.log | tail -100`
3. 如果反复崩溃:
   - 不要调仓
   - 查看是否有Python错误
   - 临时切换到手工决策

### 情况2: 数据异常
**现象**: 价格明显错误，如AAPL显示$10

**处理**:
1. 验证外部数据源（Yahoo Finance）
2. 如果是API问题:
   ```bash
   # 删除异常数据
   python -c "
   from backend.storage.db import SessionLocal
   from backend.storage.models import PriceDaily
   from datetime import datetime
   
   db = SessionLocal()
   # 删除今天的异常数据
   db.query(PriceDaily).filter(
       PriceDaily.date == datetime.now().date()
   ).delete()
   db.commit()
   db.close()
   "
   
   # 重新拉取
   python scripts/fetch_prices.py --symbols [stock_list] --range 1M
   ```
3. 重新计算因子和评分

### 情况3: 单周暴跌 > 10%
**处理流程**:
1. 🛑 **立即停止自动决策**
2. 📊 **人工审查**:
   - 是系统问题还是市场整体下跌？
   - 对比SPY：如果SPY也大跌，可能是市场问题
3. 💼 **决策**:
   - 如果是市场: 考虑减仓50%避险
   - 如果是系统: 立即清仓，检查bug
4. 📝 **记录事件**:
   - 详细记录发生了什么
   - 你做了什么决策
   - 后续改进措施

### 情况4: 触发止损线（-15%）
**自动执行**:
1. 🛑 **立即停止系统**
2. 💰 **清仓或大幅减仓**（至少减仓70%）
3. 🔍 **全面检查**:
   - 是什么导致的亏损？
   - 回测是否过拟合？
   - 因子是否失效？
4. 📊 **重新评估**:
   - 延长实盘模拟至30天
   - 调整策略参数
   - 降低风险偏好
5. ⏸️ **暂停至少1个月**

---

## 📈 月度操作清单（2小时）

### ⏰ 时间: 每月最后一个周末

### 任务1: 完整系统测试（30分钟）
```bash
# 运行完整验证
python scripts/validate_data.py

# 运行性能测试
python tests/performance/test_latency_final.py

# 检查数据质量
# [运行其他测试脚本]
```

### 任务2: 因子有效性分析（30分钟）
评估过去1个月各因子的表现：

**问题**:
1. 哪个因子表现最好？（价值/质量/动量/情绪）
2. 哪个因子失效了？
3. 是否需要调整权重？

**可选操作**:
- 如果动量因子失效，降低权重: 0.35 → 0.25
- 如果情绪因子表现好，提高权重: 0.20 → 0.30

### 任务3: 生成月报（30分钟）
```markdown
# 月度报告 - YYYY年MM月

## 绩效总结
- 月度收益: XX%
- 累计收益: XX%
- 最大回撤: XX%
- Sharpe比率: XX
- vs SPY: Alpha = XX%

## 交易统计
- 调仓次数: X次
- 换手率: XX%
- 平均持仓期: X天
- 手续费: $XX

## 持仓分析
- 表现最好: [股票, +XX%]
- 表现最差: [股票, -XX%]
- 当前持仓: [列表]

## 系统健康
- 数据完整度: XX%
- 系统可用性: XX%
- 异常事件: X次

## 下月计划
- [是否调整策略]
- [是否增加投资]
- [系统改进计划]
```

### 任务4: 决策复盘（30分钟）
回顾本月的所有决策：

**问题**:
1. 哪些决策是对的？为什么？
2. 哪些决策是错的？为什么？
3. 有哪些可以改进的？

**记录教训**:
```
✓ 成功案例:
- [日期]: 买入XX，理由XX，结果XX

✗ 失败案例:
- [日期]: 卖出XX，理由XX，结果XX（应该继续持有）

💡 教训:
- [总结]
```

---

## 📚 附录: 常用命令速查

### 数据更新
```bash
# 快速更新（10只主要股票）
python scripts/fetch_prices.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY --range 3M
python scripts/fetch_news.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY --days 14 --noproxy
python scripts/rebuild_factors.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY
python scripts/recompute_scores.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY
```

### 快速查询
```bash
# 检查最新数据日期
curl "http://localhost:8000/api/prices/SPY?range=1W" | python -m json.tool | head -20

# 查看某股票评分
curl -X POST "http://localhost:8000/api/analyze/AAPL" | python -m json.tool | grep -A 5 "score"

# 批量查询评分
curl -X POST "http://localhost:8000/api/score/batch" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["AAPL","MSFT","GOOGL"]}' | python -m json.tool

# 查看情绪摘要
curl "http://localhost:8000/api/sentiment/brief?symbols=AAPL,MSFT&days=7" | python -m json.tool
```

### 诊断命令
```bash
# 检查数据库状态
python -c "
from backend.storage.db import SessionLocal
from backend.storage.models import PriceDaily, NewsRaw, ScoreDaily
from sqlalchemy import func

db = SessionLocal()
print(f'价格记录: {db.query(func.count(PriceDaily.id)).scalar():,}')
print(f'新闻记录: {db.query(func.count(NewsRaw.id)).scalar():,}')
print(f'评分记录: {db.query(func.count(ScoreDaily.id)).scalar():,}')
print(f'最新价格: {db.query(func.max(PriceDaily.date)).scalar()}')
db.close()
"

# 查看系统日志
tail -50 logs/app.log

# 检查API健康
curl http://localhost:8000/health
```

---

## 💡 经验与技巧

### 数据更新最佳实践
1. **固定时间更新**: 每周一早上9:00
2. **避开高峰**: 不要在美股开盘时更新（可能被API限流）
3. **增量更新**: 使用 `--range 3M` 而不是 `--range 5Y`（更快）
4. **备份数据**: 定期备份数据库文件

### 决策参考原则
1. **系统为辅，人工为主**: 不要100%依赖系统
2. **异常必究**: 如果建议突然大变，必须搞清楚为什么
3. **保守为上**: 不确定时，选择更保守的操作
4. **记录理由**: 每次调仓都记录"为什么这样做"

### 风险控制技巧
1. **分批建仓**: 不要一次性买入所有
2. **留有现金**: 保持10-20%现金仓位
3. **设置预警**: 单票跌幅 > 8% 时人工介入
4. **定期对账**: 每周核对系统建议 vs 实际持仓

### 效率提升
1. **创建脚本快捷方式**:
```bash
# 创建 update_all.sh
cat > update_all.sh << 'EOF'
#!/bin/bash
echo "更新价格..."
python scripts/fetch_prices.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY --range 3M

echo "更新新闻..."
python scripts/fetch_news.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY --days 14 --noproxy

echo "重算因子..."
python scripts/rebuild_factors.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY

echo "重算评分..."
python scripts/recompute_scores.py --symbols AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META,NFLX,DIS,SPY

echo "完成！"
EOF

chmod +x update_all.sh

# 使用
./update_all.sh
```

2. **Excel模板**: 提前准备好持仓记录模板
3. **日历提醒**: 设置手机提醒每周一操作

---

## 📝 记录模板

### 每日记录模板
```
日期: ________
系统状态: □ 正常 □ 异常
数据新鲜: □ 是 □ 否
持仓核对: □ 一致 □ 偏差
今日盈亏: +/- $____
累计收益: ____%
最大回撤: ____%
备注: _______________
```

### 周度调仓记录模板
```
周次: 第__周 (____/__)
上周组合: [列表]
本周建议: [列表]
变化: 新增[__] 移除[__]
执行决策: □ 完全跟随 □ 部分跟随 □ 暂不调仓
调仓明细:
  - 卖出: [股票] [数量] @[价格]
  - 买入: [股票] [数量] @[价格]
手续费: $____
周度收益: ____%
vs SPY: Alpha = ____%
备注: _______________
```

### 月度复盘模板
```
月份: YYYY年MM月

【绩效】
月度收益: ____%
累计收益: ____%
最大回撤: ____%
Sharpe: ____
vs SPY: ____%

【交易】
调仓次数: __次
换手率: ____%
手续费: $____

【持仓】
最佳: [股票] +____%
最差: [股票] -____%

【系统】
可用性: ____%
异常: __次

【复盘】
成功决策:
- _______________
失败决策:
- _______________
教训:
- _______________

【下月】
□ 维持策略
□ 调整权重: ___
□ 增加投资: $___
□ 减少投资: $___
□ 其他: ___
```

---

## 🎯 成功指标（KPI）

### 短期（1-3个月）
- [ ] 累计收益 > -5%（不大亏）
- [ ] 最大回撤 < 15%（风险可控）
- [ ] 系统可用性 > 95%（稳定）
- [ ] 无重大事故（无止损触发）

### 中期（6-12个月）
- [ ] 累计收益 > 5%（开始盈利）
- [ ] Sharpe比率 > 0.5（风险收益比合理）
- [ ] 跑赢SPY（产生Alpha）
- [ ] 换手率 < 30%/月（成本可控）

### 长期（1年+）
- [ ] 年化收益 > 10%（超过长期市场平均）
- [ ] Sharpe比率 > 1.0（优秀）
- [ ] Alpha > 3%（显著跑赢基准）
- [ ] 回撤 < 20%（下跌保护）

---

## 🚀 进阶优化建议

### 3个月后可以考虑
1. **扩大股票池**: 从10支扩展到20-30支
2. **多策略组合**: 增加价值策略、成长策略
3. **行业轮动**: 根据宏观周期调整行业配置
4. **动态止盈**: 单票涨幅 > 30% 时部分获利

### 6个月后可以考虑
1. **增加资金**: 如果表现良好，逐步增至$50,000
2. **自动化**: 设置自动调仓（需要券商API）
3. **优化频率**: 从周频改为双周频（降低成本）
4. **因子挖掘**: 开发新因子（如估值波动率）

### 1年后可以考虑
1. **机器学习**: 用ML优化因子权重
2. **多市场**: 扩展到港股、A股
3. **衍生品**: 增加期权对冲策略
4. **分享经验**: 写博客记录你的投资旅程

---

## ⚠️ 常见错误与避免

### ❌ 错误1: 过度交易
**现象**: 每天都想调仓  
**后果**: 高手续费，追涨杀跌  
**避免**: 严格遵守周频，除非触发止损

### ❌ 错误2: 盲目信任
**现象**: 系统说什么就做什么  
**后果**: 可能踩坑，失去独立判断  
**避免**: 每次都问"为什么"，不合理就不做

### ❌ 错误3: 情绪化
**现象**: 大涨时加仓，大跌时清仓  
**后果**: 高买低卖，亏损扩大  
**避免**: 提前制定规则，机械执行

### ❌ 错误4: 忽视风控
**现象**: 单票持仓 > 30%，无止损  
**后果**: 暴雷时损失惨重  
**避免**: 严格遵守约束，止损线不能破

### ❌ 错误5: 数据问题
**现象**: 用过期数据或错误数据做决策  
**后果**: 决策基于错误信息  
**避免**: 每次决策前检查数据新鲜度

---

## 📞 技术支持清单

### 自查步骤
遇到问题时按此顺序检查：

1. **系统是否运行？**
   - `curl http://localhost:8000/health`
   
2. **数据是否最新？**
   - 检查最新价格日期
   
3. **日志有无错误？**
   - `cat logs/app.log | grep ERROR`
   
4. **是否API限流？**
   - 查看AlphaVantage限额
   
5. **是否网络问题？**
   - 测试 `curl https://www.alphavantage.co`

### 重启清单
如果需要重启系统：

```bash
# 1. 停止服务
Ctrl+C  # 停止后端
Ctrl+C  # 停止前端

# 2. 清理进程（如果卡住）
ps aux | grep python | grep run.py
kill -9 [PID]

# 3. 重启后端
python run.py

# 4. 重启前端（新终端）
cd frontend
npm run dev

# 5. 验证
curl http://localhost:8000/health
curl http://localhost:3000
```

### 数据修复
如果数据损坏：

```bash
# 备份现有数据库
cp db/AInvestorAgent.sqlite db/AInvestorAgent.sqlite.backup

# 重建数据（谨慎！会重新拉取）
python scripts/fetch_prices.py --symbols [股票列表] --range 1Y
python scripts/fetch_news.py --symbols [股票列表] --days 30 --noproxy
python scripts/rebuild_factors.py --symbols [股票列表]
python scripts/recompute_scores.py --symbols [股票列表]
```

---

## ✅ 最后的话

### 记住这些原则

1. **系统是工具，你是决策者**
   - 参考建议，但保留判断

2. **风险第一，收益第二**
   - 保本比赚钱更重要

3. **持续学习，逐步优化**
   - 每次决策都是学习机会

4. **保持记录，复盘总结**
   - 好记性不如烂笔头

5. **理性投资，控制情绪**
   - 赚了不骄，亏了不慌

### 祝你投资顺利！

**记住**: 这是一场马拉松，不是百米冲刺。稳健增长，长期坚持，终会收获。

---

**文档版本**: v1.0  
**最后更新**: 2025-10-15  
**适用人群**: AInvestorAgent实际用户  
**维护者**: [你的名字]