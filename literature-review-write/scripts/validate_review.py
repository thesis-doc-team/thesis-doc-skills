#!/usr/bin/env python3
"""Fail-closed Word validation: locked official framework, typography, true citation superscripts.
Static checks cannot replace visual inspection of all rendered pages.
"""
import argparse,hashlib,json,re
from pathlib import Path
from lxml import etree
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from template_tools import require_official_template

MARK=re.compile(r'\[(\d+(?:[,，\-–]\d+)*)\]')
REFLINE=re.compile(r'^\[(\d+)\]')
COVER_CHANGE={12,13,14,16,18,20,22,24,26}

def xml(x):
    return etree.tostring(x,method='c14n') if x is not None else b''

def ids_in_marker(txt):
    txt=txt.strip('[]').replace('，',',').replace('–','-')
    result=[]
    for part in txt.split(','):
        if '-' in part:
            a,b=map(int,part.split('-',1))
            if b<a or b-a>50:raise ValueError('引文区间格式异常: '+txt)
            result.extend(range(a,b+1))
        else:result.append(int(part))
    return result

def validate(template, docx, data):
    t,lock=require_official_template(template)
    d=Document(docx)
    issues=[]
    def check(ok,msg):
        if not ok:issues.append(msg)
    check(len(d.sections)==len(t.sections),'分节数量改变')
    check(len(d.paragraphs)==len(t.paragraphs),'模板封面段落数量改变')
    check(len(d.tables)==len(t.tables),'模板表格数量改变')
    for i in range(min(len(t.sections),len(d.sections))):
        check(xml(t.sections[i]._sectPr)==xml(d.sections[i]._sectPr),f'第{i+1}节的官方页面/页码/页眉页脚设置改变')
    for i,(before,after) in enumerate(zip(t.paragraphs,d.paragraphs)):
        if i not in COVER_CHANGE:check(xml(before._p)==xml(after._p),f'封面固定段落第{i}段被修改')
        elif i in (12,14,16,18,20,22,24,26):
            # original label must remain identical, only its value and tabs can change
            if before.runs and after.runs:
                check(xml(before.runs[0]._r)==xml(after.runs[0]._r),f'封面第{i}段固定标签/字体被更改')
    if d.tables and t.tables:
        a,b=t.tables[0],d.tables[0]
        check(len(a.rows)==len(b.rows) and len(a.columns)==len(b.columns),'表格行列变化')
        check(xml(a._tbl.tblPr)==xml(b._tbl.tblPr),'官方表格属性被更改')
        check(xml(a._tbl.tblGrid)==xml(b._tbl.tblGrid),'官方表格网格被更改')
        for i in range(min(len(a.rows),len(b.rows))):
            check(xml(a.rows[i]._tr.trPr)==xml(b.rows[i]._tr.trPr),f'官方表格行{i}结构改变')
            check(xml(a.cell(i,0)._tc.tcPr)==xml(b.cell(i,0)._tc.tcPr),f'官方表格单元格{i}结构改变')
        tc0,dc0=a.cell(0,0),b.cell(0,0)
        tc1,dc1=a.cell(1,0),b.cell(1,0)
        check(xml(tc0.paragraphs[0]._p)==xml(dc0.paragraphs[0]._p),'官方正文填写说明发生变化')
        check(xml(tc1.paragraphs[0]._p)==xml(dc1.paragraphs[0]._p),'官方指导教师审阅栏固定标题发生变化')
        for name in ('指导教师（签字）',):
            old=[p for p in tc1.paragraphs if name in p.text]
            new=[p for p in dc1.paragraphs if name in p.text]
            check(len(old)==1 and len(new)==1 and xml(old[0]._p)==xml(new[0]._p),'官方教师签名段落/格式改变')
        old=[p for p in tc1.paragraphs if '年' in p.text and '月' in p.text and '日' in p.text]
        new=[p for p in dc1.paragraphs if '年' in p.text and '月' in p.text and '日' in p.text]
        check(len(old)==1 and len(new)==1 and xml(old[0]._p)==xml(new[0]._p),'官方年月日位置或格式改变')
        body=dc0.paragraphs[1:]
        rhead=next((i for i,p in enumerate(body) if p.text.strip()=='4 参考文献'),None)
        check(rhead is not None,'缺少第4章参考文献')
        counts={'narrative_chars':0,'intext_citations':0,'references':0,'section_count':0,'superscript_errors':0}
        if rhead is not None:
            writing=body[:rhead];bib=body[rhead+1:]
            counts['narrative_chars']=sum(len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',MARK.sub('',p.text))) for p in writing)
            check(counts['narrative_chars']>=2500,'有效正文字符不足2500（不计标点和引用编号）')
            titles=[p.text.strip() for p in writing if re.match(r'^[1-3]\s+',p.text.strip())]
            # deliberately use simple numbered chapter titles, not arbitrary heading parsing
            check(len(titles)==3,'第1/2/3主章缺失或重复')
            for h in range(1,4):check(any(x.startswith(str(h)+' ') for x in titles),f'主章 {h} 缺失')
            ordered=[]
            for p in writing:
                check(p.paragraph_format.line_spacing==1.5,f'正文行距不是1.5倍: {p.text[:20]}')
                for run in p.runs:
                    if not run.text.strip():continue
                    check(run.font.size==Pt(10.5),f'正文 run 字号不是五号: {p.text[:18]}')
                    props=run._r.rPr
                    fonts=props.rFonts if props is not None else None
                    check(fonts is not None and fonts.get(qn('w:eastAsia'))=='宋体' and fonts.get(qn('w:ascii'))=='Times New Roman',f'正文中西文字体不符合要求: {p.text[:18]}')
                    for mark in MARK.finditer(run.text):
                        ordered.extend(ids_in_marker(mark.group()))
                        counts['intext_citations']+=1
                        if run.font.superscript is not True:
                            counts['superscript_errors']+=1
                            issues.append(f'正文引用不是真正Word上标: {mark.group()}')
                # concatenated marker across multiple runs is not allowed
                matches=MARK.findall(p.text)
                count_in_runs=sum(len(MARK.findall(run.text)) for run in p.runs)
                check(len(matches)==count_in_runs,f'存在跨 run 引用标记，无法验证上标: {p.text[:30]}')
            check(bool(ordered),'正文未发现引用')
            nums=[]
            for j,p in enumerate(bib):
                m=REFLINE.match(p.text.strip())
                if not m:
                    issues.append(f'文后文献表混入非条目文字：{p.text[:30]}');continue
                nums.append(int(m.group(1)))
                check(p.paragraph_format.line_spacing==1.5,'文后书目行距不是1.5倍')
                for r in p.runs:check(r.font.superscript is not True,'参考文献条目错误地设为上标')
                if j<len(data.get('bibliography',[])):
                    item=data['bibliography'][j]
                    check(p.text==f'[{item["number"]}] {item["citation"]}',f'参考文献第{j+1}项与注册文献不一致')
            check(nums==list(range(1,len(nums)+1)),'参考文献编号不连续')
            check(len(nums)==len(data.get('bibliography',[])),'参考文献数与输入清单不一致')
            check(set(ordered)==set(nums),'正文引用与文末条目集合不一致')
            first=[]
            for n in ordered:
                if n not in first:first.append(n)
            check(first==list(range(1,len(nums)+1)),'参考文献编号不是正文首次出现的顺序')
            counts['references']=len(nums)
            counts['section_count']=len(titles)
        opinion=data.get('teacher_opinion','')
        check(opinion in dc1.text,'指导教师评语内容缺失')
        check(len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',opinion))>=50,'指导教师拟稿少于50字')
        check(len([p for p in dc1.paragraphs if p.text==opinion])==1,'教师评语应为独立一个自然段')
    else:counts={}
    check(Path(docx).resolve()!=Path(template).resolve(),'禁止直接覆盖官方模板')
    check('Error! Reference source not found' not in '\n'.join(p.text for p in d.paragraphs),'出现失效交叉引用错误')
    return {'result':'PASS' if not issues else 'FAIL','issues':issues,
            'template_sha256':hashlib.sha256(Path(template).read_bytes()).hexdigest(),
            'output_sha256':hashlib.sha256(Path(docx).read_bytes()).hexdigest(),**counts}

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--template',required=True);ap.add_argument('--file',required=True)
    ap.add_argument('--data',required=True);ap.add_argument('--report')
    a=ap.parse_args()
    try:result=validate(a.template,a.file,json.loads(Path(a.data).read_text(encoding='utf-8')))
    except Exception as exc:raise SystemExit(f'ERROR: {exc}')
    output=json.dumps(result,ensure_ascii=False,indent=2)
    if a.report:Path(a.report).write_text(output+'\n',encoding='utf-8')
    print(output)
    if result['result']!='PASS':raise SystemExit(2)
