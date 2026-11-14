#!/usr/bin/env python3
"""按 database/设计规范.md 检查新建 MySQL 表；不执行 SQL，不重写文件。

参考 design-doc-generator/scripts/validate_sql.py，支持原始 SQL 与 Markdown。
"""
import argparse
from pathlib import Path
import re


_STR = r"'(?:''|\\.|[^'\\])*'|\"(?:\"\"|\\.|[^\"\\])*\""
_QUOTED = _STR + r'|`(?:``|[^`])*`'
_TOKENS = re.compile(_QUOTED + r'|[(),;]', re.S)
_NAME = r'(?:`[^`]+`|[A-Za-z_][A-Za-z_0-9]*)'
_CREATE = re.compile(r'^CREATE\s+(?:TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(' + _NAME + r'(?:\s*\.\s*' + _NAME + r')?)\s*\(', re.I)
_FORBIDDEN = set('type order group select from where table index key column database schema value values insert update delete drop create alter add primary foreign unique'.split())


def _syntax(text):
    # 注释说明里的 NOT NULL / ENGINE 等文字不算 SQL 属性；保留布尔默认值。
    return re.sub(_STR, lambda m: m.group() if m.group() in ("'0'", "'1'") else ' ', text)


def _split(text, separator):
    start, depth = 0, 0
    for match in _TOKENS.finditer(text):
        token = match.group()
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif token == separator and depth == 0:
            yield text[start:match.start()]
            start = match.end()
    yield text[start:]


