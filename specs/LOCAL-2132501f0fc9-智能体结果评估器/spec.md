# 智能体结果评估器 · 需求规格

## 目标与业务规则

用可组合规则评估智能体输出，形成通过率与失败明细。

## 验收条件

| 编号 | 场景、操作与预期 |
|---|---|
| AC-1 | evaluate 支持 exact、contains、regex 和 json_equals 检查，返回 total/passed/pass_rate/failures。 |
| AC-2 | 混合用例只统计真实通过项；JSON 按结构比较，失败项包含用例 ID 与实际原因。 |