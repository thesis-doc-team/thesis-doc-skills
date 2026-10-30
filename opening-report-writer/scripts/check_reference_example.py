#!/usr/bin/env python3
"""Static privacy/role check of the packaged anonymized writing reference."""
from pathlib import Path
import hashlib
import json
import re
import sys
from zipfile import ZipFile
from lxml import etree
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'assets'/'reference-samples'/'sample-a-smart-interaction-anonymized.docx'
OFFICIAL=ROOT/'assets'/'official-opening-report-template.docx'
EXAMPLE_HASH=ROOT/'assets'/'reference-samples'/'SAMPLE-A.sha256'
HASH=ROOT/'assets'/'template.sha256'
COVER_FIELDS=('学生姓名','学号','学院','专业','班级','指导教师','职称')

def check():
    failures=[]
    if not EXAMPLE.exists(): return ['缺少匿名参考范本']
    if not OFFICIAL.exists(): return ['缺少官方空白模板']
    sha=hashlib.sha256(OFFICIAL.read_bytes()).hexdigest()
    if sha!=HASH.read_text(encoding='utf-8').strip(): failures.append('官方空白模板哈希发生变化')
    if EXAMPLE.read_bytes()==OFFICIAL.read_bytes(): failures.append('参考范本与官方模板被错误混用')
    manifest=json.loads((ROOT/'assets'/'reference-samples'/'samples-manifest.json').read_text(encoding='utf-8'))
    entries=manifest.get('samples',[])
    if len(entries)!=1 or entries[0].get('file')!=EXAMPLE.name or entries[0].get('sha256')!=hashlib.sha256(EXAMPLE.read_bytes()).hexdigest():
        failures.append('脱敏样本清单不匹配')
    lock=json.loads((ROOT/'assets'/'template-lock.json').read_text(encoding='utf-8'))
    if lock.get('sha256')!=sha or lock.get('bytes')!=OFFICIAL.stat().st_size:
        failures.append('官方模板锁文件不匹配')
    if not EXAMPLE_HASH.exists() or hashlib.sha256(EXAMPLE.read_bytes()).hexdigest()!=EXAMPLE_HASH.read_text(encoding='utf-8').strip(): failures.append('脱敏参考范本哈希不匹配')
    with ZipFile(EXAMPLE) as z:
        texts=[]
        for n in z.namelist():
            if n.endswith(('.xml','.rels')):
                texts.append(z.read(n).decode('utf-8','ignore'))
        xml='\n'.join(texts)
    if re.search(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}', xml):
        failures.append('范本中残留电子邮箱格式')
    d=Document(EXAMPLE)
    content='\n'.join([p.text for p in d.paragraphs]+[p.text for t in d.tables for c in t.rows[0].cells for p in c.paragraphs])
    if '【脱敏写作范本' not in content: failures.append('缺少参考样本警告标记')
    if not len(d.tables)==1 or not len(d.tables[0].rows)==2: failures.append('匿名范本结构不符合源样本章节容器')
    for key in COVER_FIELDS:
        candidates=[p.text.replace(' ','') for p in d.paragraphs if p.text.replace(' ','').startswith(key+'：')]
        if not candidates or '（已匿名）' not in candidates[0]:
            failures.append('封面身份字段未脱敏：'+key)
    if d.core_properties.author != '匿名写作示例':
        failures.append('作者元数据未脱敏')
    if d.core_properties.last_modified_by != 'opening-report-writer':
        failures.append('最后编辑人元数据未脱敏')
    if re.search(r'(?<!\d)(?:1[3-9]\d{9}|\d{17}[\dXx])(?!\d)',content):
        failures.append('疑似手机号码或身份号码未脱敏')
    if '7 参考文献' not in content and '7 主要参考文献' not in content: failures.append('范本尾部参考文献章节丢失')
    return failures

if __name__=='__main__':
    problems=check()
    print(json.dumps({'status':'PASS' if not problems else 'FAIL','issues':problems},ensure_ascii=False,indent=2))
    sys.exit(0 if not problems else 1)
