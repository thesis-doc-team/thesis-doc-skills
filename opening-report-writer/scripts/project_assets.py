#!/usr/bin/env python3
"""Project-local shared assets for independent thesis-document Skills (stdlib only).

Never modifies source documents or the installed Skill. Only mutates the explicitly
chosen project root's project-assets/ directory. Cleans only owned temporary runs.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid
from urllib.parse import urlparse

SCHEMA = 1
ASSET_DIR = 'project-assets'
WORK_BASE = ('.skill-tmp', 'opening-report-writer')
MARKER = '.owned-by-opening-report-writer'
KINDS = ('references', 'facts', 'schedule', 'project')
REQUIRED_REF = ('id', 'citation', 'source_url', 'source_type', 'verified')
RUN_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def load(path):
    with Path(path).open('r', encoding='utf-8') as f:
        return json.load(f)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    try:
        with tmp.open('w', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def project_dir(root):
    return Path(root).resolve() / ASSET_DIR


@contextmanager
def exclusive(project):
    lock = project / '.asset-write.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('共享资产已有另一进程在写入，请检查锁文件并稍后重试；禁止强制覆盖')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(now())
        yield
    finally:
        lock.unlink(missing_ok=True)


def get_store(root):
    base = project_dir(root)
    if not (base / 'project.json').is_file():
        raise ValueError(f'共享资产尚未初始化：{base}；先执行 init')
    metadata = load(base / 'project.json')
    if metadata.get('schema_version') != SCHEMA or not metadata.get('project_id'):
        raise ValueError('项目资产版本不受支持或缺少 project_id，不能盲目复用')
    return base, metadata


def stamp_event(base, event):
    payload = {'at': now(), **event}
    with (base / 'activity.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + '\n')


def init(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise ValueError(f'项目根目录不存在：{root}')
    base = root / ASSET_DIR
    base.mkdir(exist_ok=True)
    path = base / 'project.json'
    if path.exists():
        prior = load(path)
        if prior.get('project_id') != args.project_id:
            raise ValueError('该目录已有其他项目资产；不可改用新 project_id 覆盖')
        print(f'EXISTS: {base}（未覆盖任何文件）')
        return
    if any((base / f'{k}.json').exists() for k in ('references', 'facts', 'schedule')):
        raise ValueError('发现无项目标识的共享资产，拒绝自动初始化以免覆盖')
    timestamp = now()
    atomic_json(path, {'schema_version': SCHEMA, 'project_id': args.project_id,
                       'name': args.name, 'metadata': {}, 'created_at': timestamp,
                       'updated_at': timestamp})
    for kind in ('references', 'facts'):
        atomic_json(base / f'{kind}.json', {'schema_version': SCHEMA,
                                          'project_id': args.project_id, 'items': [],
                                          'updated_at': timestamp})
    atomic_json(base / 'schedule.json', {'schema_version': SCHEMA,
                                        'project_id': args.project_id, 'plan': None,
                                        'updated_at': timestamp})
    stamp_event(base, {'action': 'init', 'actor': args.actor, 'project_id': args.project_id})
    print(f'CREATED: {base}')


def check_records(kind, items):
    if not isinstance(items, list):
        raise ValueError(f'{kind} 更新格式需要 items 数组')
    ids = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].strip():
            raise ValueError('每条共享资产都必须有非空稳定 id')
        if item['id'] in ids:
            raise ValueError(f'同一次更新中出现重复 ID: {item["id"]}')
        ids.add(item['id'])
        if kind == 'references':
            missing = [k for k in REQUIRED_REF if k not in item or item[k] in ('', None)]
            if missing:
                raise ValueError(f'文献 {item["id"]} 缺少字段: {missing}')
            if not isinstance(item['verified'], bool):
                raise ValueError('文献 verified 必须为布尔值')
            if item['verified'] and not item.get('checked_at'):
                raise ValueError('verified=true 的文献必须记录实际核验日期 checked_at')
            url = urlparse(item['source_url'])
            if url.scheme not in ('http', 'https') or not url.netloc:
                raise ValueError(f'文献 {item["id"]} 来源 URL 不合法')
        elif kind == 'facts':
            if not item.get('statement') or not item.get('source'):
                raise ValueError(f'技术事实 {item["id"]} 缺少 statement/source')
            if item.get('status') not in ('implemented', 'declared', 'unverified', 'proposed'):
                raise ValueError('技术事实 status 须是 implemented/declared/unverified/proposed')
    return ids


def check_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError('周计划必须是 plan 对象')
    if not plan.get('id') or not isinstance(plan.get('total_weeks'), int) or plan['total_weeks'] < 1:
        raise ValueError('周计划必须有稳定 id 及正整数 total_weeks')
    if plan.get('status') not in ('draft', 'confirmed'):
        raise ValueError('周计划 status 必须是 draft 或 confirmed；confirmed 只能在用户确认后使用')
    stages = plan.get('stages')
    if not isinstance(stages, list) or not stages:
        raise ValueError('周计划缺少阶段')
    ids, weeks = set(), []
    for stage in stages:
        if not isinstance(stage, dict) or not stage.get('id') or not stage.get('task'):
            raise ValueError('周计划每个阶段须有 id/task')
        if stage['id'] in ids:
            raise ValueError('周计划阶段 id 重复')
        ids.add(stage['id'])
        a, b = stage.get('from_week'), stage.get('to_week')
        if not isinstance(a, int) or not isinstance(b, int) or a > b or a < 1:
            raise ValueError('无效的周区间')
        weeks.extend(range(a, b+1))
    if sorted(weeks) != list(range(1, plan['total_weeks']+1)):
        raise ValueError('共享周计划不能缺周、重周或超出总周数')
    if bool(plan.get('start_date')) != bool(plan.get('end_date')):
        raise ValueError('起止日期应同时有或同时无；不得套用旧范本日期')


def merge(args):
    base, project = get_store(args.root)
    incoming = load(args.input)
    if incoming.get('project_id') not in (None, project['project_id']):
        raise ValueError('跨项目资产拒绝写入：project_id 不匹配')
    kind = args.kind
    path = base / f'{kind}.json'
    with exclusive(base):
        previous = load(path)
        if previous.get('project_id') != project['project_id'] or previous.get('schema_version') != SCHEMA:
            raise ValueError('资产版本/项目 ID 不一致')
        if kind in ('references', 'facts'):
            new_items = incoming.get('items')
            check_records(kind, new_items)
            old = previous.get('items', [])
            check_records(kind, old)
            by_id = {x['id']: x for x in old}
            change_ids = []
            for item in new_items:
                old_item = by_id.get(item['id'])
                if old_item is not None and old_item != item:
                    if not args.replace or not args.reason:
                        raise ValueError(f'资产 {item["id"]} 已存在但内容不同；要有依据地更新，须 --replace --reason')
                    change_ids.append(item['id'])
                elif old_item is None:
                    change_ids.append(item['id'])
                by_id[item['id']] = item
            result = list(by_id.values())
            if kind == 'references':
                seen = {}
                for entry in result:
                    cit = re.sub(r'\s+', '', re.sub(r'^\[\d+\]', '', entry['citation'])).casefold()
                    if cit in seen and seen[cit] != entry['id']:
                        raise ValueError(f'参考文献重复：{entry["id"]} 与 {seen[cit]}')
                    seen[cit] = entry['id']
            previous['items'] = result
        elif kind == 'schedule':
            plan = incoming.get('plan')
            check_plan(plan)
            old = previous.get('plan')
            if old is not None and old != plan and (not args.replace or not args.reason):
                raise ValueError('共享周计划已存在，不可悄悄覆盖；须 --replace --reason')
            change_ids = [plan['id']] if old != plan else []
            previous['plan'] = plan
        else:
            updates = incoming.get('metadata')
            if not isinstance(updates, dict):
                raise ValueError('project 更新必须有 metadata 对象')
            old = previous.get('metadata', {})
            conflicts = [k for k, v in updates.items() if k in old and old[k] != v]
            if conflicts and (not args.replace or not args.reason):
                raise ValueError(f'项目元信息冲突 {conflicts}；须 --replace --reason')
            change_ids = list(updates)
            old.update(updates)
            previous['metadata'] = old
        if not change_ids:
            print(f'UNCHANGED: {path}')
            return
        previous['updated_at'] = now()
        atomic_json(path, previous)
        stamp_event(base, {'action': 'merge', 'kind': kind, 'ids': change_ids,
                           'actor': args.actor, 'reason': args.reason or '新增资产'})
        print(f'UPDATED: {path} ({len(change_ids)} entries)')


def compose(args):
    base, project = get_store(args.root)
    draft = load(args.draft)
    if not isinstance(draft, dict):
        raise ValueError('任务书草稿数据必须是 JSON 对象')
    if draft.get('project_id') not in (None, project['project_id']):
        raise ValueError('任务书草稿与资产 project_id 不一致')
    plan = load(base / 'schedule.json')['plan']
    if plan is None:
        raise ValueError('共享周计划为空；先创建或核实项目级计划，不在文书里临时编造')
    check_plan(plan)
    refs = load(base / 'references.json')['items']
    check_records('references', refs)
    ref_by_id = {r['id']: r for r in refs}
    selected = draft.get('selected_reference_ids')
    if selected is None:
        selected = [r['id'] for r in refs if r['verified']]
    if not isinstance(selected, list) or len(set(selected)) != len(selected):
        raise ValueError('selected_reference_ids 必须是无重复的数组')
    if len(selected) < 10:
        raise ValueError('已选参考文献少于 10 篇，不能组装正式任务书')
    chosen = []
    for rid in selected:
        if rid not in ref_by_id or not ref_by_id[rid]['verified']:
            raise ValueError(f'文献 {rid} 不存在或尚未真实核验，不得导入正式文书')
        r = ref_by_id[rid]
        chosen.append({k: r[k] for k in ('citation', 'source_url', 'source_type', 'verified')}
                      | ({'checked_at': r['checked_at']} if r.get('checked_at') else {}))
    expected = ['title', 'thesis_content', 'issuer_opinion']
    if any(not draft.get(k) for k in expected):
        raise ValueError(f'文书特有草稿必须明确提供：{expected}；不从共享技术事实自动冒充导师意见')
    data = {k: draft[k] for k in expected}
    for key in ('college', 'class_name', 'student_name', 'student_id',
                'instructor_name', 'instructor_title', 'receiver_opinion'):
        if draft.get(key):
            data[key] = draft[key]
        elif project.get('metadata', {}).get(key):
            data[key] = project['metadata'][key]
    data['total_weeks'] = plan['total_weeks']
    if plan.get('start_date'):
        data['start_date'] = plan['start_date']
        data['end_date'] = plan['end_date']
    data['schedule'] = [{key: entry[key] for key in ('from_week', 'to_week', 'task')}
                        for entry in plan['stages']]
    data['references'] = chosen
    atomic_json(args.out, data)
    print(f'COMPOSED: {args.out}; reused {len(chosen)} refs; {len(data["schedule"])} schedule phases; plan={plan["status"]}')


def owned_work_base(root):
    """Reject symlinked temp ancestors to prevent writes/deletes outside project."""
    root = Path(root).resolve()
    level1 = root / WORK_BASE[0]
    level2 = level1 / WORK_BASE[1]
    if level1.is_symlink() or level2.is_symlink():
        raise ValueError('临时目录父路径为符号链接，拒绝越界写入/清理')
    if level2.resolve().parent != level1.resolve() or not level2.resolve().is_relative_to(root):
        raise ValueError('临时目录路径脱离项目根目录，拒绝操作')
    return level2


def create_workdir(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise ValueError('项目根目录不存在')
    run_id = args.run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
    if not RUN_RE.fullmatch(run_id) or run_id in ('.', '..'):
        raise ValueError('非法 run_id')
    path = owned_work_base(root) / run_id
    path.mkdir(parents=True, exist_ok=False)
    (path / MARKER).write_text('opening-report-writer\n', encoding='utf-8')
    print(str(path))


def cleanup(args):
    root = Path(args.root).resolve()
    if not RUN_RE.fullmatch(args.run_id) or args.run_id in ('.', '..'):
        raise ValueError('非法 run_id')
    base = owned_work_base(root)
    path = base / args.run_id
    if path.is_symlink() or not path.is_dir() or path.resolve().parent != base:
        raise ValueError('只允许删除本 Skill 自己创建的单个运行临时目录')
    marker = path / MARKER
    if not marker.is_file() or marker.is_symlink() or marker.read_text(encoding='utf-8') != 'opening-report-writer\n':
        raise ValueError('目录缺少合法所有权标记，禁止删除')
    # Symlinks inside the owned directory are not followed by shutil.rmtree.
    shutil.rmtree(path)
    print(f'CLEANED: {path}')


def record_use(args):
    base, project = get_store(args.root)
    file = Path(args.file).resolve()
    if not file.is_file():
        raise ValueError('最终文件不存在；不允许记录虚假使用情况')
    root = Path(args.root).resolve()
    if file.is_relative_to(root / '.skill-tmp'):
        raise ValueError('临时工作空间内的文件不可登记为最终文书')
    ids = [x.strip() for x in args.ref_ids.split(',') if x.strip()]
    if ids:
        refs = {r['id'] for r in load(base / 'references.json')['items']}
        if any(x not in refs for x in ids):
            raise ValueError('使用记录引用了不存在的参考文献 ID')
    event = {'action': 'document-published', 'actor': args.actor,
             'doc_type': args.doc_type, 'path': str(file), 'reference_ids': ids,
             'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
             'project_id': project['project_id']}
    with exclusive(base):
        stamp_event(base, event)
    print(f'RECORDED: {file}')


def status(args):
    base, project = get_store(args.root)
    refs = load(base / 'references.json')['items']
    facts = load(base / 'facts.json')['items']
    plan = load(base / 'schedule.json')['plan']
    print(json.dumps({'project_id': project['project_id'], 'name': project['name'],
                      'asset_dir': str(base), 'references': len(refs),
                      'verified_references': sum(r.get('verified') is True for r in refs),
                      'facts': len(facts), 'schedule': None if plan is None else {
                          'id': plan['id'], 'total_weeks': plan['total_weeks'],
                          'status': plan['status'], 'stages': len(plan['stages'])}},
                     ensure_ascii=False, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('init'); s.add_argument('--root', required=True)
    s.add_argument('--project-id', required=True); s.add_argument('--name', required=True)
    s.add_argument('--actor', default='opening-report-writer'); s.set_defaults(func=init)
    s = sub.add_parser('merge'); s.add_argument('--root', required=True)
    s.add_argument('--kind', required=True, choices=KINDS); s.add_argument('--input', required=True)
    s.add_argument('--replace', action='store_true'); s.add_argument('--reason', default='')
    s.add_argument('--actor', default='opening-report-writer'); s.set_defaults(func=merge)
    s = sub.add_parser('compose'); s.add_argument('--root', required=True)
    s.add_argument('--draft', required=True); s.add_argument('--out', required=True); s.set_defaults(func=compose)
    s = sub.add_parser('workdir'); s.add_argument('--root', required=True)
    s.add_argument('--run-id'); s.set_defaults(func=create_workdir)
    s = sub.add_parser('cleanup'); s.add_argument('--root', required=True)
    s.add_argument('--run-id', required=True); s.set_defaults(func=cleanup)
    s = sub.add_parser('record-use'); s.add_argument('--root', required=True)
    s.add_argument('--file', required=True); s.add_argument('--doc-type', required=True)
    s.add_argument('--ref-ids', default=''); s.add_argument('--actor', default='opening-report-writer')
    s.set_defaults(func=record_use)
    s = sub.add_parser('status'); s.add_argument('--root', required=True); s.set_defaults(func=status)
    args = p.parse_args(argv)
    try:
        args.func(args)
    except (ValueError, OSError, json.JSONDecodeError, KeyError) as exc:
        p.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
