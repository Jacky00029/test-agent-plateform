# 令牌桶限流器：设计

## 设计方案

在 `agent_tools/rate_limiter.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：try_acquire 在令牌不足时返回 False 且不扣减；成功时扣减且桶容量不超过 capacity。
- AC-2：retry_after 返回按 refill_per_second 计算的等待秒数；时钟推进后允许新调用。
- 在 `tests/test_rate_limiter.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_rate_limiter -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。