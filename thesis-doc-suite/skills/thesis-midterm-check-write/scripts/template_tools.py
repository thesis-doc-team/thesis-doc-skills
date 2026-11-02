"""Exact-template guard and repeatable structural audits for the bundled midterm form."""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
from pathlib import Path
import hashlib
import json
import re
from docx import Document
from lxml import etree

HERE = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = HERE/'assets'/'official-midterm-template.docx'
DEFAULT_LOCK = HERE/'assets'/'template-lock.json'

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def lock_check(template, lock_path=DEFAULT_LOCK):
    lock = json.loads(Path(lock_path).read_text(encoding='utf-8'))
    actual = sha256(template)
    if actual != lock['sha256']:
        raise ValueError(f'当前官方模板与已审计模板不一致：{actual}。不得以旧坐标自动灌入；先分析新模板并重新生成锁定映射。')
    doc = Document(template)
    if len(doc.tables) != 1 or len(doc.tables[0].rows) != 6 or len(doc.tables[0].columns) != 4:
        raise ValueError('官方模板表格结构不符，停止填充')
    labels = ['学生姓名','班    级','毕业论文（设计）题目',
              '完成进度：','存在的问题及整改措施：','指导教师意见：','学院意见：']
    alltext=' '.join([p.text for p in doc.paragraphs]+[c.text for r in doc.tables[0].rows for c in r.cells])
    if not all(x in alltext for x in labels):
        raise ValueError('官方栏目固定标签缺失，拒绝写入')
    return doc, lock

def unique_cells(row):
    res=[]
    for cell in row.cells:
        if all(cell._tc is not old._tc for old in res):
            res.append(cell)
    return res

def para_xml_props(p):
    return etree.tostring(p._p.pPr, method='c14n') if p._p.pPr is not None else None

def count_content_chars(block):
    if isinstance(block,list):
        block=''.join(block)
    # 字数核验忽略空白、标点和常见格式分隔符；中英文及数字有效信息计数。
    return sum(bool(re.match(r'[\u4e00-\u9fffA-Za-z0-9]',ch)) for ch in block)
