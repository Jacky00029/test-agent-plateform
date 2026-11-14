# 工具延迟统计：设计

## 设计方案

在 `agent_tools/latency_tracker.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：LatencyTracker.summary 返回 count、error_count、error_rate、avg_ms、p50_ms、p95_ms 和 total_ms。
- AC-2：百分位使用 nearest-rank；measure 成功/异常都记录实际耗时，异常继续抛出且空工具无样本时显示 unknown。
- 在 `tests/test_latency_tracker.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_latency_tracker -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。