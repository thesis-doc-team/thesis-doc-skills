#!/usr/bin/env python3
"""Static verification for offline HTML and its Markdown source.

Tests DOM, chapter links, source semantic text coverage, offline assets,
prohibited review sections, diagram source retention. This cannot replace
browser interaction/visual checks or verify project factual accuracy.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

from render_html import extract_chapters, strip_number, DEFAULT_EXCLUDES

MD = MarkdownIt('commonmark', {'html': False}).enable('table').enable('strikethrough')
FORBIDDEN = DEFAULT_EXCLUDES + ['不足与改进','风险与对策','优化建议','技术展望','技术演进','升级建议']


def norm(value):
    return ''.join(value.split()).replace('\u200b','')


def included_chapters(markdown):
    _, chapters = extract_chapters(markdown)
    return [(strip_number(label),raw) for label,raw in chapters
            if strip_number(label)!='目录' and not any(x in strip_number(label) for x in DEFAULT_EXCLUDES)]


def validate(path, source_path=None):
    content=Path(path).read_text('utf-8')
    soup=BeautifulSoup(content,'html.parser')
    errors=[];warnings=[]
    required=['#overview','#site-nav','#search-input','#progress','#sidebar','#menu-btn',
              '.hero','.feature-grid','.overview-grid','.chapter','.chapter-contents']
    for q in required:
        if soup.select_one(q) is None:errors.append('缺少关键页面元素 '+q)
    sections=soup.select('section.chapter')
    nav=soup.select('.nav-chapter')
    if len(sections)!=len(nav):errors.append(f'导航章节 {len(nav)} 与正文章节 {len(sections)} 数量不一致')
    expected=[str(i) for i in range(1,len(sections)+1)]
    nums=[n.get('data-chapter') for n in sections]
    if nums!=expected:errors.append('章节编号不连续或顺序异常 '+str(nums))
    navnums=[n.get('data-chapter-link') for n in soup.select('[data-chapter-link]')]
    if navnums!=expected:errors.append('侧边导航章节链接顺序异常 '+str(navnums))
    ids=[tag['id'] for tag in soup.select('[id]')]
    duplicates=[x for x,n in Counter(ids).items() if n>1]
    if duplicates:errors.append('HTML 重复 ID '+str(duplicates))
    available=set(ids)
    for a in soup.select('a[href^="#"]'):
        ref=a.get('href','')[1:]
        if ref and ref not in available:errors.append('锚点目标不存在 #'+ref)
    for el in soup.select('section.chapter h2,section.chapter h3,.section-label h2,.feature-card h3,.overview-card h3,.nav-link-text'):
        if any(term in el.get_text(' ',strip=True) for term in FORBIDDEN):
            errors.append('用户展示中出现越界章节：'+el.get_text(' ',strip=True))
    if re.search(r'@@[A-Z_]+@@',content):errors.append('存在未替换模板占位符')
    for el in soup.select('link[href],script[src],img[src],iframe[src],source[src]'):
        url=el.get('href') or el.get('src') or ''
        if url and not url.startswith(('data:','#')):
            errors.append('存在 HTML 外部依赖：'+url[:90])
    for el in soup.select('svg image[href],svg use[href],svg image[xlink\\:href],svg use[xlink\\:href]'):
        url=el.get('href') or el.get('xlink:href') or ''
        if url and not url.startswith('#'):errors.append('SVG 引用了外部资产：'+url[:90])
    if soup.select('.diagram-fallback'):
        warnings.append(f'存在 {len(soup.select(".diagram-fallback"))} 张未生成 SVG 的流程图，展示为原文代码')
    if len(sections)<1:errors.append('没有有效的正文章节')
    if len(sections)<=2:warnings.append('正文少于三章，请确认项目资料范围')
    # Verify that source MD is the sole source of full chapter content.
    parity_checked=parity_missing=0
    if source_path:
        source=Path(source_path).read_text('utf-8-sig')
        chapters=included_chapters(source)
        if len(chapters)!=len(sections):
            errors.append(f'MD 有 {len(chapters)} 章，但 HTML 有 {len(sections)} 章')
        for index, ((label,raw),html_section) in enumerate(zip(chapters,sections),1):
            heading=html_section.select_one('h2')
            if not heading or strip_number(heading.get_text(' ',strip=True))!=label:
                errors.append(f'第 {index} 章标题不匹配：{label}')
            md_soup=BeautifulSoup(MD.render(raw),'html.parser')
            html_text=norm(html_section.get_text(' ',strip=False))
            for item in md_soup.select('p,li,td,th,pre,blockquote'):
                # Compare text atoms, not raw syntax; font and layout may differ.
                if item.find_parent(['li','blockquote','pre']) and item.name not in ('pre',):
                    continue
                txt=norm(item.get_text(' ',strip=False))
                if len(txt)<2:continue
                parity_checked+=1
                if txt not in html_text:
                    parity_missing+=1
                    errors.append(f'第 {index} 章有原文内容未找到：'+txt[:80])
            src_subs=[strip_number(el.get_text(' ',strip=True)) for el in md_soup.select('h3')]
            dst_subs=[re.sub(r'^\d+\.\d+\s*','',el.get_text(' ',strip=True)) for el in html_section.select('h3')]
            if src_subs!=dst_subs:errors.append(f'第 {index} 章小节标题缺失或顺序改变')
        orig_mermaid=sum(len(re.findall(r'^```mermaid\s*$', raw,re.M|re.I)) for _,raw in chapters)
        if orig_mermaid!=(len(soup.select('.diagram-card'))):
            errors.append(f'原文 {orig_mermaid} 张 Mermaid，页面 {len(soup.select(".diagram-card"))} 张图卡')
        if parity_missing:errors.append(f'正文语义对照：{parity_missing}/{parity_checked} 段未匹配')
    info={
        'chapters':len(sections), 'nav_links':len(nav),
        'tables':len(soup.select('section.chapter table')),
        'svg_diagrams':len(soup.select('.vector-diagram svg')),
        'fallback_diagrams':len(soup.select('.diagram-fallback')),
        'source_atoms_checked':parity_checked,'source_atoms_missing':parity_missing,
    }
    return errors,warnings,info


def main():
    p=argparse.ArgumentParser()
    p.add_argument('html')
    p.add_argument('--md',help='Original generated Markdown file for chapter and content parity check')
    p.add_argument('--json-out',type=Path)
    args=p.parse_args()
    errors,warnings,info=validate(args.html,args.md)
    result={'status':'FAIL' if errors else ('WARN' if warnings else 'PASS'),
            'errors':errors,'warnings':warnings,'statistics':info}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True,exist_ok=True)
        args.json_out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
