"""Locked official DOCX guard. A changed university template requires a new mapping and tests."""
from pathlib import Path
import hashlib,json
from docx import Document

ROOT=Path(__file__).resolve().parent.parent
LOCK=ROOT/'assets/template-lock.json'
TEMPLATE=ROOT/'assets/official-literature-review-template.docx'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require_official_template(path, lock_path=LOCK):
    lock=json.loads(Path(lock_path).read_text(encoding='utf-8'))
    sha=digest(path)
    if sha != lock['sha256']:
        raise ValueError('模板 SHA256 与本 Skill 已审计的官方原件不一致。禁止套用旧坐标；请先审计新模板并更新位置映射、锁和测试。实际 '+sha)
    doc=Document(path)
    if (len(doc.sections),len(doc.paragraphs),len(doc.tables)) != (lock['section_count'],lock['document_paragraphs'],lock['table_count']):
        raise ValueError('官方模板的章节/封面段落/表格数量不匹配')
    table=doc.tables[0]
    if len(table.rows)!=lock['table_rows'] or len(table.columns)!=lock['table_grid_columns']:
        raise ValueError('官方模板正文表格结构不匹配')
    for s in lock['fixed_instruction_contains']:
        if s not in table.cell(0,0).paragraphs[0].text:
            raise ValueError('官方固定排版要求被更改: '+s)
    if lock['teacher_label_contains'] not in table.cell(1,0).paragraphs[0].text:
        raise ValueError('官方审阅区标签不匹配')
    return doc,lock
