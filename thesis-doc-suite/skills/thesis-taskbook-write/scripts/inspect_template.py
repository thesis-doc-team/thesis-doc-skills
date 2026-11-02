#!/usr/bin/env python3
"""只读分析用户指定的任务书 DOCX；不修改原件。"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse
import hashlib
import json
from pathlib import Path
from docx import Document


def analyze(path: Path):
    doc = Document(path)
    items = []
    for k, tab in enumerate(doc.tables):
        rows = []
        for i, row in enumerate(tab.rows):
            cells = []
            for j, cell in enumerate(row.cells):
                merged = j > 0 and cell._tc is row.cells[j - 1]._tc
                cells.append({
                    'col': j, 'same_as_previous': merged,
                    'text': '' if merged else cell.text[:130],
                    'vertical_alignment': str(cell.vertical_alignment),
                    'horizontal_alignments': [] if merged else [str(p.alignment) for p in cell.paragraphs[:2]],
                })
            rows.append({'row': i, 'height_cm': round(row.height.cm, 3) if row.height else None,
                         'height_rule': str(row.height_rule), 'cells': cells})
        items.append({'index': k, 'row_count': len(tab.rows), 'col_count': len(tab.columns), 'rows': rows})
    s = doc.sections[0]
    return {
        'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'page_cm': [round(s.page_width.cm, 3), round(s.page_height.cm, 3)],
        'margins_cm': {'top': round(s.top_margin.cm, 3), 'bottom': round(s.bottom_margin.cm, 3),
                       'left': round(s.left_margin.cm, 3), 'right': round(s.right_margin.cm, 3)},
        'sections': len(doc.sections), 'tables': items,
        'outside_table': [p.text for p in doc.paragraphs]
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('template', type=Path)
    p.add_argument('--json', type=Path)
    args = p.parse_args()
    info = analyze(args.template)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
