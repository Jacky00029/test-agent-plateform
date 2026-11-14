# 项目协作规则

先读取本项目 workspace.json、docs/工作流.md 及本需求 spec/plan。AI 不代替人工确认、评审或验收。结构化认领和进度由工作台维护。远程操作需用户授权。

业务实现仅使用 Python 标准库，代码放 `agent_tools/`，测试放 `tests/`。每次完成需求后运行 `python -m unittest discover -s tests -v`，通过 MCP 回收真实测试证据，不虚构耗时或结果。

## AI 联合设计校验

成员只需检出项目仓库，在 Spec 目录打开能读写文件并运行命令的 AI 工具，发送「完成 <需求编号> 的联合设计」。
AI 先读取需求、工作流和项目规范，更新设计草稿，然后从 Spec 目录运行：

- `python3 spec-checks/collab.py check` 检查项目结构和迁移冲突。
- 新建 MySQL 表时，运行 `python3 spec-checks/validate_sql.py <本次SQL文件>`。
- 新增或修改 OpenAPI 草案时，运行 `python3 spec-checks/openapi_guard.py <本次OpenAPI文件>`。

修复本次改动引入的问题后重跑，报告实际结果及待确认项，停在人工评审。需要 Python 3.9 或更新版本。
