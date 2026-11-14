# 规则任务路由器：设计

## 设计方案

在 `agent_tools/task_router.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：规则按关键词命中数降序、priority 降序选择，匹配忽略大小写。
- AC-2：命中数和优先级都相同时保持注册顺序；没有命中时返回 general。
- 在 `tests/test_task_router.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_task_router -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。