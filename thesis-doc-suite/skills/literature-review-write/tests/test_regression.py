#!/usr/bin/env python3
"""Failure gates and negative tests: catches formatting regressions before publication."""
import sys, tempfile, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from docx import Document
from template_tools import require_official_template,TEMPLATE
from validate_review import validate
from fill_review import fill
from compose_review import compose

def should_fail(fn,descr):
    try:fn()
    except (ValueError,RuntimeError):return
    raise AssertionError('未拦截：'+descr)

def test():
    with tempfile.TemporaryDirectory(prefix='lr-regression-') as td:
        td=Path(td)
        # Even a visually similar but different file cannot use fixed offsets.
        clone=td/'modified-template.docx';d=Document(TEMPLATE)
        d.paragraphs[7].add_run('X')
        d.save(clone)
        should_fail(lambda: require_official_template(clone),'模板哈希漂移')
        # Valid synthetic input uses invented citations only inside this test sandbox.
        ids=[f'REF-{i:03}' for i in range(1,9)]
        root=td/'project';assets=root/'project-assets';assets.mkdir(parents=True)
        (assets/'project.json').write_text(json.dumps({'schema_version':1,'project_id':'TEST','metadata':{}},ensure_ascii=False))
        refs={'schema_version':1,'project_id':'TEST','items':[
            {'id':rid,'citation':f'Test Person{i}.Fake Test Source[J].No-Real-Journal,2099,1:1.',
             'source_url':'https://example.invalid/test','source_type':'journal','verified':True,
             'checked_at':'2099-01-01'} for i,rid in enumerate(ids,1)]}
        (assets/'references.json').write_text(json.dumps(refs))
        paras=['这是一条自动化排版测试句，所有参考文献信息均为虚构，严禁用于正式报告。'*42]
        paragraphs=['在本段文本中采用文献' + ''.join('[[REF:'+rid+']]' for rid in ids)+'。'] + paras
        sections=[{'heading':f'{i} '+h,'paragraphs':paragraphs if i==2 else paras} for i,h in enumerate(['引言','国内外研究现状','评述'],1)]
        draft={'project_id':'TEST','title':'基于STM32与4G通信的胡杨林安全监测系统',
               'title_lines':['基于STM32与4G通信的','胡杨林安全监测系统'],
               'sections':sections,'teacher_opinion':'该生能够围绕研究主题进行资料归纳和文字编排，梳理相关研究的技术特点与适用范围，形成完整的文献综述框架，后续仍需由实际指导教师核实全部论证内容。'}
        result=compose(root,draft)
        out=td/'test-v1.docx'
        fill(TEMPLATE,result,out)
        assert validate(TEMPLATE,out,result)['result']=='PASS'
        should_fail(lambda:fill(TEMPLATE,result,out),'禁止覆盖已存在成品')
        mod=Document(out)
        cell=mod.tables[0].cell(0,0)
        target=next(r for p in cell.paragraphs for r in p.runs if '[1]' in r.text)
        target.font.superscript=False
        bad=td/'normal-citation.docx';mod.save(bad)
        assert validate(TEMPLATE,bad,result)['result']=='FAIL','普通引用未被发现'
        mod=Document(out);mod.tables[0].cell(1,0).paragraphs[0].add_run('附加文字')
        bad=td/'bad-teacher-label.docx';mod.save(bad)
        assert validate(TEMPLATE,bad,result)['result']=='FAIL','官方教师区文本被更改未发现'
        broken=dict(draft);broken['sections']=[dict(x) for x in draft['sections']]
        broken['sections'][1]=dict(broken['sections'][1]);broken['sections'][1]['paragraphs']=paragraphs+['未经归档的[12]论文编号']
        should_fail(lambda:compose(root,broken),'未经REF标记的原始编号被接受')
        print('PASS template hash lock / non-overwrite / citation superscript / fixed teacher cell / raw citation rejection')
if __name__=='__main__':test()
