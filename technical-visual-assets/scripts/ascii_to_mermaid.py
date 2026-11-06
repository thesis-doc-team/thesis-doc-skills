#!/usr/bin/env python3
"""Conservative, reversible ASCII hierarchy/arrow parser (stdlib only).

Never infers a missing edge, implementation status, or device identity.
Returns a draft source with each node/edge linked to source line numbers.
Ambiguous ASCII diagrams are rejected for manual drafting and review.
"""
from __future__ import annotations
import json
import re

ARROWS = re.compile(r'\s+(?:-->|->|→|⇒|=>)\s+')
BRANCH = re.compile(r'^([\s│|]*)(?:[├└]──|[+\\]--|\|--)\s*(.+?)\s*$')
IGNORED = re.compile(r'^\s*(?:```\w*|```|\[.*\]:\s*https?://.*)\s*$')


def clean_label(label):
    label = re.sub(r'^\s*(?:[-*•]|\d+[.)、])\s+', '', label.strip())
    if not label or len(label) > 90 or re.search(r'[\[\]{}<>"`\x00-\x1f]', label):
        raise ValueError('节点文字有歧义或含图表不支持的字符，须人工复核：' + label[:50])
    return label


def build_mermaid(source_lines, start_line, category):
    """Return (text, evidence) or raise ValueError with no generated artifact."""
    if category not in ('system-framework', 'functional-architecture', 'flowchart'):
        raise ValueError('不支持的图表类别')
    chosen = [(start_line+i, s.rstrip()) for i,s in enumerate(source_lines) if s.strip() and not IGNORED.fullmatch(s)]
    if len(chosen) < 2 or len(chosen) > 55:
        raise ValueError('源行数不足或过多，请改用更精确的行号范围')
    texts = [s for _,s in chosen]
    # Arrows embedded INSIDE a tree-node label are text, not separate graph edges.
    has_arrows = any(ARROWS.search(s) and not BRANCH.fullmatch(s) for s in texts)
    has_tree = any(BRANCH.fullmatch(s) for s in texts)
    if has_arrows and has_tree:
        raise ValueError('箭头图与树状图混杂；自动解析可能误连，改为人工提取')
    if not has_arrows and not has_tree:
        raise ValueError('未检测到明确的树状层级/箭头关系；不能根据普通段落擅自推断拓扑')
    if category == 'flowchart' and not has_arrows:
        raise ValueError('流程图必须有实际步骤连接，不得将功能树改名为流程图')

    nodes = []; edges = []; by_label = {}; source_evidence=[]
    def add(label, lineno, distinct=False):
        label = clean_label(label)
        if not distinct and label in by_label:
            return by_label[label]
        if len(nodes) >= 40:
            raise ValueError('节点超过40个；请缩小范围')
        ident = 'N' + str(len(nodes)+1)
        nodes.append((ident, label))
        source_evidence.append({'node':ident,'text':label,'source_line':lineno})
        if not distinct:by_label[label] = ident
        return ident

    if has_arrows:
        for lineno, line in chosen:
            if not ARROWS.search(line):
                # Standalone headers/comments cannot be reliably turned into graph edges.
                if line.lstrip().startswith(('#', '图', '说明', '注：','注:')):
                    continue
                raise ValueError(f'第 {lineno} 行无明确箭头，拒绝猜测节点关系')
            pieces = ARROWS.split(line.strip())
            if not (2 <= len(pieces) <= 8):
                raise ValueError(f'第 {lineno} 行箭头链过长或为空')
            ids=[add(label,lineno) for label in pieces]
            edges.extend({'from':a,'to':b,'source_line':lineno} for a,b in zip(ids,ids[1:]))
    else:
        stack=[]
        saw_root=False
        for lineno, line in chosen:
            matched=BRANCH.fullmatch(line)
            if matched:
                prefix, name=matched.groups()
                width=len(prefix.expandtabs(4))
                if width % 4 != 0:
                    raise ValueError(f'第 {lineno} 行树状缩进不规范，拒绝误连')
                level = width//4 + 1
                if not saw_root:
                    raise ValueError(f'第 {lineno} 行缺少树状根节点')
                if level > len(stack):
                    raise ValueError(f'第 {lineno} 行缺少真实父节点，拒绝推断')
                ident=add(name,lineno,distinct=True)
                parent=stack[level-1]
                edges.append({'from':parent,'to':ident,'source_line':lineno})
                stack=stack[:level]+[ident]
            else:
                if saw_root or line.startswith(('#','-','*')):
                    raise ValueError(f'第 {lineno} 行不是合法的树节点；请缩小选区')
                root=add(line.strip(),lineno,distinct=True)
                stack=[root];saw_root=True
    if not edges:
        raise ValueError('未得到可证实的连线')
    flow='flowchart LR' if category=='system-framework' else 'flowchart TD'
    mmd=[flow]+[f'  {ident}[{label}]' for ident,label in nodes]+[f'  {edge["from"]} --> {edge["to"]}' for edge in edges]
    evidence={'category':category,'source_start_line':start_line,
              'source_end_line':start_line+len(source_lines)-1,'nodes':source_evidence,
              'edges':edges,'method':'strict-ascii-tree' if has_tree else 'explicit-arrow-lines',
              'review_required':True,
              'warning':'仅是原文层级/箭头关系的可编辑候选，并未证明架构真实性或功能完整性。'}
    return '\n'.join(mmd)+'\n', evidence
