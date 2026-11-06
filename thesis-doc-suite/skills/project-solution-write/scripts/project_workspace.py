#!/usr/bin/env python3
"""Safe project-assets workspace helper for project-solution-write (stdlib only).

与六件套同一共享资产契约：canonical project.json / facts / references / schedule、
activity.jsonl 审计流水、.asset-write.lock 排他写锁、.skill-tmp 所有权标记运行区、
成品 record-use 登记（版本路径 + SHA256）。起步时不覆盖任何既有项目资产。
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = 1
SKILL = 'project-solution-write'
MARKER = '.owned-by-project-solution-write'
RUN_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')
DOC_TYPES = {'introduction': 'project-introduction', 'implementation': 'implementation-plan'}
ASSET_KINDS = {'requirements': 'requirements.json', 'decisions': 'decisions.json'}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def read_identity(root: Path) -> dict | None:
    p = root / 'project-assets' / 'project.json'
    if not p.exists():
        return None
    if not p.is_file():
        raise ValueError(f'not a regular file: {p}')
    value = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or not value.get('project_id'):
        raise ValueError(f'missing project_id in existing asset: {p}')
    return value


def require_project(root: Path, requested: str | None = None):
    """返回 (project-assets 目录, project.json)；未初始化或 project_id 不符即拒绝。"""
    project = read_identity(root)
    if project is None:
        raise ValueError('项目尚未初始化：先执行 init --project-id … --title …')
    if requested and requested != project['project_id']:
        raise ValueError(f'project_id 不匹配：拒绝跨项目操作（{requested} != {project["project_id"]}）')
    return root / 'project-assets', project


def atomic_json(path: Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def stamp_event(base: Path, event: dict) -> None:
    payload = {'at': now(), **event}
    with (base / 'activity.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + '\n')


class exclusive:
    """与六件套同一把 .asset-write.lock；禁止强删或忽略冲突。"""

    def __init__(self, base: Path):
        self.file = Path(base) / '.asset-write.lock'

    def __enter__(self):
        try:
            fd = os.open(self.file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ValueError('项目共享资产正在写入；禁止强制覆盖 .asset-write.lock') from exc
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(now())
        return self

    def __exit__(self, *exc):
        self.file.unlink(missing_ok=True)
        return False


def cmd_init(args):
    if not args.project_id or not args.title:
        raise ValueError('init requires --project-id and --title')
    root = args.root.resolve()
    existing = read_identity(root)
    if existing:
        if existing['project_id'] != args.project_id:
            raise ValueError('Refusing cross-project collision: existing project_id is different')
        print(json.dumps({'status': 'reused', 'root': str(root), 'project_id': args.project_id}, ensure_ascii=False))
        return
    base = root / 'project-assets'
    base.mkdir(parents=True, exist_ok=True)
    target = base / 'project.json'
    ts = now()
    payload = {'schema_version': SCHEMA, 'project_id': args.project_id, 'name': args.title,
               'metadata': {'title': args.title, 'status': 'planning'},
               'created_at': ts, 'updated_at': ts}
    # Exclusive create prevents overwriting existing assets on race.
    try:
        with target.open('x', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write('\n')
    except FileExistsError:
        raise ValueError('project.json was created concurrently: inspect before reusing')
    # 与 project_assets.py init 一致：建空 facts/references/schedule，避免下游
    # status / record-use 因缺文件失败（跨 Skill 兼容的关键）。
    for kind, empty in (('references', {'items': []}), ('facts', {'items': []}),
                        ('schedule', {'plan': None})):
        atomic_json(base / f'{kind}.json', {'schema_version': SCHEMA, 'project_id': args.project_id,
                                            'updated_at': ts, **empty})
    stamp_event(base, {'action': 'init', 'actor': SKILL, 'project_id': args.project_id})
    print(json.dumps({'status': 'created', 'root': str(root), 'project_id': args.project_id}, ensure_ascii=False))


def cmd_status(args):
    root = args.root.resolve()
    existing = read_identity(root)
    print(json.dumps({'root': str(root), 'existing': bool(existing), 'project': existing}, ensure_ascii=False, indent=2))


def cmd_next(args):
    root = args.root.resolve()
    dir_name = 'project-introduction' if args.doc_type == 'introduction' else 'implementation-plan'
    folder = root / 'deliverables' / dir_name
    max_ver = 0
    for path in folder.glob('*.md') if folder.exists() else []:
        m = re.search(r'-v(\d+)\.md$', path.name, re.I)
        if m:
            max_ver = max(max_ver, int(m.group(1)))
    print('v' + str(max_ver + 1))


def cmd_workdir(args):
    root = args.root.resolve()
    require_project(root, args.project_id)
    run_id = args.run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:7]
    if not RUN_RE.fullmatch(run_id) or run_id in ('.', '..'):
        raise ValueError('非法 run-id')
    parent = root / '.skill-tmp' / SKILL
    if parent.is_symlink():
        raise ValueError('运行区为符号链接，拒绝创建')
    parent.mkdir(parents=True, exist_ok=True)
    out = parent / run_id
    if out.exists() or out.is_symlink():
        raise ValueError('运行目录已存在；不能覆盖')
    out.mkdir()
    (out / MARKER).write_text(SKILL + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'run_id': run_id, 'path': str(out)}, ensure_ascii=False))


def cmd_cleanup(args):
    root = args.root.resolve()
    require_project(root, args.project_id)
    rid = args.run_id
    if not RUN_RE.fullmatch(rid) or rid in ('.', '..'):
        raise ValueError('非法 run-id')
    parent = root / '.skill-tmp' / SKILL
    path = parent / rid
    marker = path / MARKER
    if parent.is_symlink() or path.is_symlink() or not path.is_dir() or not marker.is_file():
        raise ValueError('运行目录不存在、是符号链接或缺少所有权标记')
    if marker.read_text('utf-8').strip() != SKILL:
        raise ValueError(f'运行目录所有权标记不合法（期望 {MARKER}）')
    for part in path.rglob('*'):
        if part.is_symlink():
            raise ValueError('发现符号链接，拒绝清理')
    if path.resolve().parent != parent.resolve() or not path.resolve().is_relative_to(root):
        raise ValueError('路径越界')
    shutil.rmtree(path)
    print(json.dumps({'status': 'PASS', 'removed_run_id': rid}, ensure_ascii=False))


def cmd_record_use(args):
    root = args.root.resolve()
    base, project = require_project(root, args.project_id)
    file = (args.file if args.file.is_absolute() else root / args.file).resolve()
    if not file.is_file():
        raise ValueError('最终文件不存在；不允许记录虚假使用情况')
    if file.is_relative_to(root / '.skill-tmp'):
        raise ValueError('临时工作空间内的文件不可登记为最终文书')
    ids = [x.strip() for x in (args.ref_ids or '').split(',') if x.strip()]
    if ids:
        refs = {r['id'] for r in json.loads((base / 'references.json').read_text(encoding='utf-8'))['items']}
        if any(x not in refs for x in ids):
            raise ValueError('使用记录引用了不存在的参考文献 ID')
    event = {'action': 'document-published', 'actor': SKILL,
             'doc_type': DOC_TYPES[args.doc_type], 'path': str(file), 'reference_ids': ids,
             'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
             'project_id': project['project_id']}
    with exclusive(base):
        stamp_event(base, event)
    print(json.dumps({'status': 'PASS', 'recorded': str(file)}, ensure_ascii=False))


def cmd_write_asset(args):
    root = args.root.resolve()
    base, project = require_project(root, args.project_id)
    name = ASSET_KINDS[args.kind]
    data = json.loads(args.input.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != SCHEMA:
        raise ValueError(f'{name} 必须是 schema_version={SCHEMA} 的 JSON 对象')
    if data.get('project_id') != project['project_id']:
        raise ValueError('project_id 不匹配：拒绝写入其它项目的资产')
    if not isinstance(data.get('items'), list):
        raise ValueError(f'{name} 缺少 items 数组')
    data['updated_at'] = now()
    target = base / name
    with exclusive(base):
        atomic_json(target, data)
        stamp_event(base, {'action': 'asset-write', 'actor': SKILL, 'kind': args.kind,
                           'count': len(data['items']), 'project_id': project['project_id']})
    print(json.dumps({'status': 'PASS', 'written': str(target), 'items': len(data['items'])}, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('init', 'status', 'next-version', 'workdir', 'cleanup', 'record-use', 'write-asset'):
        s = sub.add_parser(name)
        s.add_argument('--root', type=Path, required=True)
        if name == 'init':
            s.add_argument('--project-id', required=True)
            s.add_argument('--title', required=True)
        if name in ('workdir', 'cleanup', 'record-use', 'write-asset'):
            s.add_argument('--project-id')
        if name == 'next-version':
            s.add_argument('--doc-type', choices=sorted(DOC_TYPES), required=True)
        if name == 'workdir':
            s.add_argument('--run-id')
        if name == 'cleanup':
            s.add_argument('--run-id', required=True)
        if name == 'record-use':
            s.add_argument('--file', type=Path, required=True)
            s.add_argument('--doc-type', choices=sorted(DOC_TYPES), required=True)
            s.add_argument('--ref-ids', default='')
        if name == 'write-asset':
            s.add_argument('--kind', choices=sorted(ASSET_KINDS), required=True)
            s.add_argument('--input', type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        {'init': cmd_init, 'status': cmd_status, 'next-version': cmd_next,
         'workdir': cmd_workdir, 'cleanup': cmd_cleanup, 'record-use': cmd_record_use,
         'write-asset': cmd_write_asset}[args.command](args)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print('ERROR:', e, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())