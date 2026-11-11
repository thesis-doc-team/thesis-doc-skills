#!/usr/bin/env python3
"""DOCX 格式全景只读解析（仅标准库）。

直接读取 OOXML 包内 document.xml / styles.xml / numbering.xml / theme1.xml /
header*.xml / footer*.xml，输出结构化 JSON：

- doc_defaults / styles / theme / numbering 的原始定义
- 每个段落、run 的 direct（直接格式）、style_chain（继承链）与 effective（有效值）
- 页面设置、页眉页脚、表格、图片尺寸与哈希

只读：不修改原文件，不写项目资产。

Usage:
  python inspect_docx.py <file.docx> [--json <out.json>]
Exit code: 0 = OK; 2 = 文件/结构错误。
"""
import sys as _sys
if hasattr(_sys.stdout, 'reconfigure'):
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(_sys.stderr, 'reconfigure'):
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
}
SCHEMA = 'docx-format-audit/1'
STYLE_REF_KEYS = ('style_id', 'style_name')


def qn(prefix, tag):
    return '{%s}%s' % (NS[prefix], tag)


def get(el, attr, prefix='w'):
    return None if el is None else el.get(qn(prefix, attr))


def child(el, tag, prefix='w'):
    return None if el is None else el.find(qn(prefix, tag))


def children(el, tag, prefix='w'):
    return [] if el is None else el.findall(qn(prefix, tag))


def on_off(el):
    if el is None:
        return None
    value = get(el, 'val')
    if value is None:
        return True
    return value not in ('0', 'false', 'off', 'none')


