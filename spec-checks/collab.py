#!/usr/bin/env python3
"""Spec 项目本地协作工具：不执行 SQL，不发布或修改远端。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
import sql_guard

ROOT = Path(os.environ.get('SPEC_ROOT', Path(__file__).resolve().parents[1]))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def inside(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("路径必须位于指定目录内")
    return path


def registry(root):
    entries = read_json(root / "workspace.json")["repositories"]
    names = [entry["name"] for entry in entries]
    if len(names) != len(set(names)):
        raise ValueError("仓库登记重复")
    return entries


def new_spec(root, issue, title):
    if not re.fullmatch(r"[1-9][0-9]*|LOCAL-[0-9a-f]{12}", issue):
        raise ValueError("需求编号须为正整数或工具生成的 LOCAL 编号")
    if not title.strip() or re.search(r"[/\\\x00-\x1f]", title) or title.strip() in (".", ".."):
        raise ValueError("需求名不能为空，不能包含路径分隔或控制字符")
    number = f"{int(issue):03d}" if issue.isdigit() else issue
    if list((root / "specs").glob(number + "-*")):
        raise ValueError("该需求编号已存在，请更新原需求，不覆盖已有内容")
    target = inside(root / "specs", number + "-" + title.strip())
    body = (root / "specs/_templates/spec.md").read_text(encoding="utf-8")
    target.mkdir()
    (target / "spec.md").write_text(body.replace("[需求名]", title.strip()).replace("NNN", number), encoding="utf-8")
    return target


def import_baseline(root, source, source_ref):
    if not source_ref.strip():
        raise ValueError("必须记录验收环境及代码版本来源")
    text = source.read_text(encoding="utf-8")
    # 只接收表结构导出；不能用含数据或例程的备份充当基线。
    if not re.search(r"\bCREATE\s+TABLE\b", text, re.I):
        raise ValueError("未发现 CREATE TABLE，请提供纯结构导出")
    if re.search(r"(?:^|;)\s*(INSERT\b|REPLACE\b|UPDATE\b|DELETE\b|LOAD\s+DATA\b|CALL\b)", text, re.I | re.M):
        raise ValueError("检测到数据操作，拒绝导入；请使用 --no-data --skip-triggers 导出")
    if re.search(r"\bDEFINER\s*=", text, re.I):
        raise ValueError("导出含 DEFINER，请排除触发器/例程并评审结构")
    meta = read_json(root / "database/baseline.json")
    if meta["mysql"]["status"] != "pending_export" or (root / "database/mysql/schema.sql").exists():
        raise ValueError("基线已建立；后续结构通过迁移和评审演进，不能用导入覆盖")
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    target = root / "database/mysql/baselines" / (checksum + ".sql")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    (root / "database/mysql/schema.sql").write_text(text, encoding="utf-8")
    meta["mysql"].update(status="imported_pending_review", source_ref=source_ref, path=str(target.relative_to(root / "database")), schema_path="mysql/schema.sql", sha256=checksum, imported_at=stamp())
    write_json(root / "database/baseline.json", meta)


def redact_credentials(value):
    """导入时剔除文档示例中可识别的凭据字面值，保留接口结构。"""
    patterns = [
        r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+",
        r"(?i)Bearer\s+[A-Za-z0-9_.~-]{15,}",
        r"\b(?:APS-|sk-)[A-Za-z0-9_-]{20,}",
    ]
    if isinstance(value, dict):
        return {key: redact_credentials(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_credentials(item) for item in value]
    if isinstance(value, str):
        for pattern in patterns:
            value = re.sub(pattern, "<REDACTED_CREDENTIAL>", value)
    return value


def import_api(root, service, source, project_id, directory_id, branch_id=None):
    if service not in {entry["name"] for entry in registry(root)}:
        raise ValueError("服务未在 workspace.json 登记")
    document = read_json(source)
    if not isinstance(document, dict) or not (str(document.get("openapi", "")).startswith("3.") or document.get("swagger") == "2.0"):
        raise ValueError("需要 Apifox 导出的 OpenAPI 3.x / Swagger 2.0 JSON")
    if not isinstance(document.get("paths"), dict) or not document["paths"]:
        raise ValueError("接口快照没有有效 paths")
    index = read_json(root / "docs/api/index.json")
    if index["project_id"] not in (None, project_id):
        raise ValueError("与团队单一 Apifox 项目不一致")
    branch_id = branch_id or index.get("branch_id")
    if not branch_id:
        raise ValueError("必须记录实际 Apifox 分支 ID（--branch-id）")
    if index.get("branch_id") not in (None, branch_id):
        raise ValueError("基线分支与当前登记不一致，请先评审分支切换")
    target = root / "docs/api" / (service + ".openapi.json")
    write_json(target, redact_credentials(document))
    index["project_id"] = project_id
    index["branch_id"] = branch_id
    index["services"][service] = {"directory_id": directory_id, "branch_id": branch_id, "path": target.name, "sha256": digest(target), "source_sha256": digest(source), "transform": "redact-credential-literals-v1", "imported_at": stamp(), "status": "imported_pending_review"}
    write_json(root / "docs/api/index.json", index)


def check(root, ready=False):
    errors, pending = [], []
    entries = registry(root)
    for required in ["AGENTS.md", "docs/工作流.md", "docs/接入记录.md", "specs/_templates/spec.md", "specs/_templates/plan.md", "specs/_templates/tasks.md", "specs/_templates/delivery.md"]:
        if not (root / required).is_file():
            errors.append("缺少 " + required)
    capabilities = read_json(root / "workspace.json").get("capabilities", {})
    if capabilities.get("database") is not False:
        baseline = read_json(root / "database/baseline.json")
        mysql = baseline["mysql"]
        if mysql["status"] == "pending_export":
            pending.append("已验收测试库真实 MySQL 基线尚未导入")
        else:
            path = inside(root / "database", mysql["path"])
            if not path.is_file() or not mysql.get("sha256") or digest(path) != mysql["sha256"] or not mysql.get("source_ref"):
                errors.append("MySQL 基线缺少来源或校验值不一致")
            if mysql["status"] != "reviewed":
                pending.append("MySQL 基线尚未完成人工评审")
            if not inside(root / "database", mysql.get("schema_path", "mysql/schema.sql")).is_file():
                errors.append("共享库当前结构 schema.sql 缺失")
        clickhouse = baseline.get("clickhouse", {})
        if clickhouse.get("status") != "reviewed" or not clickhouse.get("files"):
            pending.append("ClickHouse ODS/DWS/ADS 结构尚未核对")
        for item in clickhouse.get("files", []):
            path = inside(root / "database", item["path"])
            if not path.is_file() or not item.get("sha256") or digest(path) != item["sha256"]:
                errors.append("ClickHouse 基线文件缺失或校验失败")
    if capabilities.get("apifox") is not False:
        coverage_path = root / "docs/api/coverage.json"
        if coverage_path.exists() and read_json(coverage_path).get("status") != "reviewed":
            pending.append("接口目录归属与导出覆盖核对尚未评审")
        index = read_json(root / "docs/api/index.json")
        for service, item in index["services"].items():
            if service not in {entry["name"] for entry in entries}:
                errors.append("接口来源包含未知服务 " + service)
            path = inside(root / "docs/api", item["path"])
            if not path.is_file() or not item.get("sha256") or digest(path) != item["sha256"]:
                errors.append(service + " 接口快照缺失或校验失败")
            elif not isinstance(read_json(path).get("paths"), dict):
                errors.append(service + " 接口 paths 无效")
            if not item.get("directory_id") or not index.get("project_id"):
                errors.append(service + " 缺少 Apifox 来源标识")
            if item.get("status") != "reviewed":
                pending.append(service + " 接口快照待评审")
        for entry in entries:
            if entry["api_required"] and entry["name"] not in index["services"]:
                pending.append(entry["name"] + " 接口快照尚未导入")
    migrations = {}
    for engine in ["mysql", "clickhouse"]:
        for path in (root / "database" / engine / "migrations").glob("*.sql"):
            match = re.fullmatch(r"([0-9]{14})_(0*[1-9][0-9]*|LOCAL-[0-9a-f]{12})_.+\.sql", path.name)
            if not match:
                errors.append("迁移命名无效 " + str(path.relative_to(root)))
                continue
            identifier = match[1]
            if identifier in migrations:
                errors.append("迁移编号重复 " + identifier)
            migrations[identifier] = path
    table_errors, _ = sql_guard.check(root)
    errors.extend(table_errors)
    base = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA")
    if base:
        result = subprocess.run(["git", "diff", "--name-status", "--no-renames", base, "HEAD", "--", "database/*/migrations/*.sql"], cwd=root, capture_output=True, text=True)
        if result.returncode:
            errors.append("无法核对迁移历史，请获取 MR 基线提交")
        else:
            errors.extend("旧迁移不能修改/删除：" + line for line in result.stdout.splitlines() if not line.startswith("A\t"))
    if ready:
        errors.extend(pending)
    return {"check": "readiness" if ready else "structure", "ok": not errors, "errors": errors, "pending": pending}


def versions(root, allow_dirty=False):
    result = {"kind": "source_snapshot", "release_ready": False, "captured_at": stamp(), "repositories": []}
    for entry in [{"name": "spec-project", "path": "."}] + registry(root):
        path = (root / entry["path"]).resolve()
        if not path.is_dir():
            raise ValueError("仓库未检出：" + entry["name"])
        def git(*args):
            return subprocess.check_output(["git", "-C", str(path), *args], text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(git("status", "--porcelain"))
        if dirty and not allow_dirty:
            raise ValueError(entry["name"] + " 有未提交内容，先提交或使用 --allow-dirty 生成不可交付预览")
        result["repositories"].append({"name": entry["name"], "commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"), "dirty": dirty})
    result["preview"] = any(item["dirty"] for item in result["repositories"])
    result["note"] = "仅代码版本；制品校验值、环境配置和验收证据在 delivery 中补齐"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("readiness")
    command = commands.add_parser("new")
    command.add_argument("issue")
    command.add_argument("title", nargs="?")
    command.add_argument("--local", action="store_true", help="使用唯一的本地编号，无需访问 GitLab；该模式只传需求名称")
    command = commands.add_parser("import-baseline")
    command.add_argument("source", type=Path)
    command.add_argument("--source-ref", required=True)
    command = commands.add_parser("import-api")
    command.add_argument("service")
    command.add_argument("source", type=Path)
    command.add_argument("--project-id", required=True)
    command.add_argument("--directory-id", required=True)
    command.add_argument("--branch-id")
    command = commands.add_parser("versions")
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    try:
        if args.command in ("check", "readiness"):
            result = check(ROOT, args.command == "readiness")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1
        if args.command == "new":
            if args.local:
                if args.title is not None:
                    raise ValueError("--local 模式仅传需求名称，例如 new --local 需求名称")
                print(new_spec(ROOT, "LOCAL-" + uuid.uuid4().hex[:12], args.issue))
            else:
                if args.title is None:
                    raise ValueError("请提供编号和需求名称，或用 new --local 需求名称")
                print(new_spec(ROOT, args.issue, args.title))
        elif args.command == "import-baseline":
            import_baseline(ROOT, args.source, args.source_ref)
            print("真实 MySQL 结构已导入，仍需评审；未执行 SQL")
        elif args.command == "import-api":
            import_api(ROOT, args.service, args.source, args.project_id, args.directory_id, args.branch_id)
            print("接口快照已导入，仍需评审")
        else:
            write_json(args.output, versions(ROOT, args.allow_dirty))
            print(args.output)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print("未完成：" + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
