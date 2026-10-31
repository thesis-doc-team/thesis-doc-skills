#!/usr/bin/env python3
"""Structural/fixed-label QA (visual render review is an additional mandatory gate)."""
import argparse, json, hashlib, re
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]

def norm(s):return re.sub(r'\s+','',s or '')
def serialized(obj):return etree.tostring(obj)

def main():
    p=argparse.ArgumentParser();p.add_argument('--template',required=True);p.add_argument('--file',required=True)
    p.add_argument('--data',required=True);p.add_argument('--report',required=True);a=p.parse_args()
    lock=json.loads((ROOT/'assets/template-lock.json').read_text(encoding='utf-8'))
    errs=[];warnings=[]
    template=Path(a.template);out=Path(a.file)
    if hashlib.sha256(template.read_bytes()).hexdigest()!=lock['sha256']:
        errs.append('源官方模板SHA-256不匹配')
    src=Document(template);d=Document(out);data=json.loads(Path(a.data).read_text(encoding='utf-8'))
    n=len(data.get('records',[]));expected=max(8,n)
    if len(d.tables)!=2:errs.append('非原有2表：说明/指导记录表层次被改动')
    if len(d.sections)!=len(src.sections): errs.append('节数被改变')
    for i,(x,y) in enumerate(zip(src.sections,d.sections)):
        for field in ('page_width','page_height','top_margin','bottom_margin','left_margin','right_margin','header_distance','footer_distance'):
            if getattr(x,field)!=getattr(y,field):errs.append(f'节{i}的{field}变化')
    if len(d.tables)==2:
        s=src.tables[1];t=d.tables[1]
        if len(t.rows)!=13*n:errs.append('指导记录区不是13行/次')
        if len(t.columns)!=len(s.columns):errs.append('原表11逻辑列被改动')
        for k in range(len(t.rows)):
            model=s.rows[k%26] if k<26 else s.rows[k%13]
            actual=t.rows[k]
            if serialized(model._tr.trPr)!=serialized(actual._tr.trPr): errs.append(f'第{k}行trPr变化')
            if len(model._tr.tc_lst)!=len(actual._tr.tc_lst): errs.append(f'第{k}行合并/物理单元格数变化')
            for j,(old,new) in enumerate(zip(model._tr.tc_lst, actual._tr.tc_lst)):
                if serialized(old.tcPr)!=serialized(new.tcPr):errs.append(f'第{k}行第{j}格tcPr变化')
            # All fixed cell texts are identical. Only editable (name/id/grade/title/date/place/content) differ.
            editable={0:{2,5,10},1:{2},2:{3,9},5:{1}}
            for col in range(len(t.columns)):
                if any(actual.cells[col]._tc is actual.cells[ec]._tc for ec in editable.get(k%13,set())):continue
                if norm(actual.cells[col].text)!=norm(model.cells[col].text):
                    errs.append(f'第{k}行第{col}逻辑格官方固定文字被改动')
        if serialized(s._tbl.tblPr)!=serialized(t._tbl.tblPr):errs.append('官方tblPr被改动')
        if serialized(s._tbl.tblGrid)!=serialized(t._tbl.tblGrid):errs.append('官方tblGrid被改动')
        for i,rec in enumerate(data['records']):
            base=13*i
            body=t.cell(base+5,1).text
            if '指导教师指出存在问题：' not in body or '指导教师提出修改意见：' not in body:
                errs.append(f'第{i+1}次缺少两组标签')
            if '分条列出。如' in body or 'XX' in body:errs.append(f'第{i+1}次留下官方示例占位')
            pairs=rec['issue_pairs']; half=body.split('指导教师提出修改意见：')
            left=half[0].replace('指导教师指出存在问题：','');right=half[1] if len(half)>1 else ''
            for m in range(1,len(pairs)+1):
                if not re.search(rf'(?:^|\n){m}\.\s*',left) or not re.search(rf'(?:^|\n){m}\.\s*',right):
                    errs.append(f'第{i+1}次第{m}组问题/修改意见没有对应独立编号')
            for j,par in enumerate(t.cell(base+5,1).paragraphs[:2*len(pairs)+2]):
                if par.paragraph_format.first_line_indent is None:
                    errs.append(f'第{i+1}次第{j+1}段未设置首行缩进')
            for r in (base+3,base+7,base+9,base+11,base+12):
                # method, evaluation and signature/date unchanged
                for col in range(len(t.columns)):
                    if norm(t.cell(r,col).text)!=norm(s.rows[(r%13)].cells[col].text):
                        errs.append(f'第{i+1}次评价/签名内容变化')
    for i,(x,y) in enumerate(zip(src.paragraphs,d.paragraphs)):
        if i not in (13,15,17,19,21,23,25,27) and norm(x.text)!=norm(y.text):
            errs.append(f'封面/填写说明固定段落{i}内容被改动')
    # No fake meetings or signature dates should be generated.
    if any(rec.get('date') and not rec.get('date_verified') for rec in data['records']):errs.append('有未核实指导日期')
    if any(rec.get('location') and not rec.get('location_verified') for rec in data['records']):errs.append('有未核实地点')
    if len(data['records'])<8:errs.append('指导次数不足8次')
    report={'result':'PASS' if not errs else 'FAIL','records':n,'errors':list(dict.fromkeys(errs)),
            'warnings':warnings,'input_template_sha256':lock['sha256'],
            'visual_inspection_required':True}
    Path(a.report).parent.mkdir(parents=True,exist_ok=True)
    Path(a.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(report['result'],f'records={n}, errors={len(errs)}')
    if errs:
        print('\n'.join(report['errors'][:20]));raise SystemExit(1)

if __name__=='__main__':main()