def int_attr(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def twips_to_pt(value):
    return None if value is None else round(value / 20.0, 3)


def half_points_to_pt(value):
    return None if value is None else round(value / 2.0, 3)


def twips_to_cm(value):
    return None if value is None else round(value / 1440.0 * 2.54, 3)


def emu_to_cm(value):
    return None if value is None else round(value / 360000.0, 3)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def image_pixels(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        width, height = struct.unpack('>II', data[16:24])
        return [width, height]
    if data[:6] in (b'GIF87a', b'GIF89a') and len(data) >= 10:
        width, height = struct.unpack('<HH', data[6:10])
        return [width, height]
    if data[:2] == b'\xff\xd8':
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height, width = struct.unpack('>HH', data[index + 5:index + 9])
                return [width, height]
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            length = struct.unpack('>H', data[index + 2:index + 4])[0]
            index += 2 + length
    return None


# ---------------------------------------------------------------- rPr / pPr

def parse_fonts(el):
    if el is None:
        return {}
    out = {}
    for attr, key in (
        ('ascii', 'font_ascii'), ('hAnsi', 'font_hansi'), ('eastAsia', 'font_east_asia'),
        ('cs', 'font_cs'), ('asciiTheme', 'font_ascii_theme'), ('hAnsiTheme', 'font_hansi_theme'),
        ('eastAsiaTheme', 'font_east_asia_theme'), ('cstheme', 'font_cs_theme'), ('hint', 'font_hint'),
    ):
        value = get(el, attr)
        if value is not None:
            out[key] = value
    return out


def parse_run_props(rpr):
    if rpr is None:
        return {}
    out = {}
    style = child(rpr, 'rStyle')
    if style is not None and get(style, 'val'):
        out['style_id'] = get(style, 'val')
    out.update(parse_fonts(child(rpr, 'rFonts')))
    size = child(rpr, 'sz')
    if size is not None and int_attr(get(size, 'val')) is not None:
        out['font_size_pt'] = half_points_to_pt(int_attr(get(size, 'val')))
    csize = child(rpr, 'szCs')
    if csize is not None and int_attr(get(csize, 'val')) is not None:
        out['font_size_cs_pt'] = half_points_to_pt(int_attr(get(csize, 'val')))
    for tag, key in (
        ('b', 'bold'), ('i', 'italic'), ('strike', 'strike'), ('dstrike', 'double_strike'),
        ('caps', 'caps'), ('smallCaps', 'small_caps'), ('vanish', 'hidden'),
        ('outline', 'outline'), ('shadow', 'shadow'), ('emboss', 'emboss'), ('imprint', 'imprint'),
        ('noProof', 'no_proof'),
    ):
        value = on_off(child(rpr, tag))
        if value is not None:
            out[key] = value
    underline = child(rpr, 'u')
    if underline is not None:
        out['underline'] = get(underline, 'val') or 'single'
        color = get(underline, 'color')
        if color:
            out['underline_color'] = color
    color = child(rpr, 'color')
    if color is not None:
        if get(color, 'val'):
            out['color'] = get(color, 'val')
        if get(color, 'themeColor'):
            out['color_theme'] = get(color, 'themeColor')
        if get(color, 'themeTint'):
            out['color_theme_tint'] = get(color, 'themeTint')
        if get(color, 'themeShade'):
            out['color_theme_shade'] = get(color, 'themeShade')
    highlight = child(rpr, 'highlight')
    if highlight is not None and get(highlight, 'val'):
        out['highlight'] = get(highlight, 'val')
    vertical = child(rpr, 'vertAlign')
    if vertical is not None and get(vertical, 'val'):
        out['vert_align'] = get(vertical, 'val')
    spacing = child(rpr, 'spacing')
    if spacing is not None and int_attr(get(spacing, 'val')) is not None:
        out['char_spacing_pt'] = twips_to_pt(int_attr(get(spacing, 'val')))
    kern = child(rpr, 'kern')
    if kern is not None and int_attr(get(kern, 'val')) is not None:
        out['kerning_pt'] = half_points_to_pt(int_attr(get(kern, 'val')))
    position = child(rpr, 'position')
    if position is not None and int_attr(get(position, 'val')) is not None:
        out['position_pt'] = half_points_to_pt(int_attr(get(position, 'val')))
    scale = child(rpr, 'w')
    if scale is not None and int_attr(get(scale, 'val')) is not None:
        out['width_scale_percent'] = int_attr(get(scale, 'val')) / 100.0
    lang = child(rpr, 'lang')
    if lang is not None:
        values = {key: get(lang, attr) for attr, key in
                  (('val', 'latin'), ('eastAsia', 'east_asia'), ('bidi', 'bidi')) if get(lang, attr)}
        if values:
            out['lang'] = values
    return out


def parse_indent(el):
    if el is None:
        return None
    pairs = (
        ('left', 'left_pt'), ('start', 'left_pt'), ('right', 'right_pt'), ('end', 'right_pt'),
        ('firstLine', 'first_line_pt'), ('hanging', 'hanging_pt'),
    )
    out = {}
    for attr, key in pairs:
        value = int_attr(get(el, attr))
        if value is not None:
            out[key] = twips_to_pt(value)
    for attr, key in (
        ('leftChars', 'left_chars'), ('startChars', 'left_chars'), ('rightChars', 'right_chars'),
        ('endChars', 'right_chars'), ('firstLineChars', 'first_line_chars'),
        ('hangingChars', 'hanging_chars'),
    ):
        value = int_attr(get(el, attr))
        if value is not None:
            out[key] = round(value / 100.0, 3)
    return out or None


def parse_borders(el):
    out = {}
    if el is None:
        return None
    for tag in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV', 'start', 'end'):
        side = child(el, tag)
        if side is None:
            continue
        out[tag] = {
            'val': get(side, 'val'),
            'size_pt': half_points_to_pt(int_attr(get(side, 'sz'))) if get(side, 'sz') else None,
            'color': get(side, 'color'),
            'space_pt': twips_to_pt(int_attr(get(side, 'space'))) if get(side, 'space') else None,
        }
    return out or None


def parse_paragraph_props(ppr):
    if ppr is None:
        return {}
    out = {}
    style = child(ppr, 'pStyle')
    if style is not None and get(style, 'val'):
        out['style_id'] = get(style, 'val')
    for tag, key in (
        ('keepNext', 'keep_next'), ('keepLines', 'keep_lines'), ('pageBreakBefore', 'page_break_before'),
        ('widowControl', 'widow_control'), ('bidi', 'bidi'), ('snapToGrid', 'snap_to_grid'),
        ('contextualSpacing', 'contextual_spacing'), ('suppressAutoHyphens', 'suppress_auto_hyphens'),
        ('mirrorIndents', 'mirror_indents'), ('autoSpaceDE', 'auto_space_de'),
        ('autoSpaceDN', 'auto_space_dn'), ('wordWrap', 'word_wrap'),
    ):
        value = on_off(child(ppr, tag))
        if value is not None:
            out[key] = value
    num_pr = child(ppr, 'numPr')
    if num_pr is not None:
        numbering = {}
        ilvl = child(num_pr, 'ilvl')
        num_id = child(num_pr, 'numId')
        if ilvl is not None and get(ilvl, 'val') is not None:
            numbering['level'] = int_attr(get(ilvl, 'val'))
        if num_id is not None and get(num_id, 'val') is not None:
            numbering['num_id'] = int_attr(get(num_id, 'val'))
        if numbering:
            out['numbering'] = numbering
    spacing = child(ppr, 'spacing')
    if spacing is not None:
        for attr, key in (('before', 'spacing_before_pt'), ('after', 'spacing_after_pt')):
            value = int_attr(get(spacing, attr))
            if value is not None:
                out[key] = twips_to_pt(value)
        for attr, key in (('beforeLines', 'spacing_before_lines'), ('afterLines', 'spacing_after_lines')):
            value = int_attr(get(spacing, attr))
            if value is not None:
                out[key] = round(value / 100.0, 3)
        line = int_attr(get(spacing, 'line'))
        if line is not None:
            rule = get(spacing, 'lineRule') or 'auto'
            if rule == 'auto':
                out['line_spacing'] = {'rule': 'auto', 'multiple': round(line / 240.0, 4)}
            else:
                out['line_spacing'] = {'rule': rule, 'pt': twips_to_pt(line)}
    indent = parse_indent(child(ppr, 'ind'))
    if indent:
        out['indent'] = indent
    alignment = child(ppr, 'jc')
    if alignment is not None and get(alignment, 'val'):
        out['alignment'] = get(alignment, 'val')
    outline = child(ppr, 'outlineLvl')
    if outline is not None and get(outline, 'val') is not None:
        out['outline_level'] = int_attr(get(outline, 'val'))
    shading = child(ppr, 'shd')
    if shading is not None:
        out['shading'] = {key: get(shading, attr) for attr, key in
                          (('val', 'pattern'), ('fill', 'fill'), ('color', 'color')) if get(shading, attr)}
    borders = parse_borders(child(ppr, 'pBdr'))
    if borders:
        out['borders'] = borders
    tabs = child(ppr, 'tabs')
    if tabs is not None:
        items = []
        for tab in children(tabs, 'tab'):
            items.append({
                'type': get(tab, 'val'),
                'position_pt': twips_to_pt(int_attr(get(tab, 'pos'))) if get(tab, 'pos') else None,
                'leader': get(tab, 'leader'),
            })
        if items:
            out['tabs'] = items
    text_alignment = child(ppr, 'textAlignment')
    if text_alignment is not None and get(text_alignment, 'val'):
        out['text_alignment'] = get(text_alignment, 'val')
    mark = parse_run_props(child(ppr, 'rPr'))
    if mark:
        out['paragraph_mark'] = mark
    return out


# ---------------------------------------------------------------- merge

def merge(base, override, deep_keys=('indent', 'lang')):
    out = dict(base or {})
    for key, value in (override or {}).items():
        if key in STYLE_REF_KEYS:
            continue
        if key in deep_keys and isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def merge_all(*parts):
    out = {}
    for part in parts:
        out = merge(out, part)
    return out


# ---------------------------------------------------------------- package

def read_xml(archive, part):
    try:
        data = archive.read(part)
    except KeyError:
        return None
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f'{part} XML 解析失败：{exc}')


def parse_relationships(archive, part):
    root = read_xml(archive, part)
    if root is None:
        return {}
    base = part.rsplit('/_rels/', 1)[0] if '/_rels/' in part else ''
    out = {}
    for rel in root.findall(qn('rel', 'Relationship')):
        target = rel.get('Target') or ''
        resolved = target.lstrip('/') if target.startswith('/') else _join(base, target)
        out[rel.get('Id')] = {
            'type': (rel.get('Type') or '').rsplit('/', 1)[-1],
            'target': resolved,
            'external': rel.get('TargetMode') == 'External',
        }
    return out


def _join(base, target):
    parts = base.split('/') if base else []
    for piece in target.split('/'):
        if piece in ('', '.'):
            continue
        if piece == '..':
            if parts:
                parts.pop()
        else:
            parts.append(piece)
    return '/'.join(parts)


def parse_theme(archive):
    root = read_xml(archive, 'word/theme/theme1.xml')
    if root is None:
        return None
    result = {'fonts': {}, 'colors': {}}
    scheme = root.find('.//' + qn('a', 'fontScheme'))
    if scheme is not None:
        result['name'] = scheme.get('name')
        for slot, tag in (('major', 'majorFont'), ('minor', 'minorFont')):
            node = scheme.find(qn('a', tag))
            if node is None:
                continue
            entry = {}
            for key, font_tag in (('latin', 'latin'), ('ea', 'ea'), ('cs', 'cs')):
                font = node.find(qn('a', font_tag))
                if font is not None and font.get('typeface'):
                    entry[key] = font.get('typeface')
            result['fonts'][slot] = entry
    colors = root.find('.//' + qn('a', 'clrScheme'))
    if colors is not None:
        for node in list(colors):
            name = node.tag.rsplit('}', 1)[-1]
            value = None
            for child_node in list(node):
                value = child_node.get('val') or child_node.get('lastClr')
                if value:
                    break
            if value:
                result['colors'][name] = value
    return result


def parse_styles(archive):
    root = read_xml(archive, 'word/styles.xml')
    data = {'paragraph': {}, 'run': {}, 'default_paragraph_id': None, 'default_character_id': None, 'styles': []}
    if root is None:
        return data
    defaults = child(root, 'docDefaults')
    if defaults is not None:
        ppr_default = child(defaults, 'pPrDefault')
        rpr_default = child(defaults, 'rPrDefault')
        data['paragraph'] = parse_paragraph_props(child(ppr_default, 'pPr'))
        data['run'] = parse_run_props(child(rpr_default, 'rPr'))
    ids = {}
    for style in children(root, 'style'):
        style_id = get(style, 'styleId') or ''
        name_node = child(style, 'name')
        based_on = child(style, 'basedOn')
        next_style = child(style, 'next')
        entry = {
            'style_id': style_id,
            'type': get(style, 'type') or 'paragraph',
            'name': get(name_node, 'val') if name_node is not None else style_id,
            'based_on': get(based_on, 'val') if based_on is not None else None,
            'next': get(next_style, 'val') if next_style is not None else None,
            'default': get(style, 'default') in ('1', 'true', 'on'),
            'q_format': child(style, 'qFormat') is not None,
        }
        if get(style, 'default') in ('1', 'true', 'on'):
            if entry['type'] == 'paragraph':
                data['default_paragraph_id'] = style_id
            elif entry['type'] == 'character':
                data['default_character_id'] = style_id
        paragraph = parse_paragraph_props(child(style, 'pPr'))
        run = parse_run_props(child(style, 'rPr'))
        if paragraph:
            entry['paragraph'] = paragraph
        if run:
            entry['run'] = run
        data['styles'].append(entry)
        ids[style_id] = entry
    data['by_id'] = ids
    return data


def parse_numbering(archive):
    root = read_xml(archive, 'word/numbering.xml')
    if root is None:
        return None
    result = {'abstract_numbers': [], 'instances': []}
    for abstract in children(root, 'abstractNum'):
        entry = {'abstract_num_id': int_attr(get(abstract, 'abstractNumId')), 'levels': []}
        if get(abstract, 'multiLevelType'):
            entry['multi_level_type'] = get(abstract, 'multiLevelType')
        for level in children(abstract, 'lvl'):
            item = {
                'level': int_attr(get(level, 'ilvl')),
                'num_format': get(child(level, 'numFmt'), 'val'),
                'text': get(child(level, 'lvlText'), 'val'),
                'start': int_attr(get(child(level, 'start'), 'val')),
                'suffix': get(child(level, 'suff'), 'val'),
                'justification': get(child(level, 'lvlJc'), 'val'),
                'style_id': get(child(level, 'pStyle'), 'val'),
            }
            indent = parse_indent(child(child(level, 'pPr'), 'ind'))
            if indent:
                item['indent'] = indent
            run = parse_run_props(child(level, 'rPr'))
            if run:
                item['run'] = run
            entry['levels'].append({key: value for key, value in item.items() if value is not None})
        result['abstract_numbers'].append(entry)
    for num in children(root, 'num'):
        entry = {'num_id': int_attr(get(num, 'numId')),
                 'abstract_num_id': int_attr(get(child(num, 'abstractNumId'), 'val'))}
        overrides = []
        for override in children(num, 'lvlOverride'):
            item = {'level': int_attr(get(override, 'ilvl'))}
            start = child(override, 'startOverride')
            if start is not None:
                item['start'] = int_attr(get(start, 'val'))
            level = child(override, 'lvl')
            if level is not None:
                item['num_format'] = get(child(level, 'numFmt'), 'val')
                item['text'] = get(child(level, 'lvlText'), 'val')
            overrides.append(item)
        if overrides:
            entry['overrides'] = overrides
        result['instances'].append(entry)
    return result


def parse_section(sect_pr, rels):
    if sect_pr is None:
        return None
    out = {}
    size = child(sect_pr, 'pgSz')
    if size is not None:
        out['page_size_cm'] = {
            'width': twips_to_cm(int_attr(get(size, 'w'))),
            'height': twips_to_cm(int_attr(get(size, 'h'))),
        }
        out['orientation'] = get(size, 'orient') or 'portrait'
    margin = child(sect_pr, 'pgMar')
    if margin is not None:
        out['margins_cm'] = {
            key: twips_to_cm(int_attr(get(margin, attr)))
            for attr, key in (('top', 'top'), ('bottom', 'bottom'), ('left', 'left'),
                              ('right', 'right'), ('header', 'header'), ('footer', 'footer'),
                              ('gutter', 'gutter'))
        }
    cols = child(sect_pr, 'cols')
    if cols is not None:
        out['columns'] = {
            'count': int_attr(get(cols, 'num')) or 1,
            'space_cm': twips_to_cm(int_attr(get(cols, 'space'))),
            'separator': on_off(child(cols, 'sep')) or False,
        }
    title = on_off(child(sect_pr, 'titlePg'))
    if title is not None:
        out['title_page'] = title
    v_align = child(sect_pr, 'vAlign')
    if v_align is not None and get(v_align, 'val'):
        out['vertical_alignment'] = get(v_align, 'val')
    grid = child(sect_pr, 'docGrid')
    if grid is not None:
        out['doc_grid'] = {key: get(grid, attr) for attr, key in
                           (('type', 'type'), ('linePitch', 'line_pitch'), ('charSpace', 'char_space'))
                           if get(grid, attr)}
    for reference_tag, key in (('headerReference', 'headers'), ('footerReference', 'footers')):
        refs = []
        for ref in children(sect_pr, reference_tag):
            rel = rels.get(get(ref, 'id', 'r'), {})
            refs.append({'type': get(ref, 'type') or 'default', 'part': rel.get('target')})
        if refs:
            out[key] = refs
    return out


# ---------------------------------------------------------------- content

class Inspector:
    def __init__(self, archive, path):
        self.archive = archive
        self.path = path
        self.styles = parse_styles(archive)
        self.theme = parse_theme(archive)
        self.rels = parse_relationships(archive, 'word/_rels/document.xml.rels')
        self.warnings = []

    def style_name(self, style_id):
        entry = self.styles.get('by_id', {}).get(style_id)
        return entry['name'] if entry else style_id

    def style_chain(self, style_id, style_type='paragraph'):
        chain = []
        seen = set()
        current = style_id
        while current and current not in seen:
            seen.add(current)
            entry = self.styles.get('by_id', {}).get(current)
            if entry is None:
                break
            chain.append(entry)
            current = entry.get('based_on')
        chain.reverse()
        if not chain and style_type == 'paragraph':
            default_id = self.styles.get('default_paragraph_id')
            if default_id and default_id != style_id:
                return self.style_chain(default_id, style_type)
        return chain

    def theme_font(self, theme_ref, key):
        if not theme_ref or not self.theme:
            return None
        slot = 'major' if theme_ref.startswith('major') else 'minor'
        fonts = self.theme.get('fonts', {}).get(slot, {})
        if key == 'ea' or theme_ref.endswith('EastAsia'):
            return fonts.get('ea')
        if theme_ref.endswith('Bidi') or theme_ref.endswith('cs'):
            return fonts.get('cs')
        return fonts.get('latin')

    def resolve_theme(self, fmt):
        if not fmt:
            return fmt
        pairs = (
            ('font_ascii_theme', 'font_ascii_resolved', 'latin'),
            ('font_hansi_theme', 'font_hansi_resolved', 'latin'),
            ('font_east_asia_theme', 'font_east_asia_resolved', 'ea'),
            ('font_cs_theme', 'font_cs_resolved', 'cs'),
        )
        for ref_key, out_key, slot in pairs:
            value = self.theme_font(fmt.get(ref_key), slot)
            if value:
                fmt[out_key] = value
        return fmt

    def paragraph_effective(self, style_id, direct_ppr, direct_rpr=None):
        chain = self.style_chain(style_id)
        paragraph = merge(self.styles.get('paragraph'), {})
        run = merge(self.styles.get('run'), {})
        for entry in chain:
            paragraph = merge(paragraph, entry.get('paragraph'))
            run = merge(run, entry.get('run'))
        paragraph = merge(paragraph, direct_ppr)
        run = merge(run, direct_rpr)
        return paragraph, run, chain

    def run_effective(self, paragraph_style_id, direct_rpr):
        chain = self.style_chain(paragraph_style_id)
        run = merge(self.styles.get('run'), {})
        for entry in chain:
            run = merge(run, entry.get('run'))
        run_style = direct_rpr.get('style_id') if direct_rpr else None
        for entry in self.style_chain(run_style, 'character'):
            run = merge(run, entry.get('run'))
        run = merge(run, direct_rpr)
        return self.resolve_theme(run)

    def parse_run(self, run_el, paragraph_style_id):
        direct = parse_run_props(child(run_el, 'rPr'))
        text_parts = []
        kinds = []
        field_code = []
        for node in list(run_el):
            tag = node.tag.rsplit('}', 1)[-1]
            if tag == 't':
                text_parts.append(node.text or '')
            elif tag == 'tab':
                text_parts.append('\t')
                kinds.append('tab')
            elif tag in ('br', 'cr'):
                text_parts.append('\n')
                kinds.append('break')
            elif tag == 'instrText':
                field_code.append(node.text or '')
            elif tag == 'fldChar':
                kinds.append('field_char')
            elif tag == 'drawing':
                kinds.append('drawing')
            elif tag == 'pict':
                kinds.append('legacy_drawing')
            elif tag == 'noBreakHyphen':
                text_parts.append('-')
            elif tag == 'softHyphen':
                text_parts.append('\u00ad')
        run = {
            'text': ''.join(text_parts),
            'style_id': direct.get('style_id'),
            'style_name': self.style_name(direct['style_id']) if direct.get('style_id') else None,
            'direct': {key: value for key, value in direct.items() if key not in STYLE_REF_KEYS},
            'effective': self.run_effective(paragraph_style_id, direct),
        }
        if kinds:
            run['kinds'] = sorted(set(kinds))
        if field_code:
            run['field_code'] = ''.join(field_code)
        return run

    def parse_paragraph(self, paragraph_el, location, index):
        direct_ppr = parse_paragraph_props(child(paragraph_el, 'pPr'))
        style_id = direct_ppr.get('style_id')
        paragraph_fmt, paragraph_run_fmt, chain = self.paragraph_effective(style_id, direct_ppr)
        runs = []
        for node in list(paragraph_el):
            tag = node.tag.rsplit('}', 1)[-1]
            if tag == 'r':
                runs.append(self.parse_run(node, style_id))
            elif tag in ('hyperlink', 'ins', 'del', 'smartTag', 'sdt', 'sdtContent', 'fldSimple', 'moveTo', 'moveFrom'):
                for inner in node.iter(qn('w', 'r')):
                    runs.append(self.parse_run(inner, style_id))
            elif tag == 'oMath':
                runs.append({'text': '', 'kinds': ['math'], 'direct': {}, 'effective': {}})
        effective = self.resolve_theme(merge(paragraph_fmt, paragraph_run_fmt))
        return {
            'index': index,
            'location': location,
            'text': ''.join(run['text'] for run in runs),
            'style_id': style_id,
            'style_name': self.style_name(style_id) if style_id else None,
            'style_chain': [entry['style_id'] for entry in chain],
            'style_chain_names': [entry['name'] for entry in chain],
            'direct': {key: value for key, value in direct_ppr.items() if key not in STYLE_REF_KEYS},
            'effective': effective,
            'runs': runs,
        }

    def parse_table(self, table_el, location, index):
        style_node = child(child(table_el, 'tblPr'), 'tblStyle')
        style_id = get(style_node, 'val') if style_node is not None else None
        grid = [twips_to_cm(int_attr(get(col, 'w'))) for col in children(child(table_el, 'tblGrid'), 'gridCol')]
        tbl_pr = child(table_el, 'tblPr')
        table = {
            'index': index,
            'location': location,
            'style_id': style_id,
            'style_name': self.style_name(style_id) if style_id else None,
            'columns_cm': grid,
            'rows': [],
        }
        if tbl_pr is not None:
            alignment = child(tbl_pr, 'jc')
            if alignment is not None and get(alignment, 'val'):
                table['alignment'] = get(alignment, 'val')
            width = child(tbl_pr, 'tblW')
            if width is not None and get(width, 'w'):
                table['width_cm'] = twips_to_cm(int_attr(get(width, 'w')))
            borders = parse_borders(child(tbl_pr, 'tblBorders'))
            if borders:
                table['borders'] = borders
        for row_index, row in enumerate(children(table_el, 'tr')):
            row_entry = {'index': row_index, 'cells': []}
            tr_pr = child(row, 'trPr')
            if tr_pr is not None:
                height = child(tr_pr, 'trHeight')
                if height is not None:
                    row_entry['height_cm'] = twips_to_cm(int_attr(get(height, 'val')))
                header = on_off(child(tr_pr, 'tblHeader'))
                if header is not None:
                    row_entry['header'] = header
            column = 0
            for cell in children(row, 'tc'):
                tc_pr = child(cell, 'tcPr')
                span = 1
                if tc_pr is not None:
                    span_node = child(tc_pr, 'gridSpan')
                    if span_node is not None:
                        span = int_attr(get(span_node, 'val')) or 1
                cell_paragraphs = []
                nested = []
                for node in list(cell):
                    tag = node.tag.rsplit('}', 1)[-1]
                    if tag == 'p':
                        cell_paragraphs.append(self.parse_paragraph(
                            node, f'{location}/table:{index}/r{row_index}c{column}', len(cell_paragraphs)))
                    elif tag == 'tbl':
                        nested.append(self.parse_table(
                            node, f'{location}/table:{index}/r{row_index}c{column}', len(nested)))
                cell_entry = {
                    'row': row_index,
                    'column': column,
                    'grid_span': span,
                    'paragraphs': cell_paragraphs,
                }
                if tc_pr is not None:
                    merge_node = child(tc_pr, 'vMerge')
                    if merge_node is not None:
                        cell_entry['v_merge'] = get(merge_node, 'val') or 'continue'
                    width = child(tc_pr, 'tcW')
                    if width is not None and get(width, 'w'):
                        cell_entry['width_cm'] = twips_to_cm(int_attr(get(width, 'w')))
                    shading = child(tc_pr, 'shd')
                    if shading is not None and get(shading, 'fill'):
                        cell_entry['shading'] = get(shading, 'fill')
                    vertical = child(tc_pr, 'vAlign')
                    if vertical is not None and get(vertical, 'val'):
                        cell_entry['vertical_alignment'] = get(vertical, 'val')
                if nested:
                    cell_entry['nested_tables'] = nested
                row_entry['cells'].append(cell_entry)
                column += span
            table['rows'].append(row_entry)
        return table

    def collect_blocks(self, container, location, blocks, paragraphs, tables):
        for node in list(container):
            tag = node.tag.rsplit('}', 1)[-1]
            if tag == 'p':
                paragraphs.append(self.parse_paragraph(node, location, len(paragraphs)))
                blocks.append({'kind': 'paragraph', 'ref': len(paragraphs) - 1})
            elif tag == 'tbl':
                tables.append(self.parse_table(node, location, len(tables)))
                blocks.append({'kind': 'table', 'ref': len(tables) - 1})
            elif tag == 'sdt':
                content = child(node, 'sdtContent')
                if content is not None:
                    self.collect_blocks(content, location, blocks, paragraphs, tables)

    def images(self, container, part):
        found = []
        for drawing in container.iter(qn('w', 'drawing')):
            for kind in ('inline', 'anchor'):
                holder = drawing.find(qn('wp', kind))
                if holder is None:
                    continue
                extent = holder.find(qn('wp', 'extent'))
                doc_pr = holder.find(qn('wp', 'docPr'))
                blip = None
                for node in holder.iter(qn('a', 'blip')):
                    blip = node
                    break
                rel_id = blip.get(qn('r', 'embed')) or blip.get(qn('r', 'link')) if blip is not None else None
                relation = self.rels.get(rel_id, {}) if rel_id else {}
                item = {
                    'part': part,
                    'kind': kind,
                    'relationship_id': rel_id,
                    'target': relation.get('target'),
                    'name': doc_pr.get('name') if doc_pr is not None else None,
                    'description': doc_pr.get('descr') if doc_pr is not None else None,
                    'width_cm': emu_to_cm(int_attr(extent.get('cx'))) if extent is not None else None,
                    'height_cm': emu_to_cm(int_attr(extent.get('cy'))) if extent is not None else None,
                }
                target = relation.get('target')
                if target and not relation.get('external'):
                    try:
                        data = self.archive.read(target)
                        item['size_bytes'] = len(data)
                        item['sha256'] = sha256_bytes(data)
                        pixels = image_pixels(data)
                        if pixels:
                            item['pixel_size'] = pixels
                    except KeyError:
                        self.warnings.append(f'图片关系目标缺失：{target}')
                found.append({key: value for key, value in item.items() if value is not None})
        return found


def inspect_docx(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'文件不存在：{path}')
    data = path.read_bytes()
    try:
        archive = ZipFile(path)
    except BadZipFile as exc:
        raise ValueError(f'不是有效的 DOCX/ZIP 包：{exc}')
    with archive:
        names = set(archive.namelist())
        if 'word/document.xml' not in names:
            raise ValueError('缺少 word/document.xml，不是 Word 文档')
        inspector = Inspector(archive, path)
        root = read_xml(archive, 'word/document.xml')
        body = child(root, 'body')
        if body is None:
            raise ValueError('document.xml 缺少 w:body')

        blocks, paragraphs, tables = [], [], []
        inspector.collect_blocks(body, 'body', blocks, paragraphs, tables)

        sections = []
        for sect_pr in root.iter(qn('w', 'sectPr')):
            section = parse_section(sect_pr, inspector.rels)
            if section:
                sections.append(section)

        header_footer = []
        seen_parts = set()
        for section in sections:
            for kind in ('headers', 'footers'):
                for ref in section.get(kind, []):
                    part = ref.get('part')
                    if not part or part in seen_parts:
                        continue
                    seen_parts.add(part)
                    part_root = read_xml(archive, part)
                    if part_root is None:
                        inspector.warnings.append(f'页眉页脚部件缺失：{part}')
                        continue
                    hf_blocks, hf_paragraphs, hf_tables = [], [], []
                    inspector.collect_blocks(part_root, part, hf_blocks, hf_paragraphs, hf_tables)
                    header_footer.append({
                        'type': 'header' if kind == 'headers' else 'footer',
                        'variant': ref.get('type'),
                        'part': part,
                        'blocks': hf_blocks,
                        'paragraphs': hf_paragraphs,
                        'tables': hf_tables,
                    })

        images = inspector.images(body, 'word/document.xml')
        for item in header_footer:
            images.extend(inspector.images(read_xml(archive, item['part']), item['part']))

        return {
            'schema': SCHEMA,
            'type': 'docx',
            'file': {
                'name': path.name,
                'path': str(path),
                'size_bytes': len(data),
                'sha256': sha256_bytes(data),
                'part_count': len(names),
                'parts': sorted(names),
            },
            'theme': inspector.theme,
            'document_defaults': {
                'paragraph': inspector.styles.get('paragraph'),
                'run': inspector.styles.get('run'),
                'default_paragraph_style': inspector.styles.get('default_paragraph_id'),
                'default_character_style': inspector.styles.get('default_character_id'),
            },
            'styles': inspector.styles.get('styles'),
            'numbering': parse_numbering(archive),
            'sections': sections,
            'body': blocks,
            'paragraphs': paragraphs,
            'tables': tables,
            'headers_footers': header_footer,
            'images': images,
            'warnings': inspector.warnings,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', help='待解析的 .docx 文件')
    parser.add_argument('--json', dest='outfile', help='JSON 输出路径（默认打印到 stdout）')
    args = parser.parse_args(argv)
    try:
        result = inspect_docx(args.file)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.outfile:
            Path(args.outfile).write_text(output + '\n', encoding='utf-8')
        else:
            print(output)
    except (ValueError, OSError, BadZipFile) as exc:
        parser.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
