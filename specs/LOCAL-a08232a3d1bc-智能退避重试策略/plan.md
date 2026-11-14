# 智能退避重试策略：设计

## 设计方案

在 `agent_tools/retry_policy.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：RetryPolicy.delays 按 base_delay 指数增长并受 max_delay 限制；max_attempts 控制总调用次数。
- AC-2：run 对成功调用立即返回，对指定异常重试并保留最后一次异常；非指定异常不重试。
- 在 `tests/test_retry_policy.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_retry_policy -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。