#!/usr/bin/env python3
"""Idempotent registration/upgrade of ONLY technical-visual-assets in a Claude plugin.

No package installs, no network, no edits to other Skills. Explicit --apply
required; writes only plugin core/contracts/skill-catalog.json and backs it up.
"""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ENTRY=json.loads((HERE/'catalog-entry.json').read_text('utf-8'))


def run(plugin_root:Path, apply:bool=False):
    skill=plugin_root/'skills'/ENTRY['name']/'SKILL.md'
    catalog=plugin_root/'core'/'contracts'/'skill-catalog.json'
    if not skill.is_file() or not catalog.is_file():
        raise ValueError('缺少新的 SKILL.md 或插件现有 skill-catalog.json；请检查 --plugin-root')
    data=json.loads(catalog.read_text('utf-8'))
    if not isinstance(data.get('skills'),list):
        raise ValueError('原有技能注册表不是 skills[] 数组，拒绝更改')
    found=[i for i,item in enumerate(data['skills']) if item.get('name')==ENTRY['name']]
    if len(found)>1:raise ValueError('已有同名重复条目，需要人工处理')
    if found and data['skills'][found[0]].get('command') != ENTRY['command']:
        raise ValueError('已有同名 Skill 命令不一致，拒绝覆盖')
    prev=data['skills'][found[0]] if found else None
    if prev==ENTRY:return 'EXISTS: 目录已注册且版本一致，无需修改'
    if not apply:return 'DRY-RUN: '+('将仅更新 technical-visual-assets 注册项' if found else '将仅新增 technical-visual-assets 注册项')
    backup=catalog.with_suffix('.json.before-technical-visual-assets.bak')
    if not backup.exists():
        backup.write_bytes(catalog.read_bytes())
    if found:data['skills'][found[0]]=ENTRY
    else:data['skills'].append(ENTRY)
    catalog.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
    return 'PASS: '+('更新' if found else '新增')+'技术图示 Skill 注册，未修改其他业务 Skill'


def main():
    p=argparse.ArgumentParser(description='只更新/新增一个插件注册项，不安装任何软件')
    p.add_argument('--plugin-root',required=True)
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    try:print(run(Path(args.plugin_root).resolve(),args.apply))
    except (OSError,ValueError,json.JSONDecodeError) as e:
        print('FAIL: '+str(e),file=sys.stderr);sys.exit(2)

if __name__=='__main__':main()
