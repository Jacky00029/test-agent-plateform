# 对话上下文窗口 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 conversation_window 并通过两个 AC | agent-dev-a |  | AC-1, AC-2 | python -m unittest tests.test_conversation_window -v | 完成 | AI报告：新增 agent_tools/conversation_window.py：estimate_tokens 按 ceil(len/4) 估算；fit_messages 始终保留开头连续 system 消息（即使超出预算），剩余预算从最新消息向前保留连续后缀，返回 window/dropped/used_tokens，消息经 deepcopy 返回且不修改输入。新增 tests/test_conversation_window.py，14 个用例覆盖正常、边界和失败场景。业务代码未提交，等待用户自行检查与提交。 |
