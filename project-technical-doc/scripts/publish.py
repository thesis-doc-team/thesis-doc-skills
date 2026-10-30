#!/usr/bin/env python3
"""Mandatory second stage: validated generated MD -> offline user-facing HTML.

This command must be called only after the Agent has written an evidence-based
project Markdown document. It does not inspect or modify the source repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from check_markdown import check
from diagram_svg import render_diagrams
from render_html import build
from validate_html import validate


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unique_target(target: Path):
    if not target.exists():return target
    stem=target.stem
    for idx in range(2,1000):
        candidate=target.with_name(f'{stem}-v{idx}{target.suffix}')
        if not candidate.exists():return candidate
    raise RuntimeError('输出目录中版本过多，请手动指定目录')


def publish(args):
    md=Path(args.markdown).expanduser().resolve()
    if not md.is_file():raise FileNotFoundError(f'MD 不存在：{md}')
    if check(md):raise RuntimeError('MD 结构门禁 FAIL，停止生成 HTML；请先修订 MD 再运行')
    source_text=md.read_text('utf-8-sig')
    outdir=Path(args.out_dir).expanduser().resolve() if args.out_dir else md.parent
    outdir.mkdir(parents=True,exist_ok=True)
    target=unique_target(outdir / (md.stem.replace('-技术文档','').replace('_技术文档','')+'_用户展示.html'))
    config=json.loads(Path(args.config).read_text('utf-8')) if args.config else {}
    # Each invocation has its own build directory. SVGs are embedded in the HTML,
    # so viewers never need access to this directory.
    build_dir=outdir/'.showcase-build'/target.stem
    build_dir.mkdir(parents=True,exist_ok=True)
    diagrams=render_diagrams(source_text,build_dir/'svg')
    markup,render_info=build(config,source_text,md.name,build_dir/'svg',md.parent)
    target.write_text(markup,'utf-8')
    errors,warnings,statistics=validate(target,md)
    if render_info.get('cross_references_to_review'):
        warnings.append('源文包含被排除章节的跨章节引用，请逐条检查：'+str(render_info['cross_references_to_review']))
    diagram_fail=[item for item in diagrams if not item['engine']]
    if diagram_fail:
        warnings.append(f'{len(diagram_fail)}/{len(diagrams)} 张 Mermaid 图未转换为 SVG；页面保留可读原文')
    result={
        'status':'FAIL' if errors else ('WARN' if warnings else 'PASS'),
        'created_at':datetime.now().astimezone().isoformat(timespec='seconds'),
        'generated_markdown':str(md), 'generated_html':str(target),
        'markdown_sha256':sha256(md), 'html_sha256':sha256(target),
        'configuration':str(Path(args.config).resolve()) if args.config else None,
        'render':render_info, 'diagrams':diagrams, 'html_validation':statistics,
        'errors':errors,'warnings':warnings,
        'reminder':'自动校验不等于网页浏览器目视测试、项目功能实测或用户验收；这些结果需独立汇报。'
    }
    report=target.with_suffix('.report.json')
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'status':result['status'],'html':str(target),'report':str(report),
                      'chapters':statistics['chapters'],'svg':statistics['svg_diagrams'],
                      'fallback':statistics['fallback_diagrams'],
                      'errors':errors,'warnings':warnings},ensure_ascii=False,indent=2))
    if errors:raise RuntimeError('HTML 对照检查 FAIL；保留文件供排查，不能向用户声称生成验收通过')
    return result


def main():
    p=argparse.ArgumentParser(description='在 MD 检查通过后构建单文件离线 HTML')
    p.add_argument('markdown',help='前一阶段已经生成并经 Agent 审核的技术文档 MD')
    p.add_argument('--out-dir',help='HTML 目标目录，默认和 MD 相同')
    p.add_argument('--config',help='Agent 根据该 MD 填写的首页介绍/功能/参数 JSON')
    args=p.parse_args()
    publish(args)

if __name__=='__main__':main()