def validate(sql):
    """返回 (ERROR/WARN, 表名, 原因) 列表；只校验显式 CREATE TABLE 字段定义。"""
    sql = re.sub(_QUOTED + r'|/\*.*?\*/|--[^\n]*|#[^\n]*', lambda m: ' ' if m.group().startswith(('/*', '--', '#')) else m.group(), sql, flags=re.S)
    issues, count = [], 0
    for statement in _split(sql, ';'):
        statement = statement.strip()
        if not re.match(r'^CREATE\s+(?:TEMPORARY\s+)?TABLE\b', statement, re.I):
            continue
        count += 1
        match = _CREATE.match(statement)
        if not match:
            issues.append(('ERROR', '未识别表', '建表必须显式列出字段，不支持省略字段定义的写法'))
            continue
        names = match[1].replace('`', '').replace(' ', '').split('.')
        name = names[-1]
        def add(level, message):
            issues.append((level, name, message))
        def check_name(value, label):
            if len(value) > 32 or not re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*', value) or re.search(r'(?<=_)\d+(?=_)', value):
                add('ERROR', label + '须为不超过32字符的小写英文/数字/下划线，以字母开头，避免纯数字中间段：' + value)
            if value.lower() in _FORBIDDEN:
                add('ERROR', label + '使用团队禁用名称：' + value)
        check_name(name, '表名')
        if len(names) > 1:
            check_name(names[0], '库名')
        depth, end = 1, None
        for token in _TOKENS.finditer(statement, match.end()):
            if token.group() == '(':
                depth += 1
            elif token.group() == ')':
                depth -= 1
                if depth == 0:
                    end = token.start()
                    break
        if end is None:
            add('ERROR', '无法识别完整字段列表，请核对括号和字符串')
            continue
        body, raw_options = statement[match.end():end], statement[end + 1:]
        options = _syntax(raw_options)
        fields = {}
        for part in _split(body, ','):
            part = part.strip()
            if re.match(r'^(?:PRIMARY|UNIQUE|KEY|INDEX|CONSTRAINT|FOREIGN|CHECK|FULLTEXT|SPATIAL)\b', part, re.I):
                continue
            field = re.match(r'^(' + _NAME + r')\s+(\w+)(.*)$', part, re.S)
            if not field:
                add('ERROR', '无法识别字段定义：' + part[:80])
                continue
            column, kind, raw_tail = field[1].strip('`'), field[2].lower(), field[3]
            tail = _syntax(raw_tail)
            check_name(column, '字段名')
            if column.lower() in fields:
                add('ERROR', '字段重复：' + column)
            fields[column.lower()] = (kind, tail)
            comment = re.search(r'\bCOMMENT\s+(' + _STR + ')', raw_tail, re.I)
            if not comment or not comment[1][1:-1].strip():
                add('ERROR', '字段缺少非空 COMMENT：' + column)
            length = re.match(r'\s*\(\s*(\d+)\s*\)', tail)
            if kind == 'varchar' and length and int(length[1]) > 5000:
                add('ERROR', 'VARCHAR 超过5000字符，请评估 TEXT：' + column)
            if column.startswith('is_') and (kind != 'tinyint' or not re.search(r'\bUNSIGNED\b', tail, re.I) or not re.search(r'\bNOT\s+NULL\b', tail, re.I) or not re.search(r"\bDEFAULT\s+(?:[01]\b|'[01]')", tail, re.I)):
                add('ERROR', '布尔字段须为 TINYINT UNSIGNED NOT NULL，DEFAULT 0或1：' + column)
            if not re.search(r'\bNOT\s+NULL\b', tail, re.I) and column != 'id':
                add('WARN', '请说明允许 NULL 的业务语义：' + column)
            if kind in ('float', 'double'):
                add('WARN', '精确金额和精确计算不能使用浮点类型：' + column)
            if kind.endswith('blob'):
                add('WARN', '确认该字段不用于存储图片、附件或大文件：' + column)
        for column in ('id', 'status', 'create_time', 'update_time'):
            if column not in fields:
                add('ERROR', '缺少基础字段：' + column)
        if 'id' in fields:
            kind, tail = fields['id']
            if kind != 'bigint' or not re.search(r'\bAUTO_INCREMENT\b', tail, re.I) or not re.search(r'\bNOT\s+NULL\b', tail, re.I):
                add('ERROR', 'id 须为 BIGINT NOT NULL AUTO_INCREMENT')
            if not re.search(r'\bPRIMARY\s+KEY\s*(?:USING\s+\w+\s*)?\(\s*`?id`?\s*\)', _syntax(body), re.I) and not re.search(r'\bPRIMARY\s+KEY\b', tail, re.I):
                add('ERROR', '须以 id 为单列主键')
        for column in ('status', 'create_time', 'update_time'):
            if column in fields:
                kind, tail = fields[column]
                allowed = ('tinyint',) if column == 'status' else ('datetime', 'timestamp')
                if kind not in allowed or not re.search(r'\bNOT\s+NULL\b', tail, re.I):
                    add('ERROR', column + ' 类型或非空约束不符合基础字段规范')
        if not re.search(r'\bENGINE\s*=\s*InnoDB\b', options, re.I):
            add('ERROR', '须显式声明 ENGINE=InnoDB')
        if not re.search(r'\b(?:CHARSET|CHARACTER\s+SET)\s*=?\s*utf8mb4\b', options, re.I):
            add('ERROR', '须显式声明字符集 utf8mb4')
        comment = re.search(r'\bCOMMENT\s*=\s*(' + _STR + ')', raw_options, re.I)
        if not comment or not comment[1][1:-1].strip():
            add('ERROR', '缺少非空表 COMMENT')
        if re.search(r'\bFOREIGN\s+KEY\b', body, re.I):
            add('WARN', '默认使用逻辑关联，请在设计中说明物理外键的必要性')
    if not count:
        issues.append(('WARN', '全局', '未发现显式 CREATE TABLE；已有表 ALTER 和其他 SQL 需另行核对，不代表已通过语法或兼容验证'))
    return issues


def validate_file(path):
    content = Path(path).read_text(encoding='utf-8')
    if Path(path).suffix.lower() == '.md':
        content = '\n'.join(re.findall(r'```sql\s*\n(.*?)```', content, re.S | re.I))
    return validate(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path, help='本次新建表的 SQL 文件或 Markdown 文档')
    args = parser.parse_args()
    errors, warnings = 0, 0
    for path in args.files:
        try:
            issues = validate_file(path)
        except (OSError, UnicodeError) as exc:
            issues = [('ERROR', '文件', str(exc))]
        for level, table, message in issues:
            print(f'{level} {path} [{table}] {message}')
            errors += level == 'ERROR'
            warnings += level == 'WARN'
    print(f'新建表规范检查：{errors} 个错误，{warnings} 个提醒；未执行 SQL。')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
