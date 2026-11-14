# 规则任务路由器 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 task_router 并通过两个 AC | agent-dev-a |  | AC-1, AC-2 | python -m unittest tests.test_task_router -v | 完成 | AI报告：新增 agent_tools/task_router.py：TaskRouter 支持注册名称、关键词列表和整数 priority；route 用 casefold 做忽略大小写的子串匹配，按命中数降序、priority 降序、注册顺序升序选择规则，无命中返回 general；rules 属性返回防御性副本，register 校验名称、关键词和优先级。新增 tests/test_task_router.py，17 个用例覆盖正常、边界和失败场景。业务代码未提交，等待用户自行检查与提交。 |
