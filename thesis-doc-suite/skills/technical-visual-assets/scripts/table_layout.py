#!/usr/bin/env python3
"""A4-native Word table layout planner based on Markdown table data, stdlib only.
No row deletion, truncated content, converted-to-image or re-fabricated values.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from a4_layout import inspect_template


def parse_md_table(content):
    lines=[x.strip() for x in content.splitlines() if x.strip()]
    if len(lines)<3 or '|' not in lines[0]:raise ValueError('没有有效的 Markdown 表格')
    def cells(line):return [x.strip().replace('\\|','|') for x in line.strip().strip('|').split('|')]
    header=cells(lines[0]); divider=cells(lines[1]); data=[cells(x) for x in lines[2:]]
    if len(divider)!=len(header) or any(not re.fullmatch(r':?-{3,}:?',x) for x in divider):
        raise ValueError('第二行不是标准 Markdown 表格分隔行')
    if any(len(row)!=len(header) for row in data):raise ValueError('存在单元格列数不一致，不能静默丢字段')
    return [header]+data


def units(cell):
    return max([sum(1.8 if ord(x)>255 else 1 for x in line) for line in cell.splitlines()]+[0])


def plan(rows,section):
    n=len(rows[0]);maxw=section['table_max_width_mm']
    # Minimum 14mm per column including cell margins; real Word can require more
    # depending on the approved thesis template's font, indent and cell padding.
    if n>12 or n*14>maxw:
        return {'status':'NEEDS_TABLE_SPLIT','reason':'A4版心无法容纳全部列的最小清晰宽度',
                'recommendation':'纵向分组拆分列，重复关键字段列，保留所有数据与表题，不得截图压缩'}
    raw=[max(units(r[j]) for r in rows) for j in range(n)]
    natural=[max(16,min(55,8+v*1.7)) for v in raw]
    total=sum(natural)
    width=[round(max(14,x/total*maxw),2) for x in natural]
    # Allocate available width while maintaining min width; do not exceed the page.
    while sum(width)>maxw+0.02:
        reducible=[i for i,x in enumerate(width) if x>14.01]
        if not reducible:break
        step=(sum(width)-maxw)/len(reducible)
        for i in reducible:width[i]=round(max(14,width[i]-max(step,0.02)),2)
    if sum(width)>maxw+0.5:
        return {'status':'NEEDS_TABLE_SPLIT','reason':'表格宽度无法合理压缩',
                'recommendation':'拆分列并重复关键列，保留全部单元格内容'}
    # Estimated row height not trustworthy; Word/WPS pagination is mandatory.
    return {'status':'PLAN_READY_NEEDS_WORD_RENDER',
            'content_width_mm':maxw,'columns':n,'rows_including_header':len(rows),
            'proposed_column_widths_mm':width,
            'table_width_mm':round(sum(width),2),
            'rules':['使用Word原生表格，不把数据表渲染成图片','文字至少9pt，允许换行但禁止挤压/截断',
              '严格三线表：仅表顶/表头下/表底三条横线，禁用所有竖线和内部数据行横线；表头重复','表题在表外，表格与表题不得跨页分离',
              '内容密集时按语义拆分表格而不是强制缩成一页','每张新生成数据表必须运行 three_line_table.py audit 并取得 PASS','最终必须在Word/WPS逐页审查']}


def main():
    ap=argparse.ArgumentParser(description='根据真实官方DOCX版心规划Markdown转Word原生表格')
    ap.add_argument('--table-md',required=True);ap.add_argument('--template',required=True)
    ap.add_argument('--section',type=int,default=1)
    args=ap.parse_args()
    try:
        section=inspect_template(args.template)['sections'][args.section-1]
        rows=parse_md_table(Path(args.table_md).read_text('utf-8'))
        result=plan(rows,section)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['status']=='PLAN_READY_NEEDS_WORD_RENDER' else 2
    except (OSError,ValueError,IndexError) as ex:
        print(json.dumps({'status':'BLOCK','error':str(ex)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
