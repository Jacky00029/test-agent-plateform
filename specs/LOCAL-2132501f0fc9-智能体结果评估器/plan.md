# 智能体结果评估器：设计

## 设计方案

在 `agent_tools/evaluator.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：evaluate 支持 exact、contains、regex 和 json_equals 检查，返回 total/passed/pass_rate/failures。
- AC-2：混合用例只统计真实通过项；JSON 按结构比较，失败项包含用例 ID 与实际原因。
- 在 `tests/test_evaluator.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_evaluator -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。