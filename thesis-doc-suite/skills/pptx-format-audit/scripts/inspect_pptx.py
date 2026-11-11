#!/usr/bin/env python3
"""PPTX 格式全景只读解析（仅标准库）。

直接读取 OOXML 包内 presentation.xml / slideMaster*.xml / slideLayout*.xml /
slide*.xml / theme*.xml，输出结构化 JSON：

- 幻灯片尺寸、主题字体与配色、母版/版式占位符
- 每个形状的位置尺寸、占位符继承、文本框内外边距与自动调整
- 每段文字的实际字号/字体/加粗/颜色/行距/段距/项目符号（继承链已合并）
- 表格列宽行高与单元格格式、图片显示尺寸与像素尺寸、哈希

只读：不修改原文件，不写项目资产。

Usage:
  python inspect_pptx.py <file.pptx> [--json <out.json>]
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
import struct
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
}
SCHEMA = 'pptx-format-audit/1'


def qn(prefix, tag):
    return '{%s}%s' % (NS[prefix], tag)


def get(el, attr, prefix='p'):
    return None if el is None else el.get(qn(prefix, attr))


def child(el, tag, prefix='p'):
    return None if el is None else el.find(qn(prefix, tag))


def children(el, tag, prefix='p'):
    return [] if el is None else el.findall(qn(prefix, tag))


def int_attr(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def emu_to_cm(value):
    return None if value is None else round(value / 360000.0, 3)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def image_pixels(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        return list(struct.unpack('>II', data[16:24]))
    if data[:6] in (b'GIF87a', b'GIF89a') and len(data) >= 10:
        return list(struct.unpack('<HH', data[6:10]))
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


def merge(base, override):
    out = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


# ---------------------------------------------------------------- package

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


class Package:
    def __init__(self, archive):
        self.archive = archive
        self.names = set(archive.namelist())
        self._rels = {}
        self._xml = {}

    def xml(self, part):
        if part not in self._xml:
            try:
                data = self.archive.read(part)
            except KeyError:
                self._xml[part] = None
            else:
                try:
                    self._xml[part] = ET.fromstring(data)
                except ET.ParseError as exc:
                    raise ValueError(f'{part} XML 解析失败：{exc}')
        return self._xml[part]

    def rels(self, part):
        if part in self._rels:
            return self._rels[part]
        rels_part = part.rsplit('/', 1)[0] + '/_rels/' + part.rsplit('/', 1)[1] + '.rels'
        root = self.xml(rels_part)
        base = part.rsplit('/', 1)[0]
        result = {}
        if root is not None:
            for rel in root.findall(qn('rel', 'Relationship')):
                target = rel.get('Target') or ''
                resolved = target.lstrip('/') if target.startswith('/') else _join(base, target)
                result[rel.get('Id')] = {
                    'type': (rel.get('Type') or '').rsplit('/', 1)[-1],
                    'target': resolved,
                    'external': rel.get('TargetMode') == 'External',
                }
        self._rels[part] = result
        return result

    def related(self, part, rel_type):
        for rel in self.rels(part).values():
            if rel['type'] == rel_type and not rel['external']:
                return rel['target']
        return None


# ---------------------------------------------------------------- formats

def parse_color(container):
    if container is None:
        return {}
    solid = child(container, 'solidFill', 'a')
    if solid is None:
        return {}
    srgb = child(solid, 'srgbClr', 'a')
    if srgb is not None and srgb.get('val'):
        return {'color': srgb.get('val')}
    scheme = child(solid, 'schemeClr', 'a')
    if scheme is not None and scheme.get('val'):
        return {'color_scheme': scheme.get('val')}
    return {}


def parse_run_props(rpr):
    if rpr is None:
        return {}
    out = {}
    size = rpr.get('sz')
    if int_attr(size) is not None:
        out['font_size_pt'] = round(int_attr(size) / 100.0, 3)
    for attr, key in (('b', 'bold'), ('i', 'italic'), ('kumimoji', 'kumimoji'), ('cap', 'caps')):
        value = rpr.get(attr)
        if value is not None:
            out[key] = value in ('1', 'true', 'on')
    underline = rpr.get('u')
    if underline is not None:
        out['underline'] = underline
    strike = rpr.get('strike')
    if strike is not None:
        out['strike'] = strike
    latin = child(rpr, 'latin', 'a')
    if latin is not None and latin.get('typeface'):
        out['font_latin'] = latin.get('typeface')
    ea = child(rpr, 'ea', 'a')
    if ea is not None and ea.get('typeface'):
        out['font_ea'] = ea.get('typeface')
    cs = child(rpr, 'cs', 'a')
    if cs is not None and cs.get('typeface'):
        out['font_cs'] = cs.get('typeface')
    out.update(parse_color(rpr))
    highlight = child(rpr, 'highlight', 'a')
    if highlight is not None:
        srgb = child(highlight, 'srgbClr', 'a')
        scheme = child(highlight, 'schemeClr', 'a')
        if srgb is not None and srgb.get('val'):
            out['highlight_color'] = srgb.get('val')
        elif scheme is not None and scheme.get('val'):
            out['highlight_color_scheme'] = scheme.get('val')
    spacing = rpr.get('spc')
    if int_attr(spacing) is not None:
        out['character_spacing_pt'] = round(int_attr(spacing) / 100.0, 3)
    baseline = rpr.get('baseline')
    if int_attr(baseline) is not None:
        out['baseline_percent'] = round(int_attr(baseline) / 1000.0, 3)
    lang = rpr.get('lang')
    if lang:
        out['language'] = lang
    return out


def parse_bullet(ppr):
    if ppr is None:
        return None
    if child(ppr, 'buNone', 'a') is not None:
        return {'type': 'none'}
    char_node = child(ppr, 'buChar', 'a')
    if char_node is not None:
        return {'type': 'char', 'char': char_node.get('char')}
    auto = child(ppr, 'buAutoNum', 'a')
    if auto is not None:
        return {'type': 'auto', 'scheme': auto.get('type'),
                'start_at': int_attr(auto.get('startAt'))}
    return None


def parse_spacing_value(node):
    if node is None:
        return None
    percent = child(node, 'spcPct', 'a')
    if percent is not None and int_attr(percent.get('val')) is not None:
        return {'percent': round(int_attr(percent.get('val')) / 1000.0, 3)}
    points = child(node, 'spcPts', 'a')
    if points is not None and int_attr(points.get('val')) is not None:
        return {'pt': round(int_attr(points.get('val')) / 100.0, 3)}
    return None


def parse_paragraph_props(ppr):
    if ppr is None:
        return {}
    out = {}
    level = int_attr(ppr.get('lvl'))
    if level is not None:
        out['level'] = level
    alignment = ppr.get('algn')
    if alignment:
        out['alignment'] = alignment
    margin = int_attr(ppr.get('marL'))
    if margin is not None:
        out['margin_left_cm'] = emu_to_cm(margin)
    indent = int_attr(ppr.get('indent'))
    if indent is not None:
        out['indent_cm'] = emu_to_cm(indent)
    line = parse_spacing_value(child(ppr, 'lnSpc', 'a'))
    if line:
        out['line_spacing'] = line
    before = parse_spacing_value(child(ppr, 'spcBef', 'a'))
    if before:
        out['space_before'] = before
    after = parse_spacing_value(child(ppr, 'spcAft', 'a'))
    if after:
        out['space_after'] = after
    bullet = parse_bullet(ppr)
    if bullet:
        out['bullet'] = bullet
    default_run = parse_run_props(child(ppr, 'defRPr', 'a'))
    if default_run:
        out['default_run'] = default_run
    return out


def parse_level_styles(container):
    out = {}
    for index in range(1, 10):
        node = child(container, f'lvl{index}pPr', 'a')
        if node is not None:
            out[str(index - 1)] = parse_paragraph_props(node)
    return out


def parse_text_body(tx_body):
    if tx_body is None:
        return None
    body_pr = child(tx_body, 'bodyPr', 'a')
    body = {}
    if body_pr is not None:
        for attr, key in (('wrap', 'wrap'), ('anchor', 'anchor'), ('anchorCtr', 'anchor_centered'),
                          ('vert', 'vertical'), ('rot', 'rotation'), ('numCol', 'columns')):
            value = body_pr.get(attr)
            if value is not None:
                body[key] = value
        for fit in ('noAutofit', 'normAutofit', 'spAutoFit'):
            node = child(body_pr, fit, 'a')
            if node is not None:
                body['autofit'] = fit
                break
        margins = {}
        for attr, key in (('lIns', 'left_cm'), ('rIns', 'right_cm'), ('tIns', 'top_cm'), ('bIns', 'bottom_cm')):
            value = int_attr(body_pr.get(attr))
            if value is not None:
                margins[key] = emu_to_cm(value)
        if margins:
            body['margins_cm'] = margins
    list_styles = parse_level_styles(child(tx_body, 'lstStyle', 'a'))
    paragraphs = []
    for paragraph in children(tx_body, 'p', 'a'):
        ppr = parse_paragraph_props(child(paragraph, 'pPr', 'a'))
        runs = []
        for node in list(paragraph):
            tag = node.tag.rsplit('}', 1)[-1]
            if tag in ('r', 'fld'):
                rpr = parse_run_props(child(node, 'rPr', 'a'))
                text_node = child(node, 't', 'a')
                runs.append({
                    'text': (text_node.text or '') if text_node is not None else '',
                    'direct': rpr,
                })
            elif tag == 'br':
                runs.append({'text': '\n', 'direct': parse_run_props(child(node, 'rPr', 'a'))})
        paragraphs.append({'properties': ppr, 'runs': runs})
    return {'body': body, 'list_styles': list_styles, 'paragraphs': paragraphs}


def parse_xfrm_element(xfrm):
    if xfrm is None:
        return None
    off = child(xfrm, 'off', 'a')
    ext = child(xfrm, 'ext', 'a')
    out = {}
    if off is not None:
        out['left_cm'] = emu_to_cm(int_attr(off.get('x')))
        out['top_cm'] = emu_to_cm(int_attr(off.get('y')))
    if ext is not None:
        out['width_cm'] = emu_to_cm(int_attr(ext.get('cx')))
        out['height_cm'] = emu_to_cm(int_attr(ext.get('cy')))
    rotation = int_attr(xfrm.get('rot'))
    if rotation is not None:
        out['rotation_deg'] = round(rotation / 60000.0, 3)
    if xfrm.get('flipH') in ('1', 'true'):
        out['flip_h'] = True
    if xfrm.get('flipV') in ('1', 'true'):
        out['flip_v'] = True
    return out or None


def parse_xfrm(sp_pr):
    if sp_pr is None:
        return None
    xfrm = child(sp_pr, 'xfrm', 'a')
    if xfrm is None:
        xfrm = child(sp_pr, 'xfrm', 'p')
    return parse_xfrm_element(xfrm)


def parse_placeholder_ref(shape):
    ph = None
    for nv_tag in ('nvSpPr', 'nvPicPr', 'nvGraphicFramePr', 'nvCxnSpPr', 'nvGrpSpPr'):
        nv = child(shape, nv_tag)
        if nv is not None:
            ph = child(child(nv, 'nvPr'), 'ph')
            break
    if ph is None:
        return None
    return {
        'type': ph.get('type') or 'body',
        'index': int_attr(ph.get('idx')),
        'size': ph.get('sz'),
    }


def shape_identity(shape):
    for nv_tag in ('nvSpPr', 'nvPicPr', 'nvGraphicFramePr', 'nvCxnSpPr', 'nvGrpSpPr'):
        nv = child(shape, nv_tag)
        if nv is not None:
            c_nv = child(nv, 'cNvPr')
            if c_nv is not None:
                return {'id': int_attr(c_nv.get('id')), 'name': c_nv.get('name')}
    return {'id': None, 'name': None}


# ---------------------------------------------------------------- contexts

class Deck:
    def __init__(self, package):
        self.package = package
        self.warnings = []
        self.default_text_style = {}
        self.slide_size = None
        self.notes_size = None
        self.slide_parts = []
        self.masters = {}
        self.layouts = {}
        self.master_order = []
        self.layout_order = []
        self._load()

    def _load(self):
        presentation = self.package.xml('ppt/presentation.xml')
        if presentation is None:
            raise ValueError('缺少 ppt/presentation.xml，不是 PowerPoint 文档')
        size = child(presentation, 'sldSz')
        if size is not None:
            self.slide_size = {'width_cm': emu_to_cm(int_attr(size.get('cx'))),
                               'height_cm': emu_to_cm(int_attr(size.get('cy')))}
        notes = child(presentation, 'notesSz')
        if notes is not None:
            self.notes_size = {'width_cm': emu_to_cm(int_attr(notes.get('cx'))),
                               'height_cm': emu_to_cm(int_attr(notes.get('cy')))}
        self.default_text_style = parse_level_styles(child(presentation, 'defaultTextStyle'))
        rels = self.package.rels('ppt/presentation.xml')
        for sld_id in children(child(presentation, 'sldIdLst'), 'sldId'):
            rel = rels.get(get(sld_id, 'id', 'r'), {})
            if rel.get('target'):
                self.slide_parts.append({'part': rel['target'], 'slide_id': int_attr(sld_id.get('id'))})
        for part in sorted(self.package.names, key=_numeric_key):
            if part.startswith('ppt/slideMasters/') and part.endswith('.xml'):
                self.master_order.append(part)
            elif part.startswith('ppt/slideLayouts/') and part.endswith('.xml'):
                self.layout_order.append(part)
        for index, part in enumerate(self.master_order):
            self.masters[part] = self._load_master(index, part)
        for index, part in enumerate(self.layout_order):
            self.layouts[part] = self._load_layout(index, part)

    def _load_master(self, index, part):
        root = self.package.xml(part)
        c_sld = child(root, 'cSld')
        tx_styles = {'title': {}, 'body': {}, 'other': {}}
        styles_root = child(root, 'txStyles')
        for key, tag in (('title', 'titleStyle'), ('body', 'bodyStyle'), ('other', 'otherStyle')):
            node = child(styles_root, tag)
            if node is not None:
                tx_styles[key] = parse_level_styles(node)
                default = parse_run_props(child(node, 'defRPr', 'a'))
                if default:
                    tx_styles[key]['default'] = default
        theme_part = self.package.related(part, 'theme') or 'ppt/theme/theme1.xml'
        return {
            'index': index,
            'part': part,
            'name': c_sld.get('name') if c_sld is not None else None,
            'theme_part': theme_part,
            'text_styles': tx_styles,
            'placeholders': self._placeholders(child(c_sld, 'spTree')),
            'layout_parts': [rel['target'] for rel in self.package.rels(part).values()
                             if rel['type'] == 'slideLayout'],
        }

    def _load_layout(self, index, part):
        root = self.package.xml(part)
        c_sld = child(root, 'cSld')
        master_part = self.package.related(part, 'slideMaster')
        return {
            'index': index,
            'part': part,
            'name': c_sld.get('name') if c_sld is not None else None,
            'type': root.get('type'),
            'master_part': master_part,
            'show_master_sp': root.get('showMasterSp') not in ('0', 'false'),
            'placeholders': self._placeholders(child(c_sld, 'spTree')),
        }

    def _placeholders(self, sp_tree):
        out = []
        if sp_tree is None:
            return out
        for node in list(sp_tree):
            tag = node.tag.rsplit('}', 1)[-1]
            if tag not in ('sp', 'pic', 'graphicFrame', 'cxnSp'):
                continue
            ref = parse_placeholder_ref(node)
            if not ref:
                continue
            identity = shape_identity(node)
            position = parse_xfrm(child(node, 'spPr'))
            text = parse_text_body(child(node, 'txBody'))
            out.append({
                'type': ref['type'],
                'index': ref['index'],
                'size': ref['size'],
                'name': identity['name'],
                'position_cm': position,
                'list_styles': text.get('list_styles', {}) if text else {},
            })
        return out


def _numeric_key(part):
    digits = ''.join(ch if ch.isdigit() else ' ' for ch in part).split()
    return (part.rsplit('/', 1)[0], int(digits[-1]) if digits else 0)


def placeholder_lookup(placeholders):
    by_index = {}
    by_type = {}
    for item in placeholders:
        if item.get('index') is not None:
            by_index[str(item['index'])] = item
        by_type.setdefault(item.get('type'), item)
    return by_index, by_type


def find_placeholder(ref, layout_ph, master_ph):
    layout_by_index, layout_by_type = layout_ph
    master_by_index, master_by_type = master_ph
    key = str(ref['index']) if ref.get('index') is not None else None
    layout = layout_by_index.get(key) if key else None
    master = master_by_index.get(key) if key else None
    if layout is None:
        layout = layout_by_type.get(ref.get('type'))
    if master is None:
        master = master_by_type.get(ref.get('type'))
    return layout, master


def style_group(ph_type):
    if ph_type in ('title', 'ctrTitle'):
        return 'title'
    if ph_type in ('body', 'subTitle', 'obj'):
        return 'body'
    return 'other'


def theme_font(theme, typeface):
    if not theme or not typeface:
        return None
    if not typeface.startswith('+'):
        return None
    slot = 'major' if typeface[1:3] == 'mj' else 'minor'
    kind = typeface[-2:]
    fonts = theme.get('fonts', {}).get(slot, {})
    return {'lt': fonts.get('latin'), 'ea': fonts.get('ea'), 'cs': fonts.get('cs')}.get(kind)


def resolve_theme(fmt, theme):
    if not fmt:
        return fmt
    for key, out_key in (('font_latin', 'font_latin_resolved'),
                         ('font_ea', 'font_ea_resolved'),
                         ('font_cs', 'font_cs_resolved')):
        value = theme_font(theme, fmt.get(key))
        if value:
            fmt[out_key] = value
    return fmt


# ---------------------------------------------------------------- emitter

class SlideEmitter:
    def __init__(self, deck):
        self.deck = deck
        self.package = deck.package

    def slide(self, index, entry):
        part = entry['part']
        root = self.package.xml(part)
        if root is None:
            self.deck.warnings.append(f'幻灯片部件缺失：{part}')
            return None
        layout_part = self.package.related(part, 'slideLayout')
        layout = self.deck.layouts.get(layout_part, {})
        master_part = layout.get('master_part') or (self.deck.master_order[0] if self.deck.master_order else None)
        master = self.deck.masters.get(master_part, {})
        theme = self._theme(master)
        rels = self.package.rels(part)
        layout_ph = placeholder_lookup(layout.get('placeholders', []))
        master_ph = placeholder_lookup(master.get('placeholders', []))
        ctx = {
            'theme': theme,
            'layout_ph': layout_ph,
            'master_ph': master_ph,
            'text_styles': master.get('text_styles', {}),
            'rels': rels,
            'part': part,
        }
        c_sld = child(root, 'cSld')
        shapes = self._shape_tree(child(c_sld, 'spTree'), ctx, f'slide{index + 1}')
        notes_part = self.package.related(part, 'notesSlide')
        return {
            'index': index,
            'part': part,
            'slide_id': entry.get('slide_id'),
            'hidden': root.get('show') in ('0', 'false'),
            'layout_part': layout_part,
            'layout_name': layout.get('name'),
            'master_part': master_part,
            'notes_part': notes_part,
            'notes_text': self._notes_text(notes_part),
            'shapes': shapes,
        }

    def _theme(self, master):
        part = master.get('theme_part') if master else None
        if not part:
            return None
        root = self.package.xml(part)
        if root is None:
            return None
        return parse_theme_root(root)

    def _notes_text(self, part):
        if not part:
            return None
        root = self.package.xml(part)
        if root is None:
            return None
        texts = [node.text for node in root.iter(qn('a', 't')) if node.text]
        return '\n'.join(texts) or None

    def _shape_tree(self, sp_tree, ctx, path):
        out = []
        if sp_tree is None:
            return out
        for node in list(sp_tree):
            tag = node.tag.rsplit('}', 1)[-1]
            if tag == 'sp':
                out.append(self._shape(node, ctx, path))
            elif tag == 'pic':
                out.append(self._picture(node, ctx, path))
            elif tag == 'graphicFrame':
                out.append(self._graphic_frame(node, ctx, path))
            elif tag == 'grpSp':
                out.append({
                    'kind': 'group',
                    **shape_identity(node),
                    'position_cm': parse_xfrm(child(node, 'grpSpPr')),
                    'children': self._shape_tree(node, ctx, path),
                })
            elif tag == 'cxnSp':
                out.append({'kind': 'connector', **shape_identity(node),
                            'position_cm': parse_xfrm(child(node, 'spPr'))})
        return out

    def _shape(self, node, ctx, path):
        identity = shape_identity(node)
        ref = parse_placeholder_ref(node)
        text = parse_text_body(child(node, 'txBody'))
        layout_ph_item, master_ph_item = find_placeholder(ref, ctx['layout_ph'], ctx['master_ph']) if ref else (None, None)
        position = parse_xfrm(child(node, 'spPr'))
        if not position:
            if layout_ph_item and layout_ph_item.get('position_cm'):
                position = layout_ph_item['position_cm']
            elif master_ph_item and master_ph_item.get('position_cm'):
                position = master_ph_item['position_cm']
        shape = {
            'kind': 'shape',
            **identity,
            'placeholder': ref,
            'position_cm': position,
            'text_body': self._resolve_text(text, ref, layout_ph_item, master_ph_item, ctx),
        }
        if ref and ref.get('type') == 'pic':
            shape['kind'] = 'placeholder_picture'
        return shape

    def _resolve_text(self, text, ref, layout_ph_item, master_ph_item, ctx):
        if not text:
            return None
        group = style_group(ref.get('type') if ref else 'other')
        tx_style = ctx['text_styles'].get(group, {})
        base = dict(tx_style.get('default') or {})
        slide_list = text.get('list_styles', {})
        paragraphs = []
        for paragraph in text.get('paragraphs', []):
            props = paragraph.get('properties', {})
            level = str(props.get('level', 0))
            layers = [
                self.deck.default_text_style.get(level),
                base,
                tx_style.get(level),
                (master_ph_item.get('list_styles') or {}).get(level) if master_ph_item else None,
                (layout_ph_item.get('list_styles') or {}).get(level) if layout_ph_item else None,
                slide_list.get(level),
            ]
            inherited, run_base = {}, {}
            for layer in layers:
                if not layer:
                    continue
                inherited = merge(inherited, {key: value for key, value in layer.items()
                                              if key != 'default_run'})
                run_base = merge(run_base, layer.get('default_run'))
            paragraph_props = {key: value for key, value in props.items() if key != 'default_run'}
            paragraph_fmt = merge(merge(inherited, run_base), paragraph_props)
            run_defaults = merge(run_base, props.get('default_run'))
            runs = []
            for run in paragraph.get('runs', []):
                effective = merge(run_defaults, run.get('direct'))
                effective = resolve_theme(dict(effective), ctx['theme'])
                runs.append({
                    'text': run.get('text'),
                    'direct': run.get('direct'),
                    'effective': effective,
                })
            paragraphs.append({
                'level': int(level),
                'alignment': props.get('alignment'),
                'bullet': props.get('bullet'),
                'line_spacing': props.get('line_spacing'),
                'space_before': props.get('space_before'),
                'space_after': props.get('space_after'),
                'margin_left_cm': props.get('margin_left_cm'),
                'indent_cm': props.get('indent_cm'),
                'effective': resolve_theme(dict(paragraph_fmt), ctx['theme']),
                'runs': runs,
            })
        return {'body': text.get('body'), 'paragraphs': paragraphs}

    def _picture(self, node, ctx, path):
        identity = shape_identity(node)
        blip = node.find('.//' + qn('a', 'blip'))
        rel_id = blip.get(qn('r', 'embed')) if blip is not None else None
        relation = ctx['rels'].get(rel_id, {})
        item = {
            'kind': 'picture',
            **identity,
            'placeholder': parse_placeholder_ref(node),
            'position_cm': parse_xfrm(child(node, 'spPr')),
            'relationship_id': rel_id,
            'target': relation.get('target'),
        }
        self._media_info(item, relation)
        return item

    def _media_info(self, item, relation):
        target = relation.get('target')
        if not target or relation.get('external'):
            return
        try:
            data = self.package.archive.read(target)
        except KeyError:
            self.deck.warnings.append(f'图片关系目标缺失：{target}')
            return
        item['size_bytes'] = len(data)
        item['sha256'] = sha256_bytes(data)
        pixels = image_pixels(data)
        if pixels:
            item['pixel_size'] = pixels

    def _graphic_frame(self, node, ctx, path):
        identity = shape_identity(node)
        data = node.find('.//' + qn('a', 'graphicData'))
        uri = data.get('uri') if data is not None else None
        item = {
            'kind': 'graphic_frame',
            **identity,
            'placeholder': parse_placeholder_ref(node),
            'position_cm': parse_xfrm_element(child(node, 'xfrm')),
            'uri': uri,
        }
        table = data.find(qn('a', 'tbl')) if data is not None else None
        if table is not None:
            item['kind'] = 'table'
            item['table'] = self._table(table, ctx)
        chart_ref = data.find('.//' + qn('c', 'chart')) if data is not None else None
        if chart_ref is not None:
            item['kind'] = 'chart'
            rel_id = chart_ref.get(qn('r', 'id'))
            relation = ctx['rels'].get(rel_id, {})
            item['chart'] = {'relationship_id': rel_id, 'target': relation.get('target')}
        return item

    def _table(self, table, ctx):
        grid = [emu_to_cm(int_attr(col.get('w'))) for col in children(child(table, 'tblGrid', 'a'), 'gridCol', 'a')]
        rows = []
        for row in children(table, 'tr', 'a'):
            cells = []
            for cell in children(row, 'tc', 'a'):
                tc_pr = child(cell, 'tcPr', 'a')
                entry = {
                    'text_body': self._resolve_text(parse_text_body(child(cell, 'txBody', 'a')), None, None, None, ctx),
                }
                if tc_pr is not None:
                    if tc_pr.get('gridSpan'):
                        entry['grid_span'] = int_attr(tc_pr.get('gridSpan'))
                    if tc_pr.get('hMerge') in ('1', 'true'):
                        entry['h_merge'] = True
                    if tc_pr.get('vMerge') in ('1', 'true'):
                        entry['v_merge'] = True
                    if tc_pr.get('anchor'):
                        entry['vertical_alignment'] = tc_pr.get('anchor')
                    margins = {}
                    for attr, key in (('marL', 'left_cm'), ('marR', 'right_cm'),
                                      ('marT', 'top_cm'), ('marB', 'bottom_cm')):
                        value = int_attr(tc_pr.get(attr))
                        if value is not None:
                            margins[key] = emu_to_cm(value)
                    if margins:
                        entry['margins_cm'] = margins
                cells.append(entry)
            row_entry = {'cells': cells}
            if row.get('h'):
                row_entry['height_cm'] = emu_to_cm(int_attr(row.get('h')))
            rows.append(row_entry)
        return {'columns_cm': grid, 'rows': rows}


def parse_theme_root(root):
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


def parse_slide_scope(values, total):
    """把 --slide 的 "3" / "2-4" / "1,5" 解析为 1 起的页码集合；None 表示全量。"""
    if not values:
        return None
    selected = set()
    for value in values:
        for piece in str(value).split(','):
            piece = piece.strip()
            if not piece:
                continue
            try:
                if '-' in piece:
                    start_text, _, end_text = piece.partition('-')
                    start, end = int(start_text), int(end_text)
                else:
                    start = end = int(piece)
            except ValueError:
                raise ValueError(f'无法识别的页码：{piece}（示例：--slide 3 或 --slide 2-4）')
            if start < 1 or end < start or end > total:
                raise ValueError(f'幻灯片页码 {piece} 超出范围 1–{total}')
            selected.update(range(start, end + 1))
    return sorted(selected) or None


def inspect_pptx(path, slides=None):
    """解析 PPTX；slides 传入 1 起的页码列表时只输出对应幻灯片（表页/主题仍全量）。"""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'文件不存在：{path}')
    data = path.read_bytes()
    try:
        archive = ZipFile(path)
    except BadZipFile as exc:
        raise ValueError(f'不是有效的 PPTX/ZIP 包：{exc}')
    with archive:
        package = Package(archive)
        if 'ppt/presentation.xml' not in package.names:
            raise ValueError('缺少 ppt/presentation.xml，不是 PowerPoint 文档')
        deck = Deck(package)
        emitter = SlideEmitter(deck)
        total = len(deck.slide_parts)
        scope = parse_slide_scope(slides, total)
        entries = list(enumerate(deck.slide_parts))
        if scope:
            entries = [(index, entry) for index, entry in entries if index + 1 in scope]
        slide_items = [slide for index, entry in entries
                       if (slide := emitter.slide(index, entry)) is not None]
        masters = []
        for master in deck.masters.values():
            masters.append({
                'index': master['index'],
                'part': master['part'],
                'name': master['name'],
                'theme_part': master['theme_part'],
                'text_styles': master['text_styles'],
                'placeholders': master['placeholders'],
                'layout_parts': master['layout_parts'],
            })
        layouts = []
        for layout in deck.layouts.values():
            layouts.append({key: value for key, value in layout.items() if key != 'master_part'} | {
                'master_index': deck.masters.get(layout.get('master_part'), {}).get('index'),
            })
        theme_part = next((master['theme_part'] for master in deck.masters.values()), 'ppt/theme/theme1.xml')
        theme_root = package.xml(theme_part)
        return {
            'schema': SCHEMA,
            'type': 'pptx',
            'file': {
                'name': path.name,
                'path': str(path),
                'size_bytes': len(data),
                'sha256': sha256_bytes(data),
                'part_count': len(package.names),
                'parts': sorted(package.names),
            },
            'presentation': {
                'slide_size_cm': deck.slide_size,
                'notes_size_cm': deck.notes_size,
                'slide_count': total,
                'slide_count_returned': len(slide_items),
                'default_text_style': deck.default_text_style,
            },
            'scope': {'slides': scope},
            'theme': parse_theme_root(theme_root) if theme_root is not None else None,
            'masters': masters,
            'layouts': layouts,
            'slides': slide_items,
            'warnings': deck.warnings,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', help='待解析的 .pptx 文件')
    parser.add_argument('--json', dest='outfile', help='JSON 输出路径（默认打印到 stdout）')
    parser.add_argument('--slide', action='append', metavar='N|A-B', default=None,
                        help='只看指定幻灯片（1 起，可重复；支持 3 / 2-4 / 1,5）。输出 index 仍为原始 0 起序号。')
    args = parser.parse_args(argv)
    try:
        result = inspect_pptx(args.file, slides=args.slide)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.outfile:
            Path(args.outfile).write_text(output + '\n', encoding='utf-8')
        else:
            print(output)
    except (ValueError, OSError, BadZipFile) as exc:
        parser.exit(2, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
