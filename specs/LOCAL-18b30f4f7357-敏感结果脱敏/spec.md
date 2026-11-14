# 敏感结果脱敏 · 需求规格

## 目标与业务规则

递归清理智能体工具输出中的凭据，避免敏感字段进入日志和统计。

## 验收条件

| 编号 | 场景、操作与预期 |
|---|---|
| AC-1 | redact 对 password/token/api_key/authorization/secret 等键递归替换为 [REDACTED]，支持嵌套 dict/list。 |
| AC-2 | redact_text 将 Bearer 后内容替换为 [REDACTED]；处理不修改输入且重复执行保持幂等。 |