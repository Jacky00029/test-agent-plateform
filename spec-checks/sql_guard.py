"""共享建表冲突检查；从迁移 SQL 识别表，无需登记，不执行 SQL。"""
import json
from pathlib import Path
import re



_NAME = r'(?:`[^`]+`|[A-Za-z_][A-Za-z_0-9]*)'
_CREATE = re.compile(r'\bCREATE\s+(?:TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(' + _NAME + r'(?:\s*\.\s*' + _NAME + r')?)', re.I)
_PREFIX = re.compile(r'\bCREATE\s+(?:TEMPORARY\s+)?TABLE\b', re.I)
_VALID = re.compile(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)?\Z')


def key(engine, name):
    name = name.replace('`', '').replace(' ', '').lower()
    if engine not in ('mysql', 'clickhouse') or not _VALID.fullmatch(name):
        raise ValueError('数据库类型或表名无效；表名使用 table 或 schema.table')
    # 此中枢只维护一个共享 MySQL 逻辑库；带库名前缀与不带前缀的同名表视为同一张。
    if engine == 'mysql':
        name = name.rsplit('.', 1)[-1]
    return engine, name


def created_tables(sql, engine):
    # 去除注释与字符串，保留反引号中的表名；无法解析的静态建表语句直接报错。
    masked = re.sub(r"/\*.*?\*/|--[^\n]*|#[^\n]*|'(?:''|\\.|[^'\\])*'|\"(?:\"\"|\\.|[^\"\\])*\"", ' ', sql, flags=re.S)
    if re.search(r'\b(?:PREPARE|EXECUTE\s+IMMEDIATE)\b', masked, re.I):
        raise ValueError('动态 SQL 不能自动检查重复建表，请改为静态迁移并人工评审')
    matches = list(_CREATE.finditer(masked))
    if len(matches) != len(list(_PREFIX.finditer(masked))):
        raise ValueError('存在无法识别的 CREATE TABLE，请人工核对 SQL 写法')
    return [key(engine, m.group(1)) for m in matches]


def check(root, extra=None):
    """检查迁移是否重复建表；extra 用于尚未落盘的上传预检。"""
    root = Path(root)
    errors, occurrences = [], {}
    files = [(p, p.read_text(encoding='utf-8')) for engine in ('mysql', 'clickhouse') for p in (root / 'database' / engine / 'migrations').glob('*.sql')]
    if extra:
        files.append((root / extra[0], extra[1]))
    for path, sql in files:
        try:
            tables = created_tables(sql, path.parent.parent.name)
        except ValueError as exc:
            errors.append(str(path.relative_to(root)) + '：' + str(exc))
            continue
        for table in tables:
            occurrences.setdefault(table, []).append(str(path.relative_to(root)))
    for table, paths in occurrences.items():
        if len(paths) > 1:
            errors.append('重复建表 SQL ' + '/'.join(table) + '：' + '、'.join(paths))
    baseline = root / 'database/baseline.json'
    if baseline.is_file():
        path = json.loads(baseline.read_text(encoding='utf-8')).get('mysql', {}).get('path')
        if path and (root / 'database' / path).is_file():
            try:
                tables = created_tables((root / 'database' / path).read_text(encoding='utf-8'), 'mysql')
                errors.extend('基线已有表不能重复建表：' + table for engine, table in occurrences if (engine, table) in tables)
            except (ValueError, UnicodeError):
                errors.append('MySQL 基线建表语句无法分析')
    return errors, occurrences
