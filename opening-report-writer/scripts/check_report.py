#!/usr/bin/env python3
"""Structural QA for official-template-filled opening report (no actual research claims)."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from build_report import TEMPLATE, SHA_FILE, N, Q, DEFAULT_TITLES, text_of, normalize_label, COVER_KEYS


def err(errors,msg): errors.append(msg)


def xml_bytes(elem):
    return etree.tostring(elem, method='c14n')


def check(original, target, data):
    errors=[]; warnings=[]; metrics={}
    expected=SHA_FILE.read_text(encoding='utf-8').strip()
    if hashlib.sha256(original.read_bytes()).hexdigest()!=expected:
        err(errors,'官方模板哈希不匹配，原件可能被更换或修改')
    with ZipFile(original) as za, ZipFile(target) as zb:
        if set(za.namelist())!=set(zb.namelist()):
            err(errors,'DOCX ZIP 部件清单发生改变')
        for name in set(za.namelist()) & set(zb.namelist()):
            if name!='word/document.xml' and za.read(name)!=zb.read(name):
                err(errors, '非允许部件被修改: '+name)
        a=etree.fromstring(za.read('word/document.xml'))
        b=etree.fromstring(zb.read('word/document.xml'))
    ap=a.xpath('./w:body',namespaces=N)[0];bp=b.xpath('./w:body',namespaces=N)[0]
    atab=ap.xpath('./w:tbl',namespaces=N)[0];btab=bp.xpath('./w:tbl',namespaces=N)[0]
    for tag in ['tblPr','tblGrid']:
        ax=atab.find(Q(tag)); bx=btab.find(Q(tag))
        if (ax is None)!=(bx is None) or (ax is not None and xml_bytes(ax)!=xml_bytes(bx)):
            err(errors, f'官方表格结构发生变动：{tag}')
    ar=atab.xpath('./w:tr',namespaces=N);br=btab.xpath('./w:tr',namespaces=N)
    if len(ar)!=2 or len(br)!=2: err(errors,'正文表格必须保持原来的两行结构')
    elif xml_bytes(ar[1])!=xml_bytes(br[1]):
        err(errors,'指导教师意见及签名区域与官方模板不一致')
    for e1,e2 in zip(ap.xpath('./w:sectPr',namespaces=N), bp.xpath('./w:sectPr',namespaces=N)):
        if xml_bytes(e1)!=xml_bytes(e2): err(errors,'页面与节属性被改变')
    aps=ap.xpath('./w:p',namespaces=N);bps=bp.xpath('./w:p',namespaces=N)
    if len(aps)!=len(bps):err(errors,'官方封面/说明段落数量发生变化')
    for i,(p,q) in enumerate(zip(aps,bps)):
        x,y=text_of(p),text_of(q)
        label=normalize_label(x.split('：',1)[0]) if '：' in x else ''
        if label in COVER_KEYS:
            xr=p.xpath('./w:r[1]',namespaces=N);yr=q.xpath('./w:r[1]',namespaces=N)
            if len(xr)!=len(yr) or any(xml_bytes(z)!=xml_bytes(v) for z,v in zip(xr,yr)):
                err(errors,'封面栏目名被改动: '+label)
            if xml_bytes(p.find(Q('pPr')))!=xml_bytes(q.find(Q('pPr'))):
                err(errors,'封面栏位版式被改动: '+label)
        elif xml_bytes(p)!=xml_bytes(q):
            err(errors,f'封面/填写说明固定文本或属性被修改（段落 {i}）')
    if len(ar)==2 and len(br)==2:
        aa=ar[0].xpath('./w:tc/w:p',namespaces=N)
        bb=br[0].xpath('./w:tc/w:p',namespaces=N)
        ax=[x for x in aa if text_of(x).startswith('学生签名')]
        bx=[x for x in bb if text_of(x).startswith('学生签名')]
        if len(ax)!=1 or len(bx)!=1:err(errors,'学生签名位置丢失')
        else:
            orig_sig=aa.index(ax[0]);new_sig=bb.index(bx[0]);metrics['generated_paragraphs']=new_sig-1
            if xml_bytes(aa[0])!=xml_bytes(bb[0]):err(errors,'正文格式提示固定文本被修改')
            if len(aa)-orig_sig!=len(bb)-new_sig:
                err(errors,'学生签名后固定段落被修改')
            else:
                for k in range(len(aa)-orig_sig):
                    if xml_bytes(aa[orig_sig+k])!=xml_bytes(bb[new_sig+k]):
                        err(errors,'学生签字与日期格式被修改')
            generated=bb[1:new_sig]
            text='\n'.join(text_of(p) for p in generated)
            headings=[text_of(p) for p in generated if re.match(r'^\d+\s+',text_of(p))]
            expected_heading=[f'{i} {sec.get("title", DEFAULT_TITLES[i-1])}' for i,sec in enumerate(data['sections'],1)]
            if headings!=expected_heading:
                err(errors,f'七个一级章节不匹配：{headings}')
            refs=[p for p in generated if re.match(r'^\[\d+\]\s',text_of(p))]
            ids=[int(re.match(r'^\[(\d+)\]',text_of(p)).group(1)) for p in refs]
            if ids!=list(range(1,len(data['references'])+1)):
                err(errors,'参考文献编号不连续/重复/数量不符')
            metrics['references']=len(refs)
            for p in refs:
                jc=p.xpath('./w:pPr/w:jc',namespaces=N)
                if len(jc)!=1 or jc[0].get(Q('val'))!='left':
                    err(errors,'参考文献段落必须显式左对齐（w:jc=left），防止两端对齐拉伸出行内大空隙：'+text_of(p)[:30])
                indent=p.xpath('./w:pPr/w:ind',namespaces=N)
                if len(indent)!=1 or indent[0].get(Q('left'))!='420' or indent[0].get(Q('hanging'))!='420':
                    err(errors,'参考文献悬挂缩进不符：'+text_of(p)[:30])
                if p.xpath('./w:pPr/w:numPr',namespaces=N):
                    err(errors,'文献不允许额外启用自动列表编号，避免重复 [n] [n]')
            if re.search(r'\[\d+\]\s*\[\d+\]',text):
                err(errors,'参考文献或正文中出现重复 [n] [n] 编号')
            for p in generated:
                spacing=p.xpath('./w:pPr/w:spacing',namespaces=N)
                if len(spacing)!=1 or spacing[0].get(Q('line'))!='360' or spacing[0].get(Q('lineRule'))!='auto':
                    err(errors,'生成内容未统一为 1.5 倍行距：'+text_of(p)[:30])
                # 参考中期检查 Skill v1.3 的经验：正文必须逐段检查显式缩进，
                # 不能只检查 run 字体就把正文顶格误判为合格。
                val=text_of(p)
                if p not in refs and not re.match(r'^\d+(?:\.\d+)*\s+',val):
                    ind=p.xpath('./w:pPr/w:ind',namespaces=N)
                    if len(ind)!=1 or ind[0].get(Q('firstLine'))!='420':
                        err(errors,'普通正文/周计划首行缩进应为 420 twips（21pt，约两字）：'+val[:30])
                for r in p.xpath('./w:r',namespaces=N):
                    fonts=r.xpath('./w:rPr/w:rFonts',namespaces=N)
                    sz=r.xpath('./w:rPr/w:sz',namespaces=N)
                    if not fonts or fonts[0].get(Q('eastAsia'))!='宋体' or fonts[0].get(Q('ascii'))!='Times New Roman' or not sz or sz[0].get(Q('val'))!='21':
                        err(errors,'正文新写入字符字体或五号字号错误：'+text_of(p)[:30])
            refs_ids=set(ids); cite_occ=[]
            for p in generated:
                if p in refs: continue
                for r in p.xpath('./w:r',namespaces=N):
                    s=text_of(r)
                    if re.fullmatch(r'\[[\d,\-]+\]',s):
                        va=r.xpath('./w:rPr/w:vertAlign',namespaces=N)
                        if len(va)!=1 or va[0].get(Q('val'))!='superscript':
                            err(errors,'正文引用没有真正的 Word superscript 属性：'+s)
                        for tok in s.strip('[]').split(','):
                            if '-' in tok:
                                st,en=map(int,tok.split('-'));cite_occ+=list(range(st,en+1))
                            else: cite_occ.append(int(tok))
                    elif re.search(r'\[\d+\]',s):
                        err(errors,'发现疑似普通基线正文引用：'+s[:40])
                if re.search(r'第\d+周[～〜~—–]第\d+周',text_of(p)):
                    err(errors,'计划周次连接符不符合 -- 规定')
            missing=set(cite_occ)-refs_ids
            if missing:err(errors,'正文引文在文末找不到对应条目: '+str(missing))
            metrics['superscript_citations']=len([x for x in cite_occ])
            body_only=''.join(text_of(p) for p in generated if p not in refs and not re.match(r'^\d+\s+',text_of(p)))
            num_zh=len(re.findall(r'[\u4e00-\u9fff]',body_only))
            metrics['chinese_characters_excluding_bibliography']=num_zh
            if num_zh<3000:err(errors,f'正文汉字数不足 3000：目前 {num_zh}')
            if re.search(r'\[\[cite:|【待填写】|\{\{',text):err(errors,'成品残留内部引用语法或占位符')
            if len(refs)<10:err(errors,'参考文献少于 10 条')
            if not re.search('指导教师审阅意见',text_of(br[1])):
                err(errors,'教师审阅意见区域丢失')
    if not data.get('cover',{}).get('student_name'):
        warnings.append('封面学生信息保留空白；用户需手动填写，不可自行臆造。')
    warnings.append('机器结构检查不能代替 Word/WPS 全页渲染目视检查及文献真实性核验。')
    return {'status':'FAIL' if errors else 'PASS','errors':errors,'warnings':warnings,'metrics':metrics}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('file',type=Path)
    ap.add_argument('--json',required=True,type=Path)
    ap.add_argument('--template',type=Path,default=TEMPLATE)
    ap.add_argument('--output-report',type=Path)
    args=ap.parse_args()
    try:
        data=json.loads(args.json.read_text(encoding='utf-8'))
        report=check(args.template,args.file,data)
        if args.output_report:
            args.output_report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        sys.exit(0 if report['status']=='PASS' else 1)
    except Exception as exc:
        print('FAIL: '+str(exc),file=sys.stderr);sys.exit(2)

if __name__=='__main__':main()
