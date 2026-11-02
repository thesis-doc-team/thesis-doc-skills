#!/usr/bin/env python3
"""Append one guidance record to a draft JSON (逐条落盘 helper).

Draft fields follow templates/input.schema.json. topic/evidence_note/verification
are draft-only metadata and never enter the DOCX.
Usage:
  python scripts/append_record.py --draft D.json --init --project-id PID --title T
  python scripts/append_record.py --draft D.json --record rec.json
  python scripts/append_record.py --draft D.json --pair "problem||action" [--pair ...]
      [--topic ...] [--evidence-note ...] [--date ... --date-verified]
      [--location ... --location-verified]
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse, json
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def build_record(a):
    if a.record:
        rec = load(a.record)
        if not isinstance(rec, dict):
            raise ValueError('--record 必须是单条记录对象（JSON object）')
    else:
        if not a.pair:
            raise ValueError('需要 --record 文件或至少一个 --pair "问题||建议"')
        pairs = []
        for raw in a.pair:
            if '||' not in raw:
                raise ValueError('--pair 格式为 "问题||建议"，缺分隔符：' + raw[:30])
            problem, action = (x.strip() for x in raw.split('||', 1))
            if not problem or not action:
                raise ValueError('--pair 的问题与建议都不得为空')
            pairs.append({'problem': problem, 'action': action})
        rec = {'issue_pairs': pairs}
        for key, val in (('topic', a.topic), ('evidence_note', a.evidence_note),
                         ('date', a.date), ('location', a.location)):
            if val: rec[key] = val
        if a.date: rec['date_verified'] = bool(a.date_verified)
        if a.location: rec['location_verified'] = bool(a.location_verified)
    rec['status'] = 'draft'
    pairs = rec.get('issue_pairs')
    if not isinstance(pairs, list) or not (1 <= len(pairs) <= 4):
        raise ValueError('每条记录应为 1~4 组问题与建议')
    for p in pairs:
        if not isinstance(p, dict) or not str(p.get('problem', '')).strip() or not str(p.get('action', '')).strip():
            raise ValueError('每组必须同时有 problem 与 action，且非空')
        if rec.get('date') and not rec.get('date_verified'):
            raise ValueError('指导日期未确认，不得填写（须 date_verified=true）')
        if rec.get('location') and not rec.get('location_verified'):
            raise ValueError('指导地点未确认，不得填写（须 location_verified=true）')
    return rec

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--draft', required=True)
    p.add_argument('--init', action='store_true', help='新建草稿骨架（已存在则拒绝）')
    p.add_argument('--project-id')
    p.add_argument('--title')
    p.add_argument('--record', help='单条记录 JSON 文件（完整字段可用此式）')
    p.add_argument('--pair', action='append', help='问题||建议，可重复 1~4 次')
    p.add_argument('--topic'); p.add_argument('--evidence-note')
    p.add_argument('--date'); p.add_argument('--date-verified', action='store_true')
    p.add_argument('--location'); p.add_argument('--location-verified', action='store_true')
    a = p.parse_args()
    draft_path = Path(a.draft)
    if a.init:
        if draft_path.exists():
            raise ValueError(f'草稿已存在，不覆盖：{draft_path}（追加记录请去掉 --init）')
        if not a.project_id or not a.title:
            raise ValueError('--init 需要 --project-id 与 --title')
        save(draft_path, {'project_id': a.project_id, 'title': a.title, 'records': []})
        print(f'CREATED: {draft_path}')
        return
    if not draft_path.is_file():
        raise ValueError(f'草稿不存在：{draft_path}（先用 --init --project-id … --title … 创建）')
    draft = load(draft_path)
    if not isinstance(draft.get('records'), list):
        raise ValueError('草稿缺少 records 数组，不是本 Skill 输入草稿')
    rec = build_record(a)
    draft['records'].append(rec)
    save(draft_path, draft)
    print(f'APPENDED: record #{len(draft["records"])} (total={len(draft["records"])}) -> {draft_path}')

if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e: raise SystemExit('ERROR: ' + str(e))
