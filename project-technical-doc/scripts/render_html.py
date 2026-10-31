#!/usr/bin/env python3
"""Render offline HTML from the approved output Markdown, never from independent source claims.
Content-specific homepage cards are curated in optional showcase configuration.
"""
import argparse
import base64
import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
MD = MarkdownIt('commonmark', {'html': False, 'breaks': False}).enable('table').enable('strikethrough')
DEFAULT_EXCLUDES = [
    '已知问题与改进建议', '内部评审', '内部问题清单', '缺陷清单',
    '研发复盘', '内部改进建议', '风险与缺陷清单',
    '存在的问题', '优化方向', '未来展望', '后续规划', '改进建议',
]


def escaped(s):
    return html.escape(str(s), quote=True)


def source_slug(text):
    s=re.sub(r'<[^>]*>','',text).lower().strip()
    s=re.sub(r'[`*_~]','',s)
    s=''.join(ch for ch in s if ch.isalnum() or ch in ' -_')
    return re.sub(r'\s+','-',s)


def strip_number(s):
    return re.sub(r'^\s*\d+(?:\.\d+)*[\.、]?\s*', '', s).strip()


def extract_chapters(text):
    headings = list(re.finditer(r'^##\s+(.+?)\s*$', text, re.M))
    if not headings:
        raise ValueError('未找到 Markdown 二级标题（## 章节）；请先规范标题层级。')
    return text[:headings[0].start()], [
        (m.group(1), text[m.start():(headings[i+1].start() if i+1 < len(headings) else len(text))])
        for i, m in enumerate(headings)
    ]


def svg_markup(s):
    # Best effort: local SVG is static; strip scripts/events and external links.
    raw = re.search(r'<svg\b[\s\S]*?</svg\s*>', s, re.I)
    if not raw:
        return None
    soup = BeautifulSoup(raw.group(0), 'html.parser')
    for element in soup.select('script,iframe,object,embed'):
        element.decompose()
    for element in soup.find_all(True):
        for attr in list(element.attrs):
            v = element.attrs[attr]
            if attr.lower().startswith('on') or (attr.lower() in ('href','xlink:href') and ('http:' in str(v) or 'https:' in str(v) or 'javascript:' in str(v))):
                del element.attrs[attr]
    svg = soup.find('svg')
    return str(svg) if svg else None


def prefix_svg_ids(svg_text, prefix):
    """Make reusable Graphviz/Mermaid SVG IDs unique across inline diagrams."""
    soup=BeautifulSoup(svg_text,'html.parser')
    renames={}
    for el in soup.select('[id]'):
        old=el.get('id')
        new=prefix+old
        renames[old]=new
        el['id']=new
    for el in soup.find_all(True):
        for attr, val in list(el.attrs.items()):
            if attr=='id':continue
            if isinstance(val,str):
                for old,new in renames.items():
                    val=val.replace('url(#'+old+')','url(#'+new+')')
                    if attr in ('href','xlink:href') and val=='#'+old:val='#'+new
                el[attr]=val
    for el in soup.find_all('style'):
        if el.string:
            css=el.string
            # 词边界替换：只改 #id 选择器引用，不误伤 #fff 等颜色字面量；
            # 按旧 id 长度降序，避免短 id 抢先截断长 id。
            for old,new in sorted(renames.items(), key=lambda kv: len(kv[0]), reverse=True):
                css=re.sub(r'#'+re.escape(old)+r'(?![\w-])', '#'+new, css)
            el.string.replace_with(css)
    return str(soup)


