# TTL 智能缓存 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 ttl_cache 并通过两个 AC | agent-dev-b |  | AC-1, AC-2 | python -m unittest tests.test_ttl_cache -v | 完成 | AI报告：新增 agent_tools/ttl_cache.py（TTLCache、TTLCacheError）与 tests/test_ttl_cache.py；实现 get/set/get_or_compute/purge_expired/items/clear 与 len 语义；TTL 内复用、过期重算，producer 异常不写入缓存，注入时钟可验证过期，len 只统计未过期键，maxsize 按最近使用淘汰。python -m unittest tests.test_ttl_cache -v 通过 19 项；业务代码未提交，等待用户自行检查与提交。 |
