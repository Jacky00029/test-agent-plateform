# 智能退避重试策略 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 retry_policy 并通过两个 AC | agent-dev-a |  | AC-1, AC-2 | python -m unittest tests.test_retry_policy -v | 完成 | AI报告：新增 agent_tools/retry_policy.py：RetryPolicy.delays 生成 base_delay 起按 2 倍增长并以 max_delay 封顶的重试延迟序列（长度 max_attempts-1）；run 对成功调用立即返回，仅重试 retry_on 指定异常，重试耗尽后抛出最后一次异常，非指定异常立即传播；支持 jitter 比例抖动与可注入 sleep/rng，含参数校验。新增 tests/test_retry_policy.py，15 个用例覆盖正常、边界和失败场景。业务代码未提交，等待用户自行检查与提交。 |
