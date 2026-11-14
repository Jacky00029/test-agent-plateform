"""OpenAPI contract quality and import readback checks; never sends requests."""
import argparse
import copy
import json
from pathlib import Path
import re

METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}
SCHEMA_KEYS = {'type', 'format', 'nullable', 'enum', 'default', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'minLength', 'maxLength', 'pattern', 'minItems', 'maxItems', 'uniqueItems', 'description', 'required', 'properties', 'items', 'additionalProperties', 'allOf', 'anyOf', 'oneOf', 'readOnly', 'writeOnly'}


def resolve(doc, value, trail=()):
    if isinstance(value, list):
        return [resolve(doc, item, trail) for item in value]
    if not isinstance(value, dict):
        return value
    if '$ref' in value:
        ref = value['$ref']
        if not isinstance(ref, str) or not ref.startswith('#/') or ref in trail:
            raise ValueError('引用必须在文件内且不能循环：' + str(ref))
        target = doc
        try:
            for key in ref[2:].split('/'):
                target = target[key.replace('~1', '/').replace('~0', '~')]
        except (KeyError, TypeError):
            raise ValueError('引用不存在：' + ref)
        return resolve(doc, target, trail + (ref,))
    return {key: resolve(doc, item, trail) for key, item in value.items()}


def operations(doc):
    return [(method, path, value, methods.get('parameters', [])) for path, methods in doc.get('paths', {}).items() if isinstance(methods, dict) for method, value in methods.items() if method in METHODS and isinstance(value, dict)]


def mapping(root):
    path = Path(root) / 'docs/api/目录映射.json'
    return json.loads(path.read_text()) if path.exists() else {}


