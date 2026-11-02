#!/usr/bin/env python3
"""Static verification for offline HTML and its Markdown source.

Tests DOM, chapter links, source semantic text coverage, offline assets,
prohibited review sections, diagram source retention, and — as a hard gate
against "SVG rendered broken but checks stayed green" — per-diagram render
content assertions (style closure, label survival, font-size proxy) plus a
template CSS scope lint. This cannot replace browser interaction/visual
checks or verify project factual accuracy.
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
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

# ---- SVG 渲染内容断言 + 模板 CSS lint 的共同规则 ----
# 页面样式禁止裸写的元素选择器：它们会泄漏进内嵌 SVG 内部（foreignObject 标签、
# path/rect 图元），把 Mermaid/Graphviz 自己的配色冲掉。带组件 class/id/属性
# 作用域的（如 .chapter-contents p、.vector-diagram svg）合法。
CSS_FORBIDDEN_ELEMENTS = {'svg', 'path', 'rect', 'foreignobject', 'div', 'span', 'p'}
# 字号可读性代理估算的名义正文宽度（px）：整图必须全局显示、不设滚动条后，
# 图宽按 viewBox 自然宽与容器宽取小，字号同比例缩放。
NOMINAL_CONTENT_WIDTH_PX = 1080.0
MIN_READABLE_FONT_PX = 9.0


def norm(value):
    return ''.join(value.split()).replace('\u200b','')


def included_chapters(markdown):
    _, chapters = extract_chapters(markdown)
    return [(strip_number(label),raw) for label,raw in chapters
            if strip_number(label)!='目录' and not any(x in strip_number(label) for x in DEFAULT_EXCLUDES)]


def mermaid_sources(markdown):
    """Mermaid 源块，顺序与 render_html/diagram_svg 完全一致（含图章节内按出现序）。"""
    sources=[]
    for _,raw in included_chapters(markdown):
        sources.extend(re.findall(r'^```mermaid\s*\n([\s\S]*?)\n```\s*$',raw,re.M|re.I))
    return sources


# ---------- 模板 CSS lint（防样式泄漏进图 / 防压缩滚动伪象） ----------

def strip_css_comments(css):
    return re.sub(r'/\*[\s\S]*?\*/','',css)


def css_rule_blocks(css):
    """按花括号配平切出顶层 (选择器或 @at-rule 头, 规则体)。"""
    css=strip_css_comments(css)
    i,n=0,len(css)
    while i<n:
        j=css.find('{',i)
        if j<0:break
        prelude=css[i:j].strip()
        depth,k=1,j+1
        while k<n and depth:
            if css[k]=='{':depth+=1
            elif css[k]=='}':depth-=1
            k+=1
        yield prelude,css[j+1:k-1]
        i=k


def _selector_is_unscoped(sel):
    """无 class/id/属性作用域、且末端是 svg/path/rect/foreignObject/div/span/p。"""
    if re.search(r'[.#\[]',sel):
        return False
    bare=re.sub(r'::?[^(]*','',sel).strip()
    m=re.match(r'^([A-Za-z][\w-]*)',bare)
    return bool(m) and m.group(1).lower() in CSS_FORBIDDEN_ELEMENTS


def check_css_scope(css, origin='模板 CSS'):
    """页面样式里未加作用域的 svg/path/rect/foreignObject/div/span/p 元素选择器 → ERROR。

    这类选择器会命中内嵌 SVG 内部元素（含 foreignObject 里的标签 HTML），
    把图形自己的 <style> 配色/布局冲掉。出新规则必须限定作用域。
    """
    errors=[]
    for prelude,body in css_rule_blocks(css):
        if prelude.startswith('@'):
            if prelude.lower().startswith(('@media','@supports')):
                errors.extend(check_css_scope(body,origin))
            continue
        for sel in prelude.split(','):
            if _selector_is_unscoped(sel):
                errors.append(f'{origin} 出现未加作用域的元素选择器「{sel.strip()}」——会泄漏进 SVG 图内部；svg/path/rect/foreignObject/div/span/p 选择器必须带组件 class/id/属性作用域')
    return errors


def _targets_diagram(prelude):
    return bool(re.search(r'vector-diagram|diagram-card',prelude) or re.search(r'(^|[^\w.-])svg([^\w-]|$)',prelude))


def check_diagram_display(css, origin='模板 CSS'):
    """图区必须全局显示（用户硬性要求）：禁止滚动条、禁止压缩、禁止最小宽溢出。

    事故根因③：`.vector-diagram svg{max-height:685px}` 把纵向图压进 685px，
    文字缩到不可读；`overflow:auto` 又把溢出藏进内层滚动条。两者一律 ERROR。
    """
    errors=[]
    for prelude,body in css_rule_blocks(css):
        if prelude.startswith('@'):
            if prelude.lower().startswith(('@media','@supports')):
                errors.extend(check_diagram_display(body,origin))
            continue
        if not _targets_diagram(prelude):
            continue
        for m in re.finditer(r'overflow\s*:\s*(auto|scroll|hidden)|max-height\s*:|min-width\s*:',body):
            decl=m.group(0).split(':')[0].strip()
            if decl=='overflow' and m.group(1)=='hidden' and 'vector-diagram' not in prelude and not re.search(r'(^|[^\w.-])svg([^\w-]|$)',prelude):
                continue  # .diagram-card 的圆角裁切可以，图内容本身不会溢出
            errors.append(f'{origin}：图区规则「{prelude[:70]}」含「{m.group(0).split(";")[0].strip()}」——流程图必须全局显示，禁止内层滚动条/高度压缩/最小宽溢出')
    return errors


# ---------- 每幅 SVG 的渲染内容断言（事故根因①②③的特征签名） ----------

def svg_style_closure(svg_soup):
    """样式闭合：<style> 选择器与 url(#…) 引用必须命中本 SVG 自己的 id 集。

    根因①特征：id 前缀化后 <style> 文本没同步替换 → 选择器指向不存在的旧 id
    （孤立引用），配色全部失配、图形回退默认黑。Mermaid 产物还以根 id 起选择器，
    根 id 不被样式覆盖同样异常。
    """
    root=svg_soup if getattr(svg_soup,'name',None)=='svg' else svg_soup.find('svg')
    ids={el.get('id') for el in svg_soup.select('[id]') if el.get('id')}
    # bs4 的 element.select 不含元素自身：根 svg 的 id 必须显式入集
    if root is not None and root.get('id'):
        ids.add(root.get('id'))
    style_texts=[s.get_text() for s in svg_soup.select('style')]
    refs={}
    for css in style_texts:
        for prelude,body in css_rule_blocks(css):
            if prelude.startswith('@'):
                continue
            for m in re.finditer(r'#([A-Za-z_][\w-]*)',prelude):
                refs.setdefault(m.group(1),'style-selector')
            for m in re.finditer(r'url\(\s*[\'"]?#([A-Za-z_][\w-]*)',body):
                refs.setdefault(m.group(1),'style-url')
    for m in re.finditer(r'url\(\s*[\'"]?#([A-Za-z_][\w-]*)',str(svg_soup)):
        refs.setdefault(m.group(1),'attr-url')
    orphans=sorted(r for r in refs if r not in ids)
    root_id=(root.get('id') if root else None)
    if style_texts and root_id:
        covered=any(re.search(r'#'+re.escape(root_id)+r'(?![\w-])',prelude)
                    for css in style_texts for prelude,_ in css_rule_blocks(css) if not prelude.startswith('@'))
    else:
        covered=None  # Graphviz 产物无 <style>，跳过该 Mermaid 特征项
    return {'refs_total':len(refs),'orphan_refs':orphans,'root_id_covered':covered,
            'style_closure_ok':not orphans and covered is not False}


def mermaid_label_texts(source):
    """从 Mermaid 源块提取节点/边标签文本（去转义），供逐条存活核对。"""
    labels=[]
    def add(raw):
        text=re.sub(r'<br\s*/?>','\n',str(raw),flags=re.I)
        text=re.sub(r'#(\d+);',lambda m:chr(int(m.group(1))) if int(m.group(1))<0x110000 else '',text)
        for part in text.split('\n'):
            part=part.strip().strip('"\'').strip()
            part=re.sub(r'\\(.)',r'\1',part).strip()
            if part:labels.append(part)
    for raw_line in source.splitlines():
        line=raw_line.strip()
        if not line or line.startswith('%%'):
            continue
        if re.match(r'^(flowchart|graph|end|classDef|class|style|linkStyle|click|direction|accTitle|accDescr)\b',line,re.I):
            if not re.match(r'^subgraph\b',line,re.I):
                continue
        for m in re.finditer(r'\[([^\[\]]*)\]|\{([^{}]*)\}|\(([^()]*)\)',line):
            val=next(g for g in m.groups() if g is not None)
            val=re.sub(r'^[\[\({]+|[\]\)}]+$','',val).strip()
            if val:add(val)
        for m in re.finditer(r'\|([^|]+)\|',line):
            add(m.group(1))
        for m in re.finditer(r'--\s+([^|<>{}\[\]]+?)\s+-->',line):
            add(m.group(1))
        for m in re.finditer(r'-\.\s+([^|<>{}\[\]]+?)\s+-\.->',line):
            add(m.group(1))
        for m in re.finditer(r'==\s+([^|<>{}\[\]]+?)\s+==>',line):
            add(m.group(1))
    seen=set();out=[]
    for lab in labels:
        if lab not in seen:
            seen.add(lab);out.append(lab)
    return out


def svg_label_survival(svg_soup, labels):
    """标签存活：每个源标签都必须能在 SVG 文本（text / foreignObject 文本）中命中。

    根因②特征：htmlLabels 未关闭 + 净化删掉 foreignObject → 节点文字全部消失。
    """
    text_norm=norm(svg_soup.get_text(''))
    missing=[lab for lab in labels if norm(lab) and norm(lab) not in text_norm]
    total=len([lab for lab in labels if norm(lab)])
    hit=total-len(missing)
    return {'labels_total':total,'labels_missing':missing,
            'label_hit_rate':round(hit/total,3) if total else None}


def estimate_min_font_px(svg_soup, page_css):
    """尺寸与可读性代理：按 viewbox 比例与 CSS 约束估算实际渲染最小字号。

    根因③代理信号：纵向图被 max-height 压扁时缩放系数骤降，估算字号 < 9px。
    """
    root=svg_soup if getattr(svg_soup,'name',None)=='svg' else svg_soup.find('svg')
    # html.parser 会把属性名小写（viewBox→viewbox），两种写法都取
    vb=((root.get('viewBox') or root.get('viewbox') or '')).split() if root else []
    if len(vb)!=4:
        return None
    vb_w,vb_h=float(vb[2]),float(vb[3])
    if vb_w<=0 or vb_h<=0:
        return None
    sizes=[]
    css_pool=[s.get_text() for s in svg_soup.select('style')]+[root.get('style') or '']
    for css in css_pool:
        for m in re.finditer(r'font-size:\s*([\d.]+)\s*(px|pt)?',css):
            sizes.append(float(m.group(1))*(1.333 if m.group(2)=='pt' else 1.0))
    for el in svg_soup.select('[font-size]'):
        m=re.match(r'([\d.]+)\s*(px|pt)?',str(el.get('font-size')))
        if m:sizes.append(float(m.group(1))*(1.333 if m.group(2)=='pt' else 1.0))
    min_font=min(sizes) if sizes else 12.0
    caps=[float(x) for x in re.findall(r'max-width:\s*([\d.]+)px',root.get('style') or '')] if root else []
    rendered_w=min([vb_w,NOMINAL_CONTENT_WIDTH_PX]+caps)
    scale=rendered_w/vb_w
    for prelude,body in css_rule_blocks(page_css):
        if prelude.startswith('@'):
            continue
        if _targets_diagram(prelude):
            m=re.search(r'max-height:\s*([\d.]+)px',body)
            if m:
                scale=min(scale,float(m.group(1))/vb_h)
    return round(min_font*scale,2)


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
    # ---- SVG 渲染内容断言（防"渲染损坏却 PASS"）+ 模板 CSS lint ----
    page_css='\n'.join(s.get_text() for s in soup.find_all('style') if not s.find_parent('svg'))
    css_scope_errors=check_css_scope(page_css)+check_diagram_display(page_css)
    errors.extend(css_scope_errors)
    sources=mermaid_sources(Path(source_path).read_text('utf-8-sig')) if source_path else None
    if source_path is None and soup.select('.vector-diagram svg'):
        warnings.append('未提供 MD 源：SVG 标签存活断言未执行，请用 --md 传入生成 MD 后复查')
    diagram_checks=[]
    for idx,card in enumerate(soup.select('.diagram-card'),1):
        svg=card.select_one('.vector-diagram svg')
        if svg is None:
            diagram_checks.append({'index':idx,'svg':False,'note':'源码回退，未生成 SVG（WARN，不得宣称完成图形化）'})
            continue
        record={'index':idx,'svg':True}
        closure=svg_style_closure(svg)
        record.update(closure)
        record['style_closure']='OK' if closure['style_closure_ok'] else 'FAIL'
        if closure['orphan_refs']:
            errors.append(f'第 {idx} 图样式不闭合：{len(closure["orphan_refs"])} 个孤立 # 引用 {closure["orphan_refs"][:6]}（id 前缀化后 <style> 未同步替换的典型特征，配色将全部失配）')
        if closure['root_id_covered'] is False:
            errors.append(f'第 {idx} 图根元素 id 未被自身 <style> 覆盖（Mermaid 产物特征被破坏）')
        record['text_count']=len(svg.select('text'))
        record['foreignobject_count']=len(svg.select('foreignobject'))
        if sources is not None and idx<=len(sources):
            survival=svg_label_survival(svg,mermaid_label_texts(sources[idx-1]))
            record.update(survival)
            if survival['labels_missing']:
                errors.append(f'第 {idx} 图标签未全部存活：{len(survival["labels_missing"])}/{survival["labels_total"]} 个标签未在 SVG 文本中找到 {survival["labels_missing"][:6]}（文字被净化剥掉的典型特征）')
        else:
            record['labels_total']=None;record['labels_missing']=[];record['label_hit_rate']=None
        font=estimate_min_font_px(svg,page_css)
        record['estimated_min_font_px']=font
        if font is not None and font<MIN_READABLE_FONT_PX:
            warnings.append(f'第 {idx} 图估算最小字号约 {font}px < {MIN_READABLE_FONT_PX}px：疑似被 CSS 压缩或原图过宽，可读性差')
        if record['foreignobject_count']:
            warnings.append(f'第 {idx} 图含 foreignObject：htmlLabels 配置可能未生效（mmdc 需顶层 "htmlLabels": false），核对标签渲染')
        diagram_checks.append(record)
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
        'diagram_checks':diagram_checks,
        'css_scope_errors':len(css_scope_errors),
    }
    return errors,warnings,info


def write_audit(html_path, result):
    """把校验证据落成 <html 同名>.audit.json：record-use 登记前的必备证据文件。"""
    audit=Path(html_path).with_name(Path(html_path).stem+'.audit.json')
    audit.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8',newline='\n')
    return audit


def main():
    p=argparse.ArgumentParser()
    p.add_argument('html')
    p.add_argument('--md',help='Original generated Markdown file for chapter and content parity check')
    p.add_argument('--json-out',type=Path)
    p.add_argument('--no-audit',action='store_true',help='不生成 <html>.audit.json 证据文件')
    args=p.parse_args()
    errors,warnings,info=validate(args.html,args.md)
    result={'status':'FAIL' if errors else ('WARN' if warnings else 'PASS'),
            'errors':errors,'warnings':warnings,'statistics':info}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True,exist_ok=True)
        args.json_out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    if not args.no_audit:
        audit=write_audit(args.html,result)
        result.setdefault('audit_file',str(audit))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
