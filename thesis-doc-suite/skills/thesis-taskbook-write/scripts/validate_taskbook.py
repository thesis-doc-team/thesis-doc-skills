#!/usr/bin/env python3
"""结构比对＋内容门禁。视觉/WPS 仍需渲染与人工核查；本脚本不会宣称已经 WPS 实测。"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse
import json
import re
from pathlib import Path
from lxml import etree
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


def canon(node):
    return etree.tostring(node, method='c14n') if node is not None else None


def compare_structure(src, out):
    errors = []
    if len(src.sections) != len(out.sections):
        errors.append('分节数量改变')
    if len(src.tables) != len(out.tables):
        errors.append('表格数量改变')
        return errors
    if canon(src._element.body.sectPr) != canon(out._element.body.sectPr):
        errors.append('节设置 / 页边距 / 页码相关属性发生改变')
    for i, (a, b) in enumerate(zip(src.tables, out.tables)):
        if len(a.rows) != len(b.rows) or len(a.columns) != len(b.columns):
            errors.append(f'表 {i} 行列数改变')
            continue
        if canon(a._tbl.tblPr) != canon(b._tbl.tblPr):
            errors.append(f'表 {i} tblPr（边框/布局等）改变')
        if canon(a._tbl.tblGrid) != canon(b._tbl.tblGrid):
            errors.append(f'表 {i} tblGrid 列宽改变')
        for ri in range(len(a.rows)):
            ar, br = a.rows[ri], b.rows[ri]
            if canon(ar._tr.trPr) != canon(br._tr.trPr):
                errors.append(f'表 {i} 行 {ri} 行高等属性改变')
            for ci in range(len(ar.cells)):
                if ci > 0 and ar.cells[ci]._tc is ar.cells[ci - 1]._tc:
                    continue
                if canon(ar.cells[ci]._tc.tcPr) != canon(br.cells[ci]._tc.tcPr):
                    errors.append(f'表 {i} 行 {ri} 单元格 {ci} 属性（合并/内边距/对齐等）改变')
    if [p.text for p in src.paragraphs] != [p.text for p in out.paragraphs]:
        errors.append('表格外官方标题/附注发生改变')
    # 所有固定栏目文字不得篡改
    expected = [(0, 0), (0, 2), (1, 0), (1, 2),
                (2, 0), (3, 0), (4, 0), (4, 2)]
    for ri, ci in expected:
        if src.tables[0].cell(ri, ci).text != out.tables[0].cell(ri, ci).text:
            errors.append(f'首页固定标签 {ri}:{ci} 发生改变')
    for ri, fixed in [(5, ['毕业论文（设计）内容：']),
                      (6, ['拟定工作进度：', '主要参考文献：']),
                      (7, ['任务下达人意见：', '任务下达人签名']),
                      (8, ['任务接受人意见：', '任务接收人签名'])]:
        after = out.tables[0].cell(ri, 0).text.replace(' ', '')
        for label in fixed:
            if label.replace(' ', '') not in after:
                errors.append(f'固定栏目 {ri} 被删除/改写：{label}')
    for ri in (7, 8):
        for p in src.tables[0].cell(ri, 0).paragraphs:
            if '签名' in p.text or ('年' in p.text and '月' in p.text and '日' in p.text):
                if p.text not in [q.text for q in out.tables[0].cell(ri, 0).paragraphs]:
                    errors.append(f'表 {ri} 官方签名/日期原句被修改：{p.text}')
    return errors


def check_content(doc, data=None):
    errors, warnings = [], []
    if not doc.tables:
        return ['任务书无表格'], warnings
    t = doc.tables[0]
    main = t.cell(5, 0).text
    mixed = t.cell(6, 0).text
    issuer = t.cell(7, 0).text
    if len(main) <= 30:
        errors.append('毕业设计内容明显为空')
    refps = [p.text.strip() for p in t.cell(6, 0).paragraphs if re.match(r'^\[\d+\]', p.text.strip())]
    if len(refps) < 10:
        errors.append(f'参考文献仅 {len(refps)} 条（要求不少于 10）')
    if [int(re.match(r'^\[(\d+)\]', r).group(1)) for r in refps] != list(range(1, len(refps)+1)):
        errors.append('参考文献序号未连续')
    p = next((p for p in t.cell(7, 0).paragraphs if p.text.strip().startswith('任务下达人意见：')), None)
    sig = next((p for p in t.cell(7, 0).paragraphs if p.text.strip().startswith('任务下达人签名')), None)
    ps = t.cell(7, 0).paragraphs
    if p is None or sig is None:
        errors.append('任务下达人意见或签名标题缺失')
    else:
        from_i = next(i for i, q in enumerate(ps) if q._p is p._p)
        to_i = next(i for i, q in enumerate(ps) if q._p is sig._p)
        op = ''.join(q.text for q in ps[from_i+1:to_i])
        if len(re.sub(r'\s+', '', op)) < 50:
            errors.append('任务下达人意见不足 50 字')
        if any(h in op for h in ('本栏为拟稿','供教师审定拟稿','供指导教师审定','教师审定为准')) or re.search(r'审定.{0,2}为准',str(op)):
            errors.append('任务下达人意见含拟稿提示语/元话语尾巴（本栏为拟稿/供教师审定拟稿/供指导教师审定/教师审定为准，含“审定结果为准”等插字变体），应以实质收束句自然结束')
        bad_font = False
        for q in ps[from_i+1:to_i]:
            for r_ in q.runs:
                if any('一' <= ch <= '鿿' for ch in r_.text):
                    rf_ = r_._element.get_or_add_rPr().find(qn('w:rFonts'))
                    if rf_ is None or rf_.get(qn('w:eastAsia')) != '宋体':
                        bad_font = True
        if bad_font:
            errors.append('任务下达人意见含非宋体汉字：汉字官方字体为宋体（除非明确要求），skill 写入必须显式设置 eastAsia=宋体')
    for ri in range(5):
        for ci in range(4):
            cell = t.cell(ri, ci)
            if ci > 0 and cell._tc is t.cell(ri, ci - 1)._tc:
                continue
            if cell.vertical_alignment != WD_CELL_VERTICAL_ALIGNMENT.CENTER:
                errors.append(f'首页单元格 {ri}:{ci} 不是垂直居中')
            if any(p.alignment != WD_ALIGN_PARAGRAPH.CENTER for p in cell.paragraphs):
                errors.append(f'首页单元格 {ri}:{ci} 不是水平居中')
    if '年' in t.cell(3, 1).text and not re.search(r'\d{4}', t.cell(3, 1).text):
        warnings.append('起止日期尚未填写，保留官方占位文本')
    if data:
        actual = [s for s in t.cell(6, 0).paragraphs if re.match(r'^第\s*\d+', s.text)]
        if len(actual) != len(data.get('schedule', [])):
            errors.append('计划进度条目数量与输入不一致')
        if data.get('references') and len(refps) != len(data['references']):
            errors.append('写入参考文献数量与输入不一致')
        for i, r in enumerate(data.get('references', [])):
            if not r.get('verified') or not r.get('source_url'):
                errors.append(f'文献 [{i+1}] 缺核验记录')
        if not data.get('start_date') or not data.get('end_date'):
            warnings.append('输入未提供起止时间；不得套用历史范本年份')
    warnings.append('仅检查 DOCX 结构和文本；视觉分页与 WPS 客户端显示须另外核查')
    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', type=Path, required=True)
    ap.add_argument('--file', type=Path, required=True)
    ap.add_argument('--data', type=Path)
    ap.add_argument('--report', type=Path)
    args = ap.parse_args()
    from template_lock import verify as verify_template_lock
    verify_template_lock(args.template)
    original, output = Document(args.template), Document(args.file)
    data = json.loads(args.data.read_text(encoding='utf-8')) if args.data else None
    se = compare_structure(original, output)
    ce, warns = check_content(output, data)
    res = {'status': 'FAIL' if se or ce else ('WARN' if warns else 'PASS'),
           'structure_errors': se, 'content_errors': ce, 'warnings': warns,
           'visual_render_checked': False, 'wps_checked': False}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if se or ce:
        raise SystemExit(2)

if __name__ == '__main__':
    main()
