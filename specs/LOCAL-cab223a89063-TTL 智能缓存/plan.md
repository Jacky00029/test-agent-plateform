# TTL 智能缓存：设计

## 设计方案

在 `agent_tools/ttl_cache.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：get_or_compute 在 TTL 内复用结果，过期后重新计算；purge_expired 清理过期键。
- AC-2：producer 异常不写入缓存；时钟推进可验证过期行为，len 只统计未过期键。
- 在 `tests/test_ttl_cache.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_ttl_cache -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。