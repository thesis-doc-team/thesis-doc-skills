#!/usr/bin/env python3
"""可持久化的项目探索候选库：推荐批次、拒绝去重、迭代、确认（不生成正式方案）。"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from render_candidate import render, validate

SCHEMA = 1
STATUS = {'candidate', 'interested', 'rejected', 'confirmed'}
BASE_CONTENT = {'title', 'overview', 'features'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def safe_json(path: Path, default):
    if not path.exists(): return default
    return json.loads(path.read_text('utf-8'))


def atomic_write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def safe_id(value: str) -> str:
    if not re.fullmatch(r'PROJECT-\d{4,}', value):
        raise ValueError('非法候选 ID')
    return value


def catalog_path(root): return root / 'discovery' / 'catalog.json'


def load(root):
    c = safe_json(catalog_path(root), {'schema_version': SCHEMA, 'next_sequence': 1, 'projects': {}})
    if c.get('schema_version') != SCHEMA or not isinstance(c.get('projects'), dict):
        raise ValueError('catalog.json schema 不兼容；停止而非覆盖')
    return c


def fold(text):
    s = unicodedata.normalize('NFKC', str(text or '')).casefold()
    for s2 in ('基于stm32的', '基于单片机的', '基于物联网的', '设计与实现', '系统的设计', '智能', '系统', '平台', '终端', '监测', '管理'):
        s = s.replace(s2, '')
    return ''.join(c for c in s if c.isalnum())


def bigrams(s):
    s = fold(s)
    return {s[i:i+2] for i in range(max(0, len(s)-1))} if len(s)>1 else ({s} if s else set())


def score_similarity(a, b):
    """保守词面去重；语义替换由 Agent 二次判定。"""
    ta,tb=fold(a['title']),fold(b['title'])
    if ta and ta == tb:
        return 1.0
    sa = (a.get('signature') or {}).get('scenario','')
    sb = (b.get('signature') or {}).get('scenario','')
    if sa and sb and fold(sa) != fold(sb):
        return 0.0
    A=bigrams(a['title']);B=bigrams(b['title'])
    title=len(A&B)/len(A|B) if A|B else 0
    fa={fold(f['name']) for f in a.get('features',[])}
    fb={fold(f['name']) for f in b.get('features',[])}
    function=len(fa&fb)/len(fa|fb) if fa|fb else 0
    # 同场景且核心功能重复高度，或标题高度接近 + 功能大致一致
    if sa and sb and fold(sa) == fold(sb) and function >= .60:
        return max(.88, title)
    return max(title if function>=.5 else 0, .7*title + .3*function)


class Lock:
    def __init__(self, root):
        self.file = root / 'discovery' / '.discovery-write.lock'
    def __enter__(self):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd=os.open(self.file, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
        except FileExistsError as e:
            raise ValueError('选题资产被另一任务占用，不得覆盖锁文件') from e
        with os.fdopen(fd,'w') as f: f.write(now())
        return self
    def __exit__(self,*_):
        self.file.unlink(missing_ok=True)


def append_log(root, obj):
    loc = root/'discovery'/'history.jsonl'
    loc.parent.mkdir(parents=True, exist_ok=True)
    with loc.open('a',encoding='utf-8') as f:
        f.write(json.dumps({'timestamp':now(),**obj},ensure_ascii=False)+'\n')


def project_dir(root, project_id):
    base=root/'projects'
    if base.is_symlink(): raise ValueError('projects 目录不能是符号链接')
    target=base/safe_id(project_id)
    if target.is_symlink(): raise ValueError('项目目录不能是符号链接')
    return target


def latest_data(root, project_id):
    path=project_dir(root,project_id)/'data'/'project.json'
    if not path.is_file(): raise ValueError('项目资产缺失: '+str(path))
    return json.loads(path.read_text('utf-8'))


def canonical(data):
    d=validate(data)
    s=data.get('signature') or {}
    if not isinstance(s, dict): raise ValueError('signature 必须是对象')
    return {**d, 'signature': {k:str(v) for k,v in s.items() if k in ('scenario','domain','mechanism')}}


def metadata(root, c):
    return [(pid,latest_data(root,pid)) for pid in c['projects']]


def previous_records(root,c):
    return metadata(root,c)


def output_project(staging, project_id, newdata, version, status):
    p=staging/project_id
    (p/'data'/'revisions').mkdir(parents=True,exist_ok=True)
    folder=p/'versions'/version
    files=render(newdata,folder)
    result={'schema_version': SCHEMA,'project_id':project_id,'status':status,'version':version,
            'title':newdata['title'],'overview':newdata['overview'], 'features':newdata['features'],
            'signature':newdata.get('signature', {}), 'updated_at':now()}
    atomic_write(p/'data'/'revisions'/f'{version}.json', result)
    atomic_write(p/'data'/'project.json', result)
    return result,files


def check_index_consistency(root,c):
    for pid in c['projects']:
        if not project_dir(root,pid).is_dir(): raise ValueError('目录与 catalog 不一致：'+pid)


def add_batch(root, payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('projects'),list):
        raise ValueError('输入要求 {"projects":[...]}')
    candidates=payload['projects']
    if not 1 <=len(candidates)<=10:
        raise ValueError('每批必须 1～10 个候选项目，不可超出上限')
    normalized=[canonical(p) for p in candidates]
    root.mkdir(parents=True,exist_ok=True)
    with Lock(root):
        c=load(root); check_index_consistency(root,c)
        existing=previous_records(root,c)
        accepted=[]; skipped=[]
        for d in normalized:
            matched=None
            for pid,old in existing + [(p[0],p[1]) for p in accepted]:
                if score_similarity(d,old)>=.82:
                    matched={'existing_id':pid,'status':old.get('status','candidate'),
                             'title':old['title']}
                    break
            if matched: skipped.append({'title':d['title'],'duplicate_of':matched});continue
            pid='PROJECT-'+f"{c['next_sequence']:04d}"
            c['next_sequence']+=1
            accepted.append((pid,d))
        temp_root=root/'.skill-tmp'/'project-solution-write'
        temp_root.mkdir(parents=True,exist_ok=True)
        created=[]
        with tempfile.TemporaryDirectory(prefix='discovery-',dir=temp_root) as temp:
            stage=Path(temp)
            generated=[]
            for pid,d in accepted:
                info,files=output_project(stage,pid,d,'v1.0','candidate')
                generated.append({'project_id':pid,'title':d['title'],'version':'v1.0','files':[f.replace(str(stage),str(root/'projects')) for f in files]})
            try:
                for pid,d in accepted:
                    dest=project_dir(root,pid)
                    if dest.exists(): raise ValueError('ID 冲突：'+pid)
                    shutil.move(str(stage/pid),str(dest))
                    created.append(dest)
                    c['projects'][pid]={'title':d['title'],'status':'candidate','version':'v1.0'}
                atomic_write(catalog_path(root),c)
            except Exception:
                for p in created: shutil.rmtree(p)
                raise
            for item in generated:
                append_log(root,{'action':'candidate-created','id':item['project_id'],'version':'v1.0'})
            for item in skipped:
                append_log(root,{'action':'candidate-skipped-duplicate',**item})
        return {'created':generated,'skipped':skipped,'created_count':len(generated),'max_per_batch':10}


def revise(root,project_id,payload):
    payload=dict(payload)
    change_summary=payload.pop('change_summary','')
    d=canonical(payload)
    with Lock(root):
        c=load(root)
        if project_id not in c['projects']: raise ValueError('找不到该候选项目')
        old=latest_data(root,project_id)
        if old['status']=='confirmed':
            raise ValueError('已确认项目进入正式方案，候选修改必须先进行明确的立项变更')
        if old['status']=='rejected':
            raise ValueError('项目已拒绝，先使用 set-status --reconsider 恢复后才能修改')
        cur=old['version']
        match=re.fullmatch(r'v(\d+)\.(\d+)',cur)
        if not match: raise ValueError('未知版本格式')
        ver=f"v{match.group(1)}.{int(match.group(2))+1}"
        # content change required
        if all(old.get(k)==d.get(k) for k in ('title','overview','features','signature')):
            raise ValueError('内容未改变，不应创建空修订版本')
        out=project_dir(root,project_id)
        work=out/'versions'/ver
        if work.exists() or (out/'data'/'revisions'/f'{ver}.json').exists(): raise ValueError('版本冲突')
        try:
            files=render(d,work)
            merged={**old,**d,'version':ver,'updated_at':now()}
            atomic_write(out/'data'/'revisions'/f'{ver}.json',merged)
            atomic_write(out/'data'/'project.json',merged)
            c['projects'][project_id].update({'title':d['title'],'version':ver})
            atomic_write(catalog_path(root),c)
        except Exception:
            shutil.rmtree(work,ignore_errors=True)
            raise
        append_log(root,{'action':'candidate-revised','id':project_id,'from':cur,'to':ver,
                         'change_summary':change_summary or '内容更新（参见两版本差异）'})
        return {'project_id':project_id,'from':cur,'version':ver,'files':files}


def set_status(root,project_id,status,reconsider=False,user_confirmed=False):
    if status not in STATUS: raise ValueError('未知状态')
    with Lock(root):
        c=load(root)
        if project_id not in c['projects']: raise ValueError('项目不存在')
        old=latest_data(root,project_id)
        former=old['status']
        if former=='confirmed' and status!='confirmed':
            raise ValueError('已确认项目不得直接退回；须走正式变更流程')
        if former=='rejected' and status!='rejected' and not reconsider:
            raise ValueError('恢复已拒绝项目必须显式 --reconsider')
        if status=='confirmed' and former!='interested':
            raise ValueError('必须先标为 interested 并由用户确认最终题目与核心功能，不能推荐后自动确认')
        if status=='confirmed' and not user_confirmed:
            raise ValueError('正式立项必须显式提供 --user-confirmed，确认来自用户指令')
        if status==former:
            return {'project_id':project_id,'status':status,'version':old['version'],'unchanged':True}
        old['status']=status;old['updated_at']=now()
        p=project_dir(root,project_id)
        atomic_write(p/'data'/'project.json',old)
        c['projects'][project_id]['status']=status
        atomic_write(catalog_path(root),c)
        if status=='rejected':
            rej=root/'discovery'/'rejected-projects.json'
            rs=safe_json(rej,{'schema_version':SCHEMA,'items':[]})
            rs['items'].append({'id':project_id,'title':old['title'],'signature':old.get('signature',{}),'at':now()})
            atomic_write(rej,rs)
        if status=='confirmed':
            # 正式方案仍须在现有 project_workspace init 之下启动，不自动编造功能完成状态
            pass
        append_log(root,{'action':'status-changed','id':project_id,'from':former,'to':status})
        return {'project_id':project_id,'from':former,'status':status,'version':old['version']}


def set_profile(root,payload):
    if not isinstance(payload,dict): raise ValueError('profile 必须是对象')
    allowed={'major','technologies','interests','education','purpose','resources','preferences','constraints','notes'}
    if any(x not in allowed for x in payload): raise ValueError('profile 含不允许的字段')
    with Lock(root):
        target=root/'discovery'/'profile.json'
        previous=safe_json(target,{'schema_version':SCHEMA,'known':{}})
        if previous.get('schema_version')!=SCHEMA: raise ValueError('profile 版本不兼容')
        previous['known'].update(payload)
        previous['updated_at']=now()
        atomic_write(target,previous)
        append_log(root,{'action':'profile-updated','fields':list(payload)})
        return {'status':'updated','known_fields':list(previous['known'])}


def show(root):
    c=load(root)
    result=[]
    for pid in c['projects']:
        info=latest_data(root,pid)
        result.append({'project_id':pid,'title':info['title'],'status':info['status'],'version':info['version']})
    return {'total':len(result),'projects':result}


def main():
    p=argparse.ArgumentParser(description='探索推荐资产与项目版本管理')
    sub=p.add_subparsers(dest='cmd',required=True)
    for cmd in ('batch','revise','set-status','profile','list','show'):
        sp=sub.add_parser(cmd)
        sp.add_argument('--root',type=Path,required=True)
        if cmd in ('batch','revise','profile'): sp.add_argument('--input',type=Path,required=True)
        if cmd in ('revise','set-status','show'): sp.add_argument('--project-id',required=True)
        if cmd=='set-status':
            sp.add_argument('--status',choices=sorted(STATUS),required=True)
            sp.add_argument('--reconsider',action='store_true')
            sp.add_argument('--user-confirmed',action='store_true',help='用户明确确认题目与功能后才能使用')
    args=p.parse_args()
    try:
        root=args.root.resolve()
        if args.cmd=='batch': obj=add_batch(root,json.loads(args.input.read_text('utf-8')))
        elif args.cmd=='revise': obj=revise(root,args.project_id,json.loads(args.input.read_text('utf-8')))
        elif args.cmd=='set-status': obj=set_status(root,safe_id(args.project_id),args.status,args.reconsider,args.user_confirmed)
        elif args.cmd=='profile': obj=set_profile(root,json.loads(args.input.read_text('utf-8')))
        elif args.cmd=='show': obj=latest_data(root,safe_id(args.project_id))
        else: obj=show(root)
        print(json.dumps(obj,ensure_ascii=False,indent=2))
    except (OSError,ValueError,KeyError,json.JSONDecodeError,RuntimeError,FileExistsError) as e:
        print('ERROR:',e,file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':
    sys.exit(main())
