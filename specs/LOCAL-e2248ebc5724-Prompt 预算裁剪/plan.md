# Prompt 预算裁剪：设计

## 设计方案

在 `agent_tools/prompt_budget.py` 中实现本需求，仅使用 Python 标准库。

- AC-1：estimate_tokens 对空串返回0，对非空文本按 ceil(len(text)/4) 估算；pack_prompt 在预算内按输入顺序保留段落。
- AC-2：超出预算时跳过低优先级段落但允许后续较短段落填入，返回 used_tokens 不超过预算且不修改输入。
- 在 `tests/test_prompt_budget.py` 中使用 `unittest` 覆盖正常、边界和失败场景。
- 测试命令：`python -m unittest tests.test_prompt_budget -v`。
- 不引入第三方依赖，不连接外部服务，不修改其他需求模块。