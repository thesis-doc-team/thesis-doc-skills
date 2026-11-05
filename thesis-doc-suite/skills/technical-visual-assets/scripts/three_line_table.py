#!/usr/bin/env python3
"""Enforce and audit native 3-line Word tables in selected, generated data tables.

Does not change original thesis templates or blindly reformat their fixed form tables.
Use indices (1-based) to distinguish generated data tables from protected form grids.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH

SIDES = ('top', 'bottom', 'left', 'right', 'insideH', 'insideV', 'start', 'end')
NO_BORDER = ('nil','none')


def border_container(parent, name):
    found = parent.find(qn('w:' + name))
    if found is None:
        found = OxmlElement('w:' + name)
        parent.append(found)
    return found


def set_border(borders, side, val, size=None):
    tag = qn('w:' + side)
    el = borders.find(tag)
    if el is None:
        el = OxmlElement('w:' + side)
        borders.append(el)
    el.set(qn('w:val'), val)
    for key in ('sz', 'color', 'space'):
        attr=qn('w:' + key)
        if attr in el.attrib: del el.attrib[attr]
    if val == 'single':
        el.set(qn('w:sz'), str(size))
        el.set(qn('w:color'), '000000')
    return el


def is_merged(table):
    for row in table.rows:
        for cell in row.cells:
            tcpr=cell._tc.tcPr
            if tcpr is None:continue
            if tcpr.find(qn('w:gridSpan')) is not None or tcpr.find(qn('w:vMerge')) is not None:
                return True
    return False


def center_table_cells(table):
    """All header/data cells: horizontal + vertical centre (hard requirement)."""
    for row in table.rows:
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for para in cell.paragraphs:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER


def apply_three_line(table):
    """One top rule, one below header, one bottom; never vertical or inner-row rules."""
    if len(table.rows)<2 or len(table.columns)<1:
        raise ValueError('必须至少有表头和一行数据')
    if is_merged(table):
        raise ValueError('合并单元格表格需人工规划，不能无损自动设三线表')
    center_table_cells(table)
    tblpr=table._tbl.tblPr
    tb=border_container(tblpr, 'tblBorders')
    for side in SIDES: set_border(tb,side,'nil')
    last=len(table.rows)-1
    for i,row in enumerate(table.rows):
        if i==0:
            trpr=row._tr.get_or_add_trPr()
            if trpr.find(qn('w:tblHeader')) is None:
                trpr.append(OxmlElement('w:tblHeader'))
        for cell in row.cells:
            cb=border_container(cell._tc.get_or_add_tcPr(),'tcBorders')
            for side in SIDES:
                if side == 'top' and i==0:
                    set_border(cb,side,'single',10)  # 1.25pt
                elif side == 'bottom' and i==0:
                    set_border(cb,side,'single',6)   # 0.75pt
                elif side == 'bottom' and i==last:
                    set_border(cb,side,'single',10)  # 1.25pt
                else:
                    set_border(cb,side,'nil')


def value_for(cell, side):
    tcpr=cell._tc.tcPr
    if tcpr is None:return None
    borders=tcpr.find(qn('w:tcBorders'))
    if borders is None:return None
    x=borders.find(qn('w:' + side))
    return x.get(qn('w:val')) if x is not None else None


def audit_three_line(table):
    problems=[]
    if len(table.rows)<2:problems.append('必须有表头及数据行')
    if is_merged(table):problems.append('合并单元格结构不能自动确认三线表')
    for i,row in enumerate(table.rows):
        for j,cell in enumerate(row.cells):
            for side in SIDES:
                expected = ('single' if (side=='top' and i==0) or
                            (side=='bottom' and i in (0,len(table.rows)-1)) else 'nil')
                val=value_for(cell,side)
                if expected == 'single' and val != 'single':
                    problems.append(f'行{i+1}列{j+1}: {side} 缺少规定横线')
                if expected == 'nil' and val not in NO_BORDER:
                    problems.append(f'行{i+1}列{j+1}: {side} 不是明确禁用的边框({val})')
    tb=table._tbl.tblPr.find(qn('w:tblBorders'))
    for side in SIDES:
        x=tb.find(qn('w:'+side)) if tb is not None else None
        val=x.get(qn('w:val')) if x is not None else None
        if val not in NO_BORDER:problems.append(f'表级边框 {side} 未禁用({val})，存在继承网格线风险')
    # v1.4.1 hard requirement: every header/data cell is horizontally and
    # vertically centred.  Missing alignment is BLOCK, not a warning.
    for i,row in enumerate(table.rows):
        for j,cell in enumerate(row.cells):
            if cell.vertical_alignment != WD_CELL_VERTICAL_ALIGNMENT.CENTER:
                problems.append(f'行{i+1}列{j+1}: 单元格未垂直居中')
            for k,para in enumerate(cell.paragraphs):
                if para.alignment != WD_ALIGN_PARAGRAPH.CENTER:
                    problems.append(f'行{i+1}列{j+1}段{k+1}: 文字未水平居中')
    return {'status':'PASS' if not problems else 'BLOCK',
            'rows':len(table.rows),'columns':len(table.columns),
            'rule_count':3 if not problems else None,
            'alignment_centered': all(cell.vertical_alignment == WD_CELL_VERTICAL_ALIGNMENT.CENTER
                                      and all(p.alignment == WD_ALIGN_PARAGRAPH.CENTER
                                              for p in cell.paragraphs)
                                      for row in table.rows for cell in row.cells),
            'problems':problems}


def table_indices(arg, count):
    if not arg:
        raise ValueError('必须显式提供 --indices，例如 --indices 1 或 --indices 1,3，防止破坏官方固定表单')
    vals=[]
    for word in arg.split(','):
        index=int(word)
        if not 1 <= index <= count:raise ValueError('表格序号超出范围 (1-based): '+word)
        if index in vals:raise ValueError('重复表格序号: '+word)
        vals.append(index)
    return vals


def main():
    ap=argparse.ArgumentParser(description='三线表硬门禁：仅选中生成的数据表；官方固定表单禁止改动')
    ap.add_argument('mode',choices=['apply','audit'])
    ap.add_argument('--docx',required=True)
    ap.add_argument('--indices',required=True,help='1-based 表格序号，如 1,3')
    ap.add_argument('--out',help='apply 模式输出DOCX路径，不覆盖源文件')
    ap.add_argument('--json',help='审计报告JSON输出路径')
    args=ap.parse_args()
    try:
        source=Path(args.docx).resolve(strict=True)
        d=Document(str(source)); indices=table_indices(args.indices,len(d.tables))
        if args.mode=='apply':
            if not args.out:raise ValueError('apply 必须指定 --out，避免覆盖原模板')
            output=Path(args.out).resolve()
            if output==source:raise ValueError('不得覆盖原DOCX/官方模板')
            for number in indices: apply_three_line(d.tables[number-1])
            output.parent.mkdir(parents=True,exist_ok=True)
            d.save(str(output))
            d=Document(str(output))
        results=[{'table_index':i,**audit_three_line(d.tables[i-1])} for i in indices]
        status='PASS' if all(x['status']=='PASS' for x in results) else 'BLOCK'
        report={'status':status,'docx':str(Path(args.out).resolve() if args.mode=='apply' else source),
                'checked_indices':indices,'tables':results,
                'note':'只检验三线表边框的OOXML规则；字体、版心、分页、Word/WPS可视排版仍须单独验收'}
        if args.json:
            dest=Path(args.json);dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if status=='PASS' else 2
    except (OSError,ValueError,IndexError) as exc:
        print(json.dumps({'status':'BLOCK','error':str(exc)},ensure_ascii=False))
        return 2
if __name__=='__main__':raise SystemExit(main())
