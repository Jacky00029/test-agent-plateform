# 工具延迟统计 · 需求规格

## 目标与业务规则

记录智能体工具耗时和失败，输出可比较的 P50/P95 与错误率。

## 验收条件

| 编号 | 场景、操作与预期 |
|---|---|
| AC-1 | LatencyTracker.summary 返回 count、error_count、error_rate、avg_ms、p50_ms、p95_ms 和 total_ms。 |
| AC-2 | 百分位使用 nearest-rank；measure 成功/异常都记录实际耗时，异常继续抛出且空工具无样本时显示 unknown。 |