def render_chapter_md(raw, n, svgs, diagram_state, source_dir=None, anchors=None):
    # Replace diagram blocks with stable placeholders before Markdown processing.
    placeholders=[]
    def replace_diagram(m):
        diagram_state['total']+=1
        idx=diagram_state['total']
        source=m.group(1)
        svg=svgs.get(str(idx))
        if svg:
            svg=prefix_svg_ids(svg, f'diagram-{idx}-')
            d=f'<div class="vector-diagram" role="img" aria-label="技术流程图">{svg}</div>'
            diagram_state['svg']+=1
        else:
            d='<div class="diagram-fallback"><p>流程图原文（尚未生成离线 SVG 图示）</p><pre class="code-sample"><code>'+escaped(source)+'</code></pre></div>'
        fragment=(f'<figure class="diagram-card"><figcaption><span class="diagram-dot"></span>'
                  f'技术流程图 {idx} <small>依据原始 Markdown；可展开核对流程定义</small></figcaption>'
                  f'{d}<details class="diagram-source"><summary>查看原文 Mermaid 描述</summary>'
                  f'<pre class="code-sample"><code>{escaped(source)}</code></pre></details></figure>')
        placeholders.append(fragment)
        return '\n\nDIAGRAMPLC'+str(len(placeholders)-1)+'\n\n'
    content=re.sub(r'```mermaid\s*\n([\s\S]*?)\n```', replace_diagram, raw)
    rendered=MD.render(content)
    for idx, fragment in enumerate(placeholders):
        rendered=rendered.replace('<p>DIAGRAMPLC'+str(idx)+'</p>', fragment)
    soup=BeautifulSoup(rendered,'html.parser')
    main=soup.find('h2')
    if main:
        main['id']=f'sec-{n}'
        title=strip_number(main.get_text(' ',strip=True))
        main.clear(); main.append(f'{n}. {title}')
    subheads=[]
    for j,h3 in enumerate(soup.find_all('h3'),1):
        title=strip_number(h3.get_text(' ',strip=True))
        id=f'sub-{n}-{j}'
        h3['id']=id
        h3.clear(); h3.append(f'{n}.{j} {title}')
        subheads.append((id,f'{n}.{j} {title}'))
    for link in soup.select('a[href^="#"]'):
        href=link.get('href','')
        if anchors and href[1:] in anchors:link['href']='#'+anchors[href[1:]]
    for table in soup.find_all('table'):
        container=soup.new_tag('div');container['class']='table-scroll';table.wrap(container)
    for pre in soup.find_all('pre'):
        classes=pre.get('class',[])
        if 'code-sample' not in classes:classes.append('code-sample')
        pre['class']=classes
    for hr in soup.find_all('hr'):hr['class']='section-break'
    # Images referenced in a generated MD must be local and inside that MD's
    # output directory to embed safely in the stand-alone HTML. No fetching.
    if source_dir:
        root=Path(source_dir).resolve()
        for img in soup.find_all('img'):
            src=img.get('src','')
            if not src or src.startswith(('http://','https://','data:')):
                continue
            try:
                local=(root/unquote(src.split('#',1)[0].split('?',1)[0])).resolve()
                local.relative_to(root)  # rejects path traversal / outside symlink
                mime,_=mimetypes.guess_type(local.name)
                if mime not in ('image/png','image/jpeg','image/webp','image/gif'):
                    continue
                if not local.is_file() or local.stat().st_size>6*1024*1024:continue
                img['src']='data:'+mime+';base64,'+base64.b64encode(local.read_bytes()).decode('ascii')
            except (ValueError,OSError):
                pass

    kicker=f'<div class="chapter-kicker"><span class="chapter-index">{n:02d}</span><span>TECHNICAL DOCUMENTATION</span></div>'
    contents=str(soup)
    # Add the visual kicker before the actual heading.
    if main:
        original=str(main)
        contents=contents.replace(original,kicker+original,1)
    return contents, subheads


def one_line(text, max_chars=115):
    clean=re.sub(r'\s+',' ',text.strip())
    if len(clean)<=max_chars:return clean
    # Never stop a project introduction in the middle of a technical term.
    punctuation=[clean.rfind(mark,0,max_chars) for mark in ('。','；','，',';','.')]
    stop=max(punctuation)
    if stop>=int(max_chars*.45):
        return clean[:stop+1].rstrip() + ('…' if clean[stop] not in '。.' else '')
    return clean[:max_chars-1].rstrip()+'…'


