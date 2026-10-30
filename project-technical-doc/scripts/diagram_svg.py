#!/usr/bin/env python3
"""Make offline SVG diagrams for a supported, conservative Mermaid flowchart subset.

Priority: Mermaid CLI (when installed) -> Graphviz for simple flowchart graphs ->
no SVG, leaving the original fenced Mermaid text intact as fallback.
The latter must be reported and never presented as a completed diagram.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

FLOW_HEADER = re.compile(r"^\s*(?:flowchart|graph)\s+(TD|TB|BT|LR|RL)\s*$", re.I)
NODE = re.compile(r"^\s*([A-Za-z_][\w-]*)(?:\s*(\[[^\]]*\]|\{[^}]*\}|\([^)]*\)))?\s*$")
ARROW = re.compile(r"(-->|-\.->|==>)")
EDGE_LABEL = re.compile(r"^(.*?)\s+--\s+(.+?)\s*$")
SKIP = re.compile(r"^\s*(?:%%.*)?$")


def _dot_escape(v):
    return v.replace('\\', '\\\\').replace('"','\\"').replace('\r','').replace('\n', '\\n')


def _parse_node(text):
    m = NODE.fullmatch(text.strip())
    if not m: raise ValueError('无法识别节点定义：' + text[:100])
    ident, raw = m.group(1), m.group(2)
    if raw:
        label = raw[1:-1].strip().replace('\\n','\n')
        shape = 'diamond' if raw.startswith('{') else ('ellipse' if raw.startswith('(') else 'box')
    else:
        label, shape = ident, 'box'
    if not label:label=ident
    return ident, label, shape


def _flowchart_to_dot(source):
    """Strict parser: unsupported syntax returns ValueError, never a misleading graph."""
    lines = [x.strip() for x in source.strip().splitlines() if x.strip() and not x.lstrip().startswith('%%')]
    if not lines:raise ValueError('图代码为空')
    m=FLOW_HEADER.fullmatch(lines.pop(0))
    if not m:raise ValueError('仅使用 Graphviz 回退转换 flowchart/graph TD/TB/LR/RL/BT')
    rankdir = {'TD':'TB', 'TB':'TB','LR':'LR','RL':'RL','BT':'BT'}[m.group(1).upper()]
    nodes={};edges=[]
    for line in lines:
        if line.endswith(';'):line=line[:-1].strip()
        if line.startswith(('classDef ', 'class ', 'style ', 'linkStyle ', 'click ', 'subgraph ', 'end', 'direction ')):
            raise ValueError('包含 Graphviz 回退不支持的 Mermaid 修饰或子图')
        arrow=ARROW.search(line)
        if not arrow:
            ident,label,shape=_parse_node(line)
            nodes[ident]=(label,shape)
            continue
        left=line[:arrow.start()].strip();right=line[arrow.end():].strip()
        if ARROW.search(right):raise ValueError('包含链式箭头，拒绝不完整转换')
        label=''
        lm=EDGE_LABEL.fullmatch(left)
        if lm:
            left=lm.group(1).strip();label=lm.group(2).strip()
        lm=re.match(r'^\|([^|]+)\|\s*(.*)$',right)
        if lm:
            if label:raise ValueError('箭头使用了重复标签')
            label,right=lm.group(1),lm.group(2).strip()
        sid,slab,sshape=_parse_node(left)
        tid,tlab,tshape=_parse_node(right)
        if sid not in nodes or slab!=sid:nodes[sid]=(slab,sshape)
        if tid not in nodes or tlab!=tid:nodes[tid]=(tlab,tshape)
        edges.append((sid,tid,label,arrow.group(1)))
    if not edges:raise ValueError('未发现可解析的连接线')
    result=[f'digraph G {{',f'  rankdir={rankdir};',
            '  graph [bgcolor="transparent", pad="0.22", nodesep="0.34", ranksep="0.48"];',
            '  node [fontname="Noto Sans CJK SC", fontsize=12, style="filled,rounded", fillcolor="#F1F3FF", color="#8B88D8", fontcolor="#33415D", penwidth=1.3, margin="0.19,0.12"];',
            '  edge [fontname="Noto Sans CJK SC", fontsize=10, color="#8689C7", fontcolor="#5C648D", arrowsize=0.72, penwidth=1.25];']
    for ident,(label,shape) in nodes.items():
        color = '#E6F5F4' if shape=='diamond' else '#F1F3FF'
        result.append(f'  "{_dot_escape(ident)}" [label="{_dot_escape(label)}", shape={shape}, fillcolor="{color}"];')
    for sid,tid,label,kind in edges:
        style=', style=dashed' if kind=='-.->' else ''
        lb=f', label="{_dot_escape(label)}"' if label else ''
        result.append(f'  "{_dot_escape(sid)}" -> "{_dot_escape(tid)}" [{lb.lstrip(", ") if lb else ""}{style.lstrip(", ") if style and not lb else style}];')
    result.append('}')
    return '\n'.join(result)


def render_one(source: str, svgfile: Path):
    svgfile.parent.mkdir(parents=True, exist_ok=True)
    cli=shutil.which('mmdc')
    if cli:
        srcfile=svgfile.with_suffix('.mmd')
        srcfile.write_text(source,'utf-8')
        try:
            cp=subprocess.run([cli, '-i',str(srcfile),'-o',str(svgfile),'-b','transparent'],
                              capture_output=True,text=True,timeout=30)
            if cp.returncode==0 and svgfile.is_file() and '<svg' in svgfile.read_text('utf-8'):
                return 'mermaid-cli',None
        except (OSError,subprocess.TimeoutExpired) as exc:
            cli_error=str(exc)
        else:cli_error=(cp.stderr or cp.stdout)[-500:]
    else:cli_error='Mermaid CLI 未安装'
    dot=shutil.which('dot')
    if dot:
        try:
            dot_src=_flowchart_to_dot(source)
            cp=subprocess.run([dot,'-Tsvg','-o',str(svgfile)],input=dot_src,text=True,
                              capture_output=True,timeout=12)
            if cp.returncode==0 and svgfile.is_file() and '<svg' in svgfile.read_text('utf-8'):
                return 'graphviz-flowchart-subset',None
            return None, (cp.stderr or 'dot 图形渲染失败')[-500:]
        except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
            return None, f'{cli_error}；Graphviz 回退不可用：{exc}'
    return None, f'{cli_error}；Graphviz dot 未安装'


def extract_mermaid(markdown):
    """Generate in the same order as render_html.py (excluding directory section)."""
    from render_html import extract_chapters, strip_number, DEFAULT_EXCLUDES
    _,chapters=extract_chapters(markdown)
    all_sources=[]
    for name,body in chapters:
        title=strip_number(name)
        if title=='目录' or any(word in title for word in DEFAULT_EXCLUDES):continue
        all_sources.extend(re.findall(r'^```mermaid\s*\n([\s\S]*?)\n```\s*$',body,re.M|re.I))
    return all_sources


def render_diagrams(markdown, svg_dir):
    svg_dir=Path(svg_dir)
    sources=extract_mermaid(markdown)
    report=[]
    for idx,source in enumerate(sources,1):
        path=svg_dir/f'{idx}.svg'
        kind,error=render_one(source,path)
        report.append({'index':idx,'engine':kind,'svg':str(path) if kind else None,'warning':error})
    return report
