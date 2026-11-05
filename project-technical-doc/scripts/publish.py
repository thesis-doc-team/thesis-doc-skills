#!/usr/bin/env python3
"""Mandatory second stage: validated generated MD -> offline user-facing HTML.

This command must be called only after the Agent has written an evidence-based
project Markdown document. It does not inspect or modify the source repository.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from check_markdown import check
from check_physical_modules import check as check_physical_modules
from diagram_svg import render_diagrams, engine_status
from render_html import build
from screenshot_audit import find_browser, pixel_probe_svg, render_probe_page
from validate_html import validate, write_audit


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
    physical=check_physical_modules(md)
    if physical['errors']:
        raise RuntimeError('实物模块清单校验 FAIL（'+Path(physical['manifest']).name
                           +' 必须与技术文档 MD 同级、定名不加版本号）：'
                           +'；'.join(physical['errors'][:5])
                           +'。请按 SKILL「实物模块清单契约」生成/修订后再发布')
    # Pre-flight: announce missing SVG engines up front, not at delivery time.
    engines=engine_status()
    if not engines['svg_capable']:
        print('WARN：未检测到 Mermaid CLI / Graphviz dot，流程图将保留可展开 Mermaid 源码回退（不出 SVG）。'
              '安装命令：'+str(engines['install_hint'])+'；装好后重跑 publish 会生成新版本 HTML 补图，不覆盖旧版。',
              file=sys.stderr)
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
        hint='' if engines['svg_capable'] else f'；当前机器无 SVG 引擎（{engines["install_hint"]}），装好后重跑 publish 生成新版本 HTML 补图，不覆盖旧版'
        warnings.append(f'{len(diagram_fail)}/{len(diagrams)} 张 Mermaid 图未转换为 SVG；页面保留可读原文'+hint)
    # ---- 报告证据化：每个 diagram 附渲染内容断言 + （有浏览器时）像素/渲染探针 ----
    # 内容断言失败已进入 errors → 顶层 status 必为 FAIL，报告自身就能暴露事故。
    ev_by_index={e.get('index'):e for e in statistics.get('diagram_checks',[])}
    svg_texts={}
    page_soup=BeautifulSoup(target.read_text('utf-8'),'html.parser')
    for i,card in enumerate(page_soup.select('.diagram-card'),1):
        svg=card.select_one('.vector-diagram svg')
        if svg is not None:svg_texts[i]=str(svg)
    browser=find_browser()
    render_by_index={}
    if browser and svg_texts:
        try:
            render_result,render_err=render_probe_page(target,browser,work=build_dir/'probe')
            if render_err:
                warnings.append('图区渲染探针未执行：'+render_err)
            else:
                render_by_index={d.get('index'):d for d in render_result.get('diagrams',[])}
        except Exception as exc:
            warnings.append(f'图区渲染探针异常未执行：{exc}')
    for item in diagrams:
        ev=ev_by_index.get(item['index'],{})
        item['mmdc_version']=engines.get('mmdc_version')
        item['text_count']=ev.get('text_count')
        item['label_hit_rate']=ev.get('label_hit_rate')
        item['style_closure']=ev.get('style_closure')
        item['estimated_min_font_px']=ev.get('estimated_min_font_px')
        if item['index'] not in svg_texts:
            item['pixel_probe']={'available':False,'reason':'未生成 SVG，像素证据不适用'}
            continue
        if not browser:
            item['pixel_probe']={'available':False,'reason':'未找到 Chrome/Edge，pixel_probe 未执行'}
            continue
        try:
            probe=pixel_probe_svg(svg_texts[item['index']],browser,build_dir/'probe')
        except Exception as exc:
            probe={'available':False,'reason':f'pixel_probe 异常未执行：{exc}'}
        if render_by_index.get(item['index']):
            probe['computed']=render_by_index[item['index']]
        item['pixel_probe']=probe
    result={
        'status':'FAIL' if errors else ('WARN' if warnings else 'PASS'),
        'created_at':datetime.now().astimezone().isoformat(timespec='seconds'),
        'generated_markdown':str(md), 'generated_html':str(target),
        'markdown_sha256':sha256(md), 'html_sha256':sha256(target),
        'configuration':str(Path(args.config).resolve()) if args.config else None,
        'physical_modules':physical,
        'svg_engines':engines,
        'render':render_info, 'diagrams':diagrams, 'html_validation':statistics,
        'errors':errors,'warnings':warnings,
        'reminder':'自动校验不等于网页浏览器目视测试、项目功能实测或用户验收；这些结果需独立汇报。'
    }
    report=target.with_suffix('.report.json')
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    # <html>.audit.json：record-use 登记前必须存在的证据文件（SKILL.md 硬规则）。
    audit=write_audit(target,result)
    print(json.dumps({'status':result['status'],'html':str(target),'report':str(report),'audit':str(audit),
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
