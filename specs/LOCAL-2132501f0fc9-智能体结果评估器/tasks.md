# 智能体结果评估器 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 evaluator 并通过两个 AC | agent-dev-b |  | AC-1, AC-2 | python -m unittest tests.test_evaluator -v | 完成 | AI报告：新增 agent_tools/evaluator.py（evaluate、EvaluationError）与 tests/test_evaluator.py；实现 exact、contains、regex、json_equals 四类检查，返回 total/passed/pass_rate/failures；JSON 字符串解析后按结构比较（键顺序无关、数组顺序敏感、布尔不混同数字），失败项带用例 ID、检查类型与实际原因。python -m unittest tests.test_evaluator -v 通过 29 项；业务代码未提交，等待用户自行检查与提交。 |
