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
        meta=dict(draft);meta['teacher_opinion']=draft['teacher_opinion']+'最终评价以指导教师审定为准。'
        should_fail(lambda:compose(root,meta),'元话语尾巴（最终评价以指导教师审定为准）被接受')
        meta2=dict(draft);meta2['teacher_opinion']=draft['teacher_opinion']+'以教师最终审定为准。'
        should_fail(lambda:compose(root,meta2),'元话语尾巴变体（以教师最终审定为准）被接受')
        res2=dict(result);res2['teacher_opinion']=result['teacher_opinion']+'以教师最终审定为准。'
        out2=td/'test-variant-tail.docx';fill(TEMPLATE,res2,out2)
        assert validate(TEMPLATE,out2,res2)['result']=='FAIL','validate 未拦元话语尾巴变体'
        meta4=dict(draft);meta4['teacher_opinion']=draft['teacher_opinion']+'最终评价以指导教师审定结果为准。'
        should_fail(lambda:compose(root,meta4),'元话语尾巴插字变体（审定结果为准）被接受')
        res4=dict(result);res4['teacher_opinion']=result['teacher_opinion']+'最终评价以指导教师审定结果为准。'
        out4=td/'test-variant-slip.docx';fill(TEMPLATE,res4,out4)
        assert validate(TEMPLATE,out4,res4)['result']=='FAIL','validate 未拦插字变体（审定结果为准）'
        import re as _re
        m=_re.search(r'→⑤收束`([^`]+)`',(ROOT/'SKILL.md').read_text(encoding='utf-8'))
        assert m,'SKILL 收束句样例未找到'
        meta5=dict(draft);meta5['teacher_opinion']=draft['teacher_opinion']+m.group(1)
        res5=compose(root,meta5)
        out5=td/'test-spec-closing.docx';fill(TEMPLATE,res5,out5)
        assert validate(TEMPLATE,out5,res5)['result']=='PASS','规范收束句样例未过门禁（规范与门禁必须同过）'
        try:
            bad2=dict(draft);bad2['sections']=[dict(x) for x in draft['sections']]
            bad2['sections'][1]=dict(bad2['sections'][1]);bad2['sections'][1]['paragraphs']=paragraphs+['特征归一化到[0,1]区间后比较']
            compose(root,bad2)
            raise AssertionError('非引用方括号数字未被拦截')
        except ValueError as e:
            assert '[[' in str(e) and '圆括号' in str(e),'误导报错未区分引用/非引用：'+str(e)
        try:
            import fitz
            import render_visual as _rv
            _doc=fitz.open()
            _doc.new_page()
            _n=_doc.new_page();_n.insert_text((72,72),'- 2 -')
            _c=_doc.new_page();_c.insert_text((72,72),'文献综述正文内容示例，用于验证正常页不被误判为空白页。')
            _probe=td/'probe.pdf';_doc.save(str(_probe));_doc.close()
            _pr=fitz.open(_probe)
            assert _rv.blank_page_kind(_pr.load_page(0))=='blank','空白页检测失效：整页无内容未判空白'
            assert _rv.blank_page_kind(_pr.load_page(1))=='blank','仅页码页未判空白'
            assert _rv.blank_page_kind(_pr.load_page(2)) is None,'正常内容页被误判空白'
            _pr.close()
            _proc=fitz.open();_pc=_proc.new_page();_pc.insert_text((72,72),'文献综述正文内容示例，用于验证正常页不被误判为空白页。');_proc.new_page()
            _pdf=td/'blank.pdf';_proc.save(str(_pdf));_proc.close()
            _fake=td/'fake.docx';_fake.write_bytes(b'X')
            _rr=_rv.render(_fake,td/'blankrender',pdf_in=_pdf)
            assert _rr['problems'] and any('第2页为空白页' in p for p in _rr['problems']),'渲染预检未拦空白页'
            blank_note='blank page detection / render blank-page blocking'
        except ImportError:
            blank_note='blank page detection skipped (PyMuPDF missing)'
        print('PASS template hash lock / non-overwrite / citation superscript / fixed teacher cell / raw citation rejection / teacher meta-tail rejection / meta-tail variant rejection / meta-tail slip-variant (shen-ding-jie-guo-wei-zhu) rejection / spec sample closing passes gates / non-citation bracket guidance / '+blank_note)
if __name__=='__main__':test()
