# 令牌桶限流器 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 rate_limiter 并通过两个 AC | agent-dev-b |  | AC-1, AC-2 | python -m unittest tests.test_rate_limiter -v | 完成 | AI报告：新增 agent_tools/rate_limiter.py（TokenBucket、RateLimiterError）与 tests/test_rate_limiter.py；实现容量内突发、按 refill_per_second 惰性补充、try_acquire 不足不扣减、retry_after 计算等待秒数且不消耗令牌，注入时钟验证补充与上限。python -m unittest tests.test_rate_limiter -v 通过 19 项；业务代码未提交，等待用户自行检查与提交。 |
