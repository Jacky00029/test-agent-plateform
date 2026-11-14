# Prompt 预算裁剪 · 任务与依赖

> 工作台生成；状态唯一来源为requirement.json，请通过工作台修改。

| 任务 | 内容 | 负责人 | 依赖 | AC/范围 | 检查标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| T1 | 实现 prompt_budget 并通过两个 AC | agent-dev-a |  | AC-1, AC-2 | python -m unittest tests.test_prompt_budget -v | 完成 | AI报告：新增 agent_tools/prompt_budget.py：estimate_tokens 对空串返回 0、非空按 ceil(len(text)/4) 估算；pack_prompt 按输入顺序装入预算，超预算时跳过低优先级/超长段落并允许后续较短段落填入，高优先级段落可替换低优先级已选段落，返回 segments/used_tokens/dropped 且不修改输入。新增 tests/test_prompt_budget.py，15 个用例覆盖正常、边界和失败场景。业务代码未提交，等待用户自行检查与提交。 |
