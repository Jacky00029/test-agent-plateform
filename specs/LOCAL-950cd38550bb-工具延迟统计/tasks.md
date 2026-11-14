# 工具延迟统计 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 latency_tracker 并通过两个 AC | agent-dev-b |  | AC-1, AC-2 | python -m unittest tests.test_latency_tracker -v | 完成 | AI报告：新增 agent_tools/latency_tracker.py（LatencyTracker、nearest_rank、LatencyTrackerError）与 tests/test_latency_tracker.py；实现 record/measure/summary/reset，summary 返回 count、error_count、error_rate、avg_ms、p50_ms、p95_ms、total_ms；百分位为 nearest-rank（ceil(p/100*n)）；measure 成功与异常均记录实际耗时且异常继续抛出；无样本统计量为 unknown。python -m unittest tests.test_latency_tracker -v 通过 21 项；业务代码未提交，等待用户自行检查与提交。 |
