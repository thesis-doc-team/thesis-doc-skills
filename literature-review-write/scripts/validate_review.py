#!/usr/bin/env python3
"""Structural/semantic QA against the exact official template (render QA still required)."""
import argparse, hashlib, json, re
from pathlib import Path
from lxml import etree
from docx import Document

REF=re.compile(r'^\[(\d+)\]')
MARK=re.compile(r'\[(?:\d+)(?:[，,\-–]\d+)*\]')

def xc(node):
    return etree.tostring(node,method='c14n') if node is not None else b''

def section_layout(s):
    return tuple(getattr(s,key) for key in ('page_width','page_height','top_margin','bottom_margin',
               'left_margin','right_margin','header_distance','footer_distance','orientation'))

def validate(template,docx,data):
    t=Document(template);d=Document(docx)
    issues=[];facts={}
    def check(ok,description):
        if not ok: issues.append(description)
    check(len(t.sections)==len(d.sections),'分节数量与官方不同')
    check(len(t.tables)==len(d.tables),'表格数量与官方不同')
    for i in range(min(len(t.sections),len(d.sections))):
        check(section_layout(t.sections[i])==section_layout(d.sections[i]),f'第{i+1}节页面边距或尺寸改变')
    if t.tables and d.tables:
        tt=t.tables[0];dt=d.tables[0]
        check(len(tt.rows)==len(dt.rows) and len(tt.columns)==len(dt.columns),'表格行列结构不同')
        for tag in ('tblPr','tblGrid'):
            check(xc(getattr(tt._tbl,tag))==xc(getattr(dt._tbl,tag)),f'表格 {tag} 被改变')
        for j in range(min(len(tt.rows),len(dt.rows))):
            check(xc(tt.rows[j]._tr.trPr)==xc(dt.rows[j]._tr.trPr),f'表格第{j+1}行 trPr 被改变')
            check(xc(tt.cell(j,0)._tc.tcPr)==xc(dt.cell(j,0)._tc.tcPr),f'表格第{j+1}行 tcPr 被改变')
        check(tt.cell(0,0).paragraphs[0].text==dt.cell(0,0).paragraphs[0].text,'官方正文说明被修改')
        check(tt.cell(1,0).paragraphs[0].text==dt.cell(1,0).paragraphs[0].text,'审阅区标题被修改')
        signature=lambda cell:[p.text for p in cell.paragraphs if '指导教师（签字）' in p.text or ('年' in p.text and '月' in p.text and '日' in p.text)]
        check(signature(tt.cell(1,0))==signature(dt.cell(1,0)),'签字或日期原文字/格式位置被更改')
        body=dt.cell(0,0).paragraphs[1:]
        ref_header=next((k for k,p in enumerate(body) if p.text.strip()=='4 参考文献'),None)
        check(ref_header is not None,'缺少参考文献章节')
        if ref_header is not None:
            writing=body[:ref_header]
            lit=body[ref_header+1:]
            chars=len(re.sub(r'\s+','', ''.join(re.sub(MARK,'',p.text) for p in writing)))
            # Heading counts are negligible; the compose gate counts body only.
            check(chars>=2500,'正文不足2500字符')
            markers=[]
            for p in writing:
                for r in p.runs:
                    for m in MARK.finditer(r.text):
                        markers.append(m.group())
                        check(r.font.superscript is True, '正文引用存在非 Word 上标')
            check(bool(markers),'正文未发现上标引用')
            bib=[]
            for p in lit:
                m=REF.search(p.text)
                if m:
                    bib.append(int(m.group(1)))
                    for r in p.runs:
                        check(r.font.superscript is not True,'参考文献列表不应整体上标')
            check(bib==list(range(1,len(bib)+1)),'参考文献编号不连续')
            check(len(bib)==len(data.get('bibliography',[])),'参考文献条数与组装输入不符')
            check(all(any(f'[{i}]' in m for m in markers) for i in bib),'存在未被正文引用的参考文献')
            facts.update({'narrative_chars':chars,'intext_citations':len(markers),'references':len(bib)})
        opinion=dt.cell(1,0).text
        check(data['teacher_opinion'] in opinion,'教师审阅意见内容缺失')
        check(len(re.sub(r'\s+','',data['teacher_opinion']))>=50,'教师审阅意见少于50字')
    check(len(t.paragraphs)==len(d.paragraphs),'封面及表格外段落数量改变')
    for idx in (0,7,8):
        if idx<len(t.paragraphs) and idx<len(d.paragraphs):
            check(t.paragraphs[idx].text==d.paragraphs[idx].text,f'封面固定文字段落{idx}被更改')
    check(Path(template).resolve()!=Path(docx).resolve(),'交付文件不能覆盖官方模板')
    return {'result':'PASS' if not issues else 'FAIL','issues':issues,
            'template_sha256':hashlib.sha256(Path(template).read_bytes()).hexdigest(),
            'output_sha256':hashlib.sha256(Path(docx).read_bytes()).hexdigest(),**facts}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--template',required=True);ap.add_argument('--file',required=True)
    ap.add_argument('--data',required=True);ap.add_argument('--report')
    a=ap.parse_args()
    report=validate(a.template,a.file,json.loads(Path(a.data).read_text(encoding='utf-8')))
    string=json.dumps(report,ensure_ascii=False,indent=2)
    if a.report: Path(a.report).write_text(string+'\n',encoding='utf8')
    print(string)
    if report['result']!='PASS':raise SystemExit(2)
