# 对话上下文窗口：设计

## 设计方案

在 `agent_tools/conversation_window.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：fit_messages 始终优先保留开头的 system 消息，再从最新消息向前填满预算。
- AC-2：返回 window 与 dropped 数量；无法放入预算的可选旧消息被丢弃，输入消息不被修改。
- 在 `tests/test_conversation_window.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_conversation_window -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。