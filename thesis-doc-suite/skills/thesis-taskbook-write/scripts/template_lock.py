"""Protect the official blank DOCX from silent template swapping."""
import hashlib,json
from pathlib import Path
from docx import Document
HERE=Path(__file__).resolve().parent.parent
LOCK=HERE/'assets/template-lock.json'

def verify(template,lock=LOCK):
    template=Path(template);config=json.loads(Path(lock).read_text(encoding='utf8'))
    actual=hashlib.sha256(template.read_bytes()).hexdigest()
    if actual!=config['sha256']:
        raise ValueError(f'官方模板 SHA-256 不匹配，拒绝套用原 9×4 单元格映射：{actual}；先重新审计/适配新官方模板。')
    d=Document(template)
    if len(d.tables)!=config['table_count'] or len(d.tables[0].rows)!=config['rows'] or len(d.tables[0].columns)!=config['cols']:
        raise ValueError('官方模板结构与锁定版本不一致，停止填充。')
    return actual
