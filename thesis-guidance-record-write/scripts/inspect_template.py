
import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
from docx import Document

p=argparse.ArgumentParser();p.add_argument('file');p.add_argument('--json');a=p.parse_args()
path=Path(a.file);d=Document(path)
report={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'sections':len(d.sections),'tables':[{'rows':len(t.rows),'columns':len(t.columns),
        'physical_cells_per_row':[len(r._tr.tc_lst) for r in t.rows]} for t in d.tables],
        'page':'A4','notes':'只读结构审计；新版需重建字段定位锁而非强制运行旧脚本'}
print(json.dumps(report,ensure_ascii=False,indent=2))
if a.json:Path(a.json).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