def check(doc, folders=None):
    errors = []
    if not isinstance(doc, dict) or not str(doc.get('openapi', '')).startswith('3.') or not operations(doc):
        return ['需要包含接口的 OpenAPI 3 文档']
    try:
        expanded = resolve(doc, doc)
    except ValueError as exc:
        return [str(exc)]
    def schema(value, location, named=False):
        if not isinstance(value, dict) or not value:
            errors.append(location + '：缺少字段结构，示例不能代替 schema')
            return
        if named and not value.get('description', '').strip():
            errors.append(location + '：缺少字段说明')
        if value.get('nullable') and value.get('enum') == [None]:
            return
        variants = next((value[k] for k in ('allOf', 'oneOf', 'anyOf') if k in value), None)
        if variants is not None:
            for index, item in enumerate(variants):
                schema(item, location + '/' + str(index))
            return
        kind = value.get('type')
        if kind == 'object' or 'properties' in value:
            if not value.get('properties') and not isinstance(value.get('additionalProperties'), dict):
                errors.append(location + '：对象没有字段定义或带类型的字典定义')
            for name, item in value.get('properties', {}).items():
                schema(item, location + '.' + name, True)
            for name in value.get('required', []):
                if name not in value.get('properties', {}):
                    errors.append(location + '：必填字段未定义 ' + name)
            if isinstance(value.get('additionalProperties'), dict):
                schema(value['additionalProperties'], location + '.*')
        elif kind == 'array':
            schema(value.get('items'), location + '[]')
        elif kind not in ('string', 'integer', 'number', 'boolean', 'null'):
            errors.append(location + '：缺少有效类型')
    ids, locations = set(), set()
    for method, path, op, shared_params in operations(expanded):
        label = method.upper() + ' ' + path
        identity = op.get('operationId')
        if not isinstance(identity, str) or not identity or identity in ids:
            errors.append(label + '：operationId 缺失或重复')
        if isinstance(identity, str):
            ids.add(identity)
        folder = op.get('x-apifox-folder', '')
        if not isinstance(folder, str) or not folder or '/' not in folder or folder != '/'.join(p.strip() for p in folder.split('/') if p.strip()):
            errors.append(label + '：需要固定的 x-apifox-folder 目录路径')
        if isinstance(folder, str):
            locations.add(folder)
        expected = next((value for prefix, value in sorted((folders or {}).items(), key=lambda item: -len(item[0])) if path == prefix or path.startswith(prefix + '/')), None)
        if expected and folder != expected:
            errors.append(label + '：目录应为 ' + expected)
        if not isinstance(op.get('summary'), str) or not op['summary'].strip():
            errors.append(label + '：缺少接口名称')
        tags = op.get('tags', [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            errors.append(label + '：接口标签需要字符串数组')
        path_params, seen = set(), set()
        for param in shared_params + op.get('parameters', []):
            name, where = param.get('name'), param.get('in')
            key = (where, name)
            if key in seen:
                errors.append(label + '：参数重复 ' + str(name))
            seen.add(key)
            if where == 'header' and str(name).lower() == 'authorization':
                errors.append(label + '：使用 security 鉴权，不重复定义 Authorization Header')
            if where == 'path':
                path_params.add(name)
                if param.get('required') is not True:
                    errors.append(label + '：路径参数必须必填 ' + str(name))
            if not param.get('description'):
                errors.append(label + '：参数缺少说明 ' + str(name))
            schema(param.get('schema'), label + '/参数/' + str(name))
        if path_params != set(re.findall(r'\{([^}]+)\}', path)):
            errors.append(label + '：路径占位符与参数定义不一致')
        body = op.get('requestBody')
        if body:
            if not body.get('content'):
                errors.append(label + '：请求体缺少内容定义')
            for media, value in body.get('content', {}).items():
                schema(value.get('schema'), label + '/请求/' + media)
        responses = op.get('responses', {})
        if not responses or not any(str(status).startswith('2') for status in responses):
            errors.append(label + '：缺少成功响应')
        for status, response in responses.items():
            if str(status) in ('204', '304') or method == 'head':
                continue
            if not response.get('content'):
                errors.append(label + '/响应/' + str(status) + '：缺少结构定义')
            for media, value in response.get('content', {}).items():
                schema(value.get('schema'), label + '/响应/' + str(status) + '/' + media)
    if len(locations) > 1:
        errors.append('同一契约包含多个目录，请按固定目录拆分文件')
    return errors


def schema_shape(node, inherited_type=None):
    if isinstance(node, list):
        return [schema_shape(v) for v in node]
    if not isinstance(node, dict):
        return node
    current_type = node.get('type', inherited_type)
    if node.get('nullable') and isinstance(node.get('type'), str):
        current_type = [node['type'], 'null']
    if isinstance(current_type, list):
        current_type = sorted(current_type)
    result = {}
    for key, value in node.items():
        if key not in SCHEMA_KEYS:
            continue
        if key == 'properties':
            result[key] = {name: schema_shape(item) for name, item in value.items()}
        elif key == 'required':
            result[key] = sorted(value)
        elif key in ('allOf', 'anyOf', 'oneOf'):
            # Composition branches constrain the same instance as their typed parent.
            # Apifox adds a redundant object type here; property/item schemas are separate instances.
            result[key] = sorted([schema_shape(item, current_type) for item in value], key=lambda item: json.dumps(item, sort_keys=True))
        else:
            result[key] = schema_shape(value)
    # Apifox stores OpenAPI 3.0 nullable as a 3.1 type union.
    if result.pop('nullable', False) and isinstance(result.get('type'), str):
        result['type'] = [result['type'], 'null']
    if isinstance(result.get('type'), list):
        result['type'] = sorted(result['type'])
    if inherited_type is not None and result.get('type') == inherited_type:
        result.pop('type', None)
    return result


def shapes(doc):
    expanded = resolve(doc, doc)
    return {(method, path): {
        'parameters': sorted([{'name':p['name'], 'in':p['in'], 'required':p.get('required', False), 'description':p.get('description', ''), 'schema':schema_shape(p.get('schema', {}))} for p in shared + op.get('parameters', [])], key=lambda p: (p['in'], p['name'])),
        'request': {media:schema_shape(v.get('schema', {})) for media,v in op.get('requestBody', {}).get('content', {}).items()},
        'request_required': op.get('requestBody', {}).get('required', False),
        'responses': {str(status):{media:schema_shape(v.get('schema', {})) for media,v in r.get('content', {}).items()} for status,r in op.get('responses', {}).items()}
    } for method,path,op,shared in operations(expanded)}


def differences(expected, actual):
    wanted, found = shapes(expected), shapes(actual)
    def paths(left, right, prefix=''):
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                location = prefix + '/' + str(key)
                if key not in left or key not in right:
                    yield location + ('（回读缺失）' if key not in right else '（回读多出）')
                else:
                    yield from paths(left[key], right[key], location)
        elif left != right:
            yield prefix
    errors = []
    for (method, path), shape in wanted.items():
        if (method, path) not in found:
            errors.append(method.upper() + ' ' + path + '：未回读到接口')
        elif found[(method, path)] != shape:
            errors.append(method.upper() + ' ' + path + '：请求/响应字段、约束或说明与契约不一致；差异位置：' + '、'.join(list(paths(shape, found[(method, path)]))[:8]))
    return errors


def prepared(doc):
    # Inline refs keep a same-named remote model from silently changing an endpoint's fields.
    return resolve(doc, copy.deepcopy(doc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    errors = 0
    root = Path(__file__).resolve().parent.parent
    for path in args.files:
        try:
            found = check(json.loads(path.read_text()), mapping(root))
        except (ValueError, OSError) as exc:
            found = [str(exc)]
        for message in found:
            print(str(path) + '：' + message)
        errors += len(found)
    print('接口契约检查：' + str(errors) + ' 个问题；未写入 Apifox。')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
