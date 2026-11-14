# 智能体工具首个版本 · 版本范围

> 工作台生成；结构化来源为version.json。

| 功能 | 说明 |
|---|---|
| F001 | Prompt 预算裁剪 |
| F002 | 工具调用参数校验 |
| F003 | 智能退避重试策略 |
| F004 | 对话上下文窗口 |
| F005 | 规则任务路由器 |
| F006 | 工具延迟统计 |
| F007 | TTL 智能缓存 |
| F008 | 令牌桶限流器 |
| F009 | 敏感结果脱敏 |
| F010 | 智能体结果评估器 |

## 需求与认领索引

| 需求 | 对应功能 | 负责人 | 设计评审人 |
|---|---|---|---|
| [敏感结果脱敏](../../specs/LOCAL-18b30f4f7357-%E6%95%8F%E6%84%9F%E7%BB%93%E6%9E%9C%E8%84%B1%E6%95%8F/spec.md) | F009 | agent-dev-b | agent-manager |
| [智能体结果评估器](../../specs/LOCAL-2132501f0fc9-%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%93%E6%9E%9C%E8%AF%84%E4%BC%B0%E5%99%A8/spec.md) | F010 | agent-dev-b | agent-manager |
| [规则任务路由器](../../specs/LOCAL-8811571a6a2d-%E8%A7%84%E5%88%99%E4%BB%BB%E5%8A%A1%E8%B7%AF%E7%94%B1%E5%99%A8/spec.md) | F005 | agent-dev-a | agent-manager |
| [工具延迟统计](../../specs/LOCAL-950cd38550bb-%E5%B7%A5%E5%85%B7%E5%BB%B6%E8%BF%9F%E7%BB%9F%E8%AE%A1/spec.md) | F006 | agent-dev-b | agent-manager |
| [智能退避重试策略](../../specs/LOCAL-a08232a3d1bc-%E6%99%BA%E8%83%BD%E9%80%80%E9%81%BF%E9%87%8D%E8%AF%95%E7%AD%96%E7%95%A5/spec.md) | F003 | agent-dev-a | agent-manager |
| [令牌桶限流器](../../specs/LOCAL-af4306d9285c-%E4%BB%A4%E7%89%8C%E6%A1%B6%E9%99%90%E6%B5%81%E5%99%A8/spec.md) | F008 | agent-dev-b | agent-manager |
| [工具调用参数校验](../../specs/LOCAL-c6c70d6fc045-%E5%B7%A5%E5%85%B7%E8%B0%83%E7%94%A8%E5%8F%82%E6%95%B0%E6%A0%A1%E9%AA%8C/spec.md) | F002 | agent-dev-a | agent-manager |
| [TTL 智能缓存](../../specs/LOCAL-cab223a89063-TTL%20%E6%99%BA%E8%83%BD%E7%BC%93%E5%AD%98/spec.md) | F007 | agent-dev-b | agent-manager |
| [Prompt 预算裁剪](../../specs/LOCAL-e2248ebc5724-Prompt%20%E9%A2%84%E7%AE%97%E8%A3%81%E5%89%AA/spec.md) | F001 | agent-dev-a | agent-manager |
| [对话上下文窗口](../../specs/LOCAL-f637343f6341-%E5%AF%B9%E8%AF%9D%E4%B8%8A%E4%B8%8B%E6%96%87%E7%AA%97%E5%8F%A3/spec.md) | F004 | agent-dev-a | agent-manager |