def derive_lead(intro, chapters):
    # Prefer a real system-description sentence over generic application background.
    paragraphs=[]
    for _,chapter in chapters[:2]:
        soup=BeautifulSoup(MD.render(chapter),'html.parser')
        paragraphs.extend(el.get_text(' ',strip=True) for el in soup.find_all('p'))
    for t in paragraphs:
        if len(t)>28 and re.match(r'^(本系统|本项目|该系统|该项目|本设备|该平台|本平台)',t):
            return one_line(t,165)
    for t in paragraphs:
        if len(t)>28 and not t.startswith(('**','文档说明','版本与状态')):
            return one_line(t,165)
    soup=BeautifulSoup(MD.render(intro),'html.parser')
    for el in soup.find_all('p'):
        t=el.get_text(' ',strip=True)
        if len(t)>23:return one_line(t,165)
    return '以结构化章节、技术表格和流程图直观展示所提供的项目技术资料。'


def render_intro(intro):
    soup=BeautifulSoup(MD.render(intro),'html.parser')
    if soup.h1:soup.h1.decompose()
    return str(soup).strip()


def build(config, text, source_name, svgdir, source_dir=None):
    intro, rawchapters=extract_chapters(text)
    excludes=config.get('excluded_sections',DEFAULT_EXCLUDES)
    chapters=[]; removed=[]
    for label, section in rawchapters:
        title=strip_number(label)
        if title=='目录' or any(word in title for word in excludes):
            removed.append(title)
        else:
            chapters.append((title,section))
    if not chapters:raise ValueError('过滤后没有可展示的章节。')
    # Source chapter numbers are not reliable after the user-facing filter.
    # Report old references explicitly instead of silently retargeting them.
    excluded_nums=[]
    for raw_title,_ in rawchapters:
        if strip_number(raw_title) in removed:
            m=re.match(r'^(\d+)\.',raw_title)
            if m:excluded_nums.append(m.group(1))
    removed_refs=[]
    for title,raw in chapters:
        for num in excluded_nums:
            hits=re.findall(rf'(?:见|详见|参见|参考)\s*(?:第\s*)?{num}(?:\.\d+)?\s*(?:章|节)?',raw)
            if hits:removed_refs.append({'chapter':title,'excluded_number':num,'samples':hits[:4]})
    svgs={}
    if svgdir and svgdir.is_dir():
        for svg in svgdir.glob('*.svg'):
            # Use 1.svg, 2.svg etc by order of Mermaid code fences in INCLUDED chapters.
            if svg.stem.isdecimal():
                markup=svg_markup(svg.read_text(encoding='utf-8'))
                if markup:svgs[svg.stem]=markup
    title=str(config.get('title') or (re.search(r'^#\s+(.+)$',text,re.M).group(1) if re.search(r'^#\s+(.+)$',text,re.M) else source_name.replace('.md','')))
    title=strip_number(title)
    # Keep the actual project name while avoiding duplicated presentation suffixes.
    if not config.get('title'):
        title=re.sub(r'\s*[—–-]\s*(?:项目)?技术文档\s*$','',title).strip()
    subtitle=str(config.get('subtitle') or '技术可视化展示')
    lead=str(config.get('summary') or derive_lead(intro,chapters))
    brand=str(config.get('brand') or title)
    notice=str(config.get('notice') or '本页面依据提供的 Markdown 技术资料整理；页面展示不代表新增的测试或验证结论。')
    version=str(config.get('version') or '展示版')
    # Keep source MD internal links valid after adding stable site IDs.
    anchors={}
    for i,(label,raw) in enumerate(chapters,1):
        for j,match in enumerate(re.finditer(r'^###\s+(.+?)\s*$',raw,re.M),1):
            anchors[source_slug(match.group(1))]=f'sub-{i}-{j}'
        anchors[source_slug(label)]=f'sec-{i}'
    nav=[]; sections=[]; diagram_state={'total':0,'svg':0}
    for i,(label,raw) in enumerate(chapters,1):
        content, subs=render_chapter_md(raw,i,svgs,diagram_state,source_dir,anchors)
        nav.append((i,label,subs))
        hint=one_line(config.get('chapter_descriptions',{}).get(label,'本章内容依据原始技术文档呈现'),95)
        sections.append(f'<section id="chapter-{i}" class="chapter" data-chapter="{i}">'
                        f'<div class="chapter-card"><div class="chapter-top"><p>{escaped(hint)}</p></div>'
                        f'<div class="chapter-contents">{content}</div>'
                        f'<div class="chapter-footer"><a href="#overview">↑ 返回总览</a><span>CHAPTER {i:02d} / {len(chapters):02d}</span></div>'
                        f'</div></section>')
    nav_html='<a class="nav-overview active" href="#overview"><span class="nav-icon">⌂</span><span>展示总览</span></a>'
    nav_html+=f'<div class="nav-caption">文档章节 · {len(chapters)}</div>'
    for i,label,subs in nav:
        nav_html+=f'<div class="nav-chapter"><a class="nav-link" href="#chapter-{i}" data-chapter-link="{i}"><span class="nav-num">{i:02d}</span><span class="nav-link-text">{escaped(label)}</span><span class="nav-chev">›</span></a><div class="subnav">'
        for hid,sub in subs:nav_html+=f'<a href="#{hid}">{escaped(sub)}</a>'
        nav_html+='</div></div>'
    features=config.get('features',[])
    if not features:
        # Overview offers verifiable reading cues, rather than fabricating product capabilities.
        features=[{'title':t,'description':f'阅读第 {i} 章，查看相关技术资料与说明。','status':'原文内容'} for i,(t,_) in enumerate(chapters[:4],1)]
        features_label='主要章节速览'
    else:features_label='核心能力一览'
    icons=['◈','◷','▣','◉'];colors=['feature-pink','feature-lilac','feature-blue','feature-mint']
    feature_html=''
    for j,feat in enumerate(features[:4]):
        feature_html+=(f'<article class="feature-card {colors[j%4]}"><div class="feature-icon">{icons[j%4]}</div>'
                       f'<h3>{escaped(feat.get("title",""))}</h3><p>{escaped(feat.get("description",""))}</p>'
                       f'<div class="feature-status">{escaped(feat.get("status","来源：原文"))}</div></article>')
    process=config.get('process_steps',[])
    if process:process_label='系统如何工作？';process_desc='依据原始文档整理的关键步骤；不代表额外实测'
    else:
        process=[{'title':t,'description':f'第 {i} 章'} for i,(t,_) in enumerate(chapters[:4],1)]
        process_label='推荐阅读路径';process_desc='沿着原文结构逐步了解项目'
    process_html=''
    for j,step in enumerate(process[:4],1):
        process_html+=(f'<div class="process-node"><span class="node-index">{j:02d}</span>'
                      f'<h4>{escaped(step.get("title",""))}</h4><p>{escaped(step.get("description",""))}</p></div>')
    facts=config.get('facts',[])
    if facts:fact_label='关键技术参数';fact_desc='基于原文中的规格与事实'
    else:
        count_h3=sum(len(subs) for _,_,subs in nav)
        count_tables=sum(s.count('<div class="table-scroll">') for s in sections)
        facts=[{'value':len(chapters),'label':'章节数量'}, {'value':count_h3,'label':'小节数量'},
               {'value':count_tables,'label':'技术表格'}, {'value':diagram_state['total'],'label':'流程定义'}]
        fact_label='文档结构速览';fact_desc='自动统计原文展示内容'
    fact_html=''.join(f'<div class="fact"><strong>{escaped(x.get("value","—"))}</strong><span>{escaped(x.get("label",""))}</span></div>' for x in facts[:4])
    # Abstract diagram illustration: suitable for software, hardware and mixed systems.
    # Never present an imagined product shell as a real product appearance.
    art=('<div class="concept-stage" role="img" aria-label="抽象系统技术概念示意图（非真实产品图）">'
         '<div class="concept-halo"></div><div class="concept-halo ring-2"></div>'
         '<div class="concept-chip"><span class="chip-led"></span><small>TECH</small><strong>SYS</strong><em>DOCUMENT</em></div>'
         '<div class="concept-node node-a">◈ <span>INPUT</span></div>'
         '<div class="concept-node node-b">⌁ <span>PROCESS</span></div>'
         '<div class="concept-node node-c">▣ <span>OUTPUT</span></div>'
         '<span class="concept-caption">科技卡通概念示意，非真实产品或运行截图</span></div>')
    def find_link(keywords, fallback):
        for index,(label,_) in enumerate(chapters,1):
            if any(k in label for k in keywords):return '#chapter-'+str(index)
        return '#chapter-'+str(min(fallback,len(chapters)))
    template=(ROOT/'assets'/'layout.html').read_text('utf-8')
    values={
        'TITLE':escaped(title),'SUBTITLE':escaped(subtitle),'BRAND':escaped(brand),
        'LEAD':escaped(lead),'NOTICE':escaped(notice),'VERSION':escaped(version),
        'NAV':nav_html,'CHAPTERS': '\n'.join(sections),'FEATURES':feature_html,
        'INTRO':render_intro(intro),'PROCESS':process_html,'FACTS':fact_html,
        'ART':art,'COUNT':str(len(chapters)),'FEATURES_LABEL':escaped(features_label),
        'PROCESS_LABEL':escaped(process_label),'PROCESS_DESC':escaped(process_desc),
        'FACT_LABEL':escaped(fact_label),'FACT_DESC':escaped(fact_desc),
        'FEATURES_LINK': find_link(['功能','能力'],1),
        'ARCH_LINK': find_link(['总体架构','系统架构','技术架构'],2),
        'FLOW_LINK': find_link(['关键流程','运行流程','业务流程'],3),
    }
    out=template
    for key,value in values.items():out=out.replace('@@'+key+'@@',value)
    unresolved=re.findall(r'@@[A-Z_]+@@',out)
    if unresolved:raise ValueError(f'模板占位符未替换：{unresolved}')
    return out, {'source':source_name,'title':title, 'chapters':len(chapters),
                 'excluded_chapters':removed, 'cross_references_to_review':removed_refs, 'mermaid_count':diagram_state['total'],
                 'svg_count':diagram_state['svg'], 'notes':[
                     '缺失 SVG 的 Mermaid 以原文代码回退显示；不能宣称完成图形可视化。',
                     '如过滤章节后源文仍包含跨章文字引用，需要人工复核、最小修改。',
                     '首页特性、流程与技术参数应由 AI 从原文核对后写入配置文件。'
                 ]}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('markdown',help='Markdown source file')
    ap.add_argument('--config', type=Path,help='Optional project JSON with verified overview excerpts')
    ap.add_argument('--svgs', type=Path,help='Optional folder with 1.svg, 2.svg, ... for Mermaid blocks')
    ap.add_argument('--out',type=Path,help='Output HTML file')
    args=ap.parse_args()
    source=Path(args.markdown)
    cfg=json.loads(args.config.read_text('utf-8')) if args.config else {}
    html_out,report=build(cfg,source.read_text('utf-8'),source.name,args.svgs,source.parent)
    target=args.out or source.with_name(source.stem+'_用户展示.html')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(html_out,'utf-8')
    reportpath=target.with_suffix('.report.json')
    reportpath.write_text(json.dumps(report,indent=2,ensure_ascii=False),'utf-8')
    print('HTML:', target, '| Bytes:',target.stat().st_size)
    print('Report:',reportpath)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
