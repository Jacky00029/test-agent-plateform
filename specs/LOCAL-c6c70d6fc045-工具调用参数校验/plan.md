# 工具调用参数校验：设计

## 设计方案

在 `agent_tools/call_validator.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：validate_call 对 required 缺失、类型错误和未声明字段分别抛出带字段名的 ToolCallError。
- AC-2：支持 string/integer/number/boolean/array/object 类型，合法输入返回原参数副本且不修改输入。
- 在 `tests/test_call_validator.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_call_validator -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。