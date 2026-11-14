# 工具调用参数校验 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 call_validator 并通过两个 AC | agent-dev-a |  | AC-1, AC-2 | python -m unittest tests.test_call_validator -v | 完成 | AI报告：新增 agent_tools/call_validator.py：ToolCallError 携带 field 路径；validate_call 校验 JSON Schema 子集的 object/properties/required/additionalProperties，支持 string/integer/number/boolean/array/object 及数组 items 递归校验，合法参数返回深拷贝。新增 tests/test_call_validator.py，20 个用例覆盖正常、嵌套、边界和失败场景。业务代码未提交，等待用户自行检查与提交。 |
