# 工具调用参数校验 · 需求规格

## 目标与业务规则

使用 JSON Schema 子集校验智能体工具参数，给调用方明确字段错误。

## 验收条件

| 编号 | 场景、操作与预期 |
|---|---|
| AC-1 | validate_call 对 required 缺失、类型错误和未声明字段分别抛出带字段名的 ToolCallError。 |
| AC-2 | 支持 string/integer/number/boolean/array/object 类型，合法输入返回原参数副本且不修改输入。 |