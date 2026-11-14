# 敏感结果脱敏 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 redactor 并通过两个 AC | agent-dev-b |  | AC-1, AC-2 | python -m unittest tests.test_redactor -v | 完成 | AI报告：新增 agent_tools/redactor.py（redact、redact_text、is_sensitive_key、RedactorError）与 tests/test_redactor.py；敏感键忽略大小写和 _-. 分隔符递归替换为 [REDACTED]，支持 dict/list/tuple 且不修改输入；redact_text 将 Bearer 后凭据替换为 [REDACTED]，重复执行幂等；循环引用安全截断。python -m unittest tests.test_redactor -v 通过 20 项；业务代码未提交，等待用户自行检查与提交。 |
