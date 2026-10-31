#!/usr/bin/env python3
"""Offline isolated INTEGRATION TEST ONLY. Test references are placeholders, not valid research."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess, sys, json, os, shutil

BASE=Path(__file__).resolve().parent.parent
SCRIPTS=BASE/'scripts'

def cmd(*args):
    p=subprocess.run([sys.executable,*map(str,args)],text=True,encoding="utf-8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        raise AssertionError('CMD FAILED: '+str(args)+'\nSTDOUT '+p.stdout+'\nSTDERR '+p.stderr)
    return p.stdout.strip()

def main():
    with TemporaryDirectory(prefix='literature-skill-QA-') as td:
        root=Path(td)
        cmd(SCRIPTS/'project_assets.py','init','--root',root,'--project-id','TEST-ONLY', '--name','虚拟结构测试项目')
        got=cmd(SCRIPTS/'project_assets.py','status','--root',root)
        assert 'TEST-ONLY' in got
        work=Path(cmd(SCRIPTS/'project_assets.py','workdir','--root',root,'--run-id','qa-001').splitlines()[-1])
        # Synthetic literature entries exist ONLY in OS tempdir, never in real registry.
        synthetic=[{'id':f'REF-{i:03d}',
                    'citation':f'测试作者{i}.测试论文{i}[J].测试期刊,2099,1(1):1-2.',
                    'source_url':f'https://example.invalid/fixture/{i}',
                    'source_type':'journal','verified':True,
                    'checked_at':'2099-01-01T00:00:00+00:00',
                    'project_relevance':'纯测试，不是真实论文'} for i in range(1,9)]
        f=work/'refs.json'
        f.write_text(json.dumps({'project_id':'TEST-ONLY','items':synthetic},ensure_ascii=False),encoding='utf8')
        cmd(SCRIPTS/'project_assets.py','merge','--root',root,'--kind','references','--input',f)
        filler='这是一段用于自动化排版烟雾测试的虚构正文，不代表真实研究资料或引用结论。' * 45
        sections=[]
        for i,h in enumerate(['1 引言','2 国内外研究现状','3 评述']):
            text=filler
            if i==0: text+=''.join(f'引用测试标记[[REF:REF-{j:03d}]]。' for j in range(1,9))
            sections.append({'heading':h,'paragraphs':[text]})
        draft={'project_id':'TEST-ONLY','title':'基于STM32与4G通信的胡杨林安全监测系统',
               'title_lines':['基于STM32与4G通信的','胡杨林安全监测系统'],
               'cover':{},'sections':sections,
               'teacher_opinion':'该生围绕测试环境进行文献格式验证，能够理解参考文献编排与技术文本结构的关系，' +
                  '已进行合理的案例整理并形成相对完整的写作路径。该评语为自动化测试用途，不可用于任何正式学校文书。'}
        inp=work/'draft.json';inp.write_text(json.dumps(draft,ensure_ascii=False),encoding='utf8')
        out=work/'composed.json'
        cmd(SCRIPTS/'compose_review.py','--root',root,'--draft',inp,'--out',out)
        final=root/'deliverables'/'literature-review'/'test-only-v1.docx'
        tmpl=BASE/'assets'/'official-literature-review-template.docx'
        cmd(SCRIPTS/'fill_review.py','--template',tmpl,'--data',out,'--out',final)
        check=json.loads(cmd(SCRIPTS/'validate_review.py','--template',tmpl,'--file',final,'--data',out))
        assert check['result']=='PASS',check
        assert check['references']==8
        if os.environ.get('LIT_QA_EXPORT'):
            shutil.copy2(final,os.environ['LIT_QA_EXPORT'])
        cmd(SCRIPTS/'project_assets.py','record-use','--root',root,'--file',final,'--doc-type','literature-review',
            '--ref-ids',','.join([f'REF-{j:03d}' for j in range(1,9)]))
        cmd(SCRIPTS/'project_assets.py','cleanup','--root',root,'--run-id','qa-001')
        assert final.exists() and (root/'project-assets'/'references.json').exists()
        assert not work.exists(), 'only the owned temp run may be removed'
        print('PASS isolated asset init/merge/compose/fill/validate/record-use/cleanup; '+str(check))

if __name__=='__main__': main()
