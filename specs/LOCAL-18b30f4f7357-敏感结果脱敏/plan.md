# 敏感结果脱敏：设计

## 设计方案

在 `agent_tools/redactor.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：redact 对 password/token/api_key/authorization/secret 等键递归替换为 [REDACTED]，支持嵌套 dict/list。
- AC-2：redact_text 将 Bearer 后内容替换为 [REDACTED]；处理不修改输入且重复执行保持幂等。
- 在 `tests/test_redactor.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_redactor -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。