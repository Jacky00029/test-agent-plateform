# test-agent-plateform

一个从零开始的智能体工具合集，同时演示 Spec Manager 驱动的真实需求流转、两名开发者协作和研发效能统计。

## 技术约定

- Python 3.9+，仅使用标准库，业务运行无需外部服务。
- 业务代码位于 `agent_tools/`，测试位于 `tests/`。
- 全部检查：`python -m unittest discover -s tests -v`
- Spec 资料位于 `specs/`，由 Spec Manager 统一维护。

## 需求与分工

| 编号 | 工具 | 开发者 |
|---|---|---|
| 01 | Prompt 预算裁剪 | agent-dev-a |
| 02 | 工具调用参数校验 | agent-dev-a |
| 03 | 智能退避重试策略 | agent-dev-a |
| 04 | 对话上下文窗口 | agent-dev-a |
| 05 | 规则任务路由器 | agent-dev-a |
| 06 | 工具延迟统计 | agent-dev-b |
| 07 | TTL 智能缓存 | agent-dev-b |
| 08 | 令牌桶限流器 | agent-dev-b |
| 09 | 敏感结果脱敏 | agent-dev-b |
| 10 | 智能体结果评估器 | agent-dev-b |

## 本地 MCP

项目级 `.zhanlu/zhanlu.json` 将当前开发者连接到 Spec Manager DevelopmentAgent。任务交接、文档、AC 校验、结果回收和过程统计通过 MCP 自动完成，不需要开发者另外填报。
