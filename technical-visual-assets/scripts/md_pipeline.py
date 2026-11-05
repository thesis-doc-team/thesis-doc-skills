#!/usr/bin/env python3
"""Markdown-first, offline-only visual resource pipeline for v1.3.

The project technical MD is the only authority for technical facts. User photos
are supplied through a project-isolated upload directory and remain unapproved
until reviewed. No network I/O or online image discovery is present.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SCHEMA = 1
RESOURCE_TYPES = ('system-framework', 'functional-architecture', 'flowchart',
                  'module-photo', 'test-result', 'data-table')
HEAD = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
TABLE_SEPARATOR = re.compile(r'^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$')
FENCE = re.compile(r'^\s*```\s*([^`\s]*)\s*$')
IMAGE_LINK = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
TREE = re.compile(r'[├└]──|\|--')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha(text):
    return sha256(text if isinstance(text, bytes) else text.encode('utf-8')).hexdigest()


def rid(category, content):
    return 'RES-' + sha(category+'\n'+content)[:16].upper()


def atomic_write(path: Path, payload: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    try:
        temp.write_text(payload, encoding='utf-8')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def json_read(path):
    return json.loads(path.read_text('utf-8'))


def validate_project(root, md_file, project_id=None):
    root = Path(root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('项目根目录不是文件夹')
    p = root / 'project-assets' / 'project.json'
    if not p.is_file():
        raise ValueError('未发现 project-assets/project.json；先初始化真实项目')
    meta = json_read(p)
    pid = meta.get('project_id')
    if meta.get('schema_version') != 1 or not isinstance(pid, str) or not pid:
        raise ValueError('项目元信息 schema_version/project_id 无效')
    if project_id is not None and project_id != pid:
        raise ValueError('project_id 不一致：禁止跨项目操作')
    md = Path(md_file).expanduser().resolve(strict=True)
    allowed = (root/'deliverables'/'technical-document').resolve()
    if not md.is_file() or md.suffix.lower() != '.md' or not md.is_relative_to(allowed):
        raise ValueError('技术 MD 必须放在本项目 deliverables/technical-document/ 下')
    if md.stat().st_size > 8_000_000:
        raise ValueError('单份技术 MD 超过8MB')
    data = md.read_bytes()
    body = data.decode('utf-8-sig')
    return root, md, pid, body, sha(data)


def heading_category(title, context, kind):
    t = (title + ' ' + context).casefold()
    local = title.casefold()
    if '功能树' in local or '功能架构' in local or '功能结构' in local or '功能模块划分' in local:
        return 'functional-architecture'
    if any(s in local for s in ('流程', '时序', '运行时数据流', '消息流', '数据流', '启动', '工作过程')):
        return 'flowchart'
    if any(s in local for s in ('拓扑', '总体架构', '系统架构', '系统框架', '分层结构', '组件关系')):
        return 'system-framework'
    if kind == 'tree' and '功能' in t:
        return 'functional-architecture'
    if any(s in t for s in ('系统总体架构', '整体架构', '系统架构', '系统框架')) and '流程' not in local:
        return 'system-framework'
    if kind == 'mermaid' and any(s in t for s in ('关键流程', '数据流', '业务流程')):
        return 'flowchart'
    return 'unclassified'


def extract_markdown(body, path, hash_):
    lines = body.splitlines()
    sections = []
    headings = []
    for i, line in enumerate(lines,1):
        h = HEAD.match(line)
        if h:
            level, label = len(h.group(1)), h.group(2).strip()
            headings = [h for h in headings if h[0] < level]
            headings.append((level, label))
        sections.append(tuple(headings))

    items = []
    def add(category, kind, content, start, end, title, notes=None):
        if not content.strip():return
        context = ' / '.join(x[1] for x in sections[start-1])
        category = category or heading_category(title, context,kind)
        if category == 'unclassified':
            status = 'needs-classification'
        else:
            status = 'candidate-needs-review'
        evidence = {'technical_md':path,'technical_md_sha256':hash_,
                    'start_line':start,'end_line':end,'section':context}
        items.append({'id':rid(category, content), 'kind':kind,'category':category,
                      'title':title,'status':status,'review_status':'pending-review',
                      'source':evidence,'content_sha256':sha(content),
                      'content':content, 'notes':notes or '', 'fact_source':'technical-md-only',
                      'source_authority':'technical-markdown','created_at':now()})

    i = 0
    while i < len(lines):
        start = i
        fence = FENCE.match(lines[i])
        if fence:
            lang = fence.group(1).casefold()
            j = i+1
            while j<len(lines) and not FENCE.match(lines[j]):j+=1
            if j==len(lines):
                i+=1;continue
            content = '\n'.join(lines[i+1:j]).strip()+'\n'
            title = sections[i][-1][1] if sections[i] else '未命名技术图'
            context = ' / '.join(h[1] for h in sections[i])
            if lang == 'mermaid':
                add(heading_category(title, context,'mermaid'),'mermaid',content,start+1,j+1,title)
            elif (lang in ('','text','plain') and TREE.search(content)
                  and len(content.splitlines())<=55):
                # A functional ASCII tree is a DRAFT source, not a verified chart.
                add(heading_category(title,context,'tree'),'ascii-tree',content,start+2,j,title,
                    'ASCII 功能树须核对每条父子关系后才能批准。')
            i=j+1;continue
        line=lines[i]
        if line.lstrip().startswith('|') and i+1<len(lines) and TABLE_SEPARATOR.match(lines[i+1]):
            j=i+2
            while j<len(lines) and lines[j].lstrip().startswith('|'):j+=1
            content='\n'.join(lines[i:j]).strip()+'\n'
            title=sections[i][-1][1] if sections[i] else '数据表格'
            if j-i>=4 and len(content)<65_000:
                # Test plans are never misrepresented as measured results.
                cat='data-table'
                if re.search(r'测试结果|实测结果|实验结果', title) and not re.search(
                        r'未运行|未测试|待测试|测试计划|预期', content + '\n' + body[:2000]):
                    cat='test-result'
                add(cat,'markdown-table',content,start+1,j,title)
            i=j;continue
        # Local Markdown images can be catalog candidates, but are not automatically
        # called complete hardware modules; they require visual inspection.
        for m in IMAGE_LINK.finditer(line):
            url=m.group(2).strip().split(' ')[0].strip('<>')
            if re.match(r'^[a-z]+://',url,re.I):
                continue  # Non-local images are never fetched or catalogued.
            if url and not url.startswith(('data:', '/')) and '..' not in Path(url).parts:
                title=m.group(1).strip() or (sections[i][-1][1] if sections[i] else '本地图像')
                add(None,'local-image-reference',url,start+1,start+1,title,
                    '引用路径待用户确认；图片内容必须单独目检，不能按文件名批准。')
        i+=1
    return items


def catalog_path(root):
    return root/'project-assets'/'resource-catalog'/'index.json'


def load_catalog(root,pid):
    p=catalog_path(root)
    if not p.exists():
        return {'schema_version':1,'project_id':pid,'updated_at':now(),'items':[]}
    d=json_read(p)
    if d.get('project_id')!=pid or d.get('schema_version')!=1 or not isinstance(d.get('items'),list):
        raise ValueError('resource-catalog 项目ID/结构不匹配')
    return d


def save_catalog(root,data):
    data['updated_at']=now()
    atomic_write(catalog_path(root),json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def find_legacy_vis(root,content):
    vis = root/'project-assets'/'visual-assets'/'index.json'
    if not vis.exists():return None
    try:
        d=json_read(vis)
        h=sha(content.strip()+'\n')
        for item in d.get('items',[]):
            if item.get('content_sha256')==h:
                return item.get('id')
    except (OSError,ValueError,TypeError):
        return None
    return None


def create_resource_file(root, row):
    catalog = root/'project-assets'/'resource-catalog'
    kind=row['kind']
    if kind not in ('mermaid','ascii-tree','markdown-table'):
        return
    if kind=='ascii-tree':
        from ascii_to_mermaid import build_mermaid
        try:
            code,evidence=build_mermaid(row['content'].splitlines(),row['source']['start_line'],row['category'])
            row['derivation_evidence']=evidence
            row['derived_mermaid_sha256']=sha(code)
        except (ValueError,IndexError) as e:
            row['render_status']='blocked-ambiguous-tree'
            row['render_error']=str(e)
            return
    elif kind=='mermaid':
        code=row['content']
    else:
        target = catalog/'tables'/f"{row['id']}.md"
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(row['content'],encoding='utf-8')
        row['source_asset']=target.relative_to(root).as_posix()
        row['a4_layout_status']='pending-official-template-and-Word-render'
        return
    target=catalog/'diagrams'/f"{row['id']}.mmd"
    if target.exists() and target.read_text('utf-8') != code:
        raise ValueError('目标图源存在同名不同内容：拒绝覆盖')
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(code,encoding='utf-8')
    row['source_asset']=target.relative_to(root).as_posix()
    row['legacy_vis_id']=find_legacy_vis(root,code)
    row['a4_layout_status']='pending-official-template-and-Word-render'
    # No shell, no npm, no browser installation. Safe fallback for simple DAG only.
    from svg_fallback import render
    svg=catalog/'diagrams'/f"{row['id']}.svg"
    if svg.exists():
        row['render_status']='rendered'
        row['preview_asset']=svg.relative_to(root).as_posix()
        return
    try:
        render(code,svg)
        row['render_status']='rendered'
        row['preview_asset']=svg.relative_to(root).as_posix()
    except (ValueError,RuntimeError) as e:
        if svg.exists():svg.unlink()
        row['render_status']='needs-mermaid-renderer'
        row['render_error']=str(e)


def merge_resources(root,pid,rows,hash_):
    from visual_assets import lock, audit
    base = root/'project-assets'
    with lock(base):
        cat=load_catalog(root,pid)
        byid={x['id']:x for x in cat['items']}
        seen=set()
        created=reused=0
        for row in rows:
            ident=row['id'];seen.add(ident)
            if ident in byid:
                old=byid[ident]
                if old.get('source',{}).get('technical_md_sha256')!=hash_:
                    old['review_status']='pending-review'
                    old['status']='source-revision-changed'
                old['source']=row['source']
                reused+=1
                continue
            create_resource_file(root,row)
            item={k:v for k,v in row.items() if k!='content'}
            cat['items'].append(item)
            byid[ident]=item
            created+=1
        for old in cat['items']:
            if old.get('kind')=='web-image-candidate':
                # History is preserved for audit but disabled from active delivery.
                old['status']='disabled-legacy-online-candidate'
                old['review_status']='rejected'
            elif (old.get('kind')!='user-upload-photo' and old['id'] not in seen
                    and old.get('source',{}).get('technical_md_sha256')!=hash_):
                old['status']='stale-source-changed'
                old['review_status']='pending-review'
        save_catalog(root,cat)
        audit(base,pid,'md-resource-catalog-synced',{'created':created,'reused':reused,
            'technical_md_sha256':hash_,'total':len(cat['items'])})
    return {'created':created,'reused':reused,'total':len(cat['items'])}


def requirements_path(root):
    return root/'project-assets'/'resource-catalog'/'module-requests.json'


def module_requirements(root,md,pid,body,hash_,save=False):
    from hardware_requests import identify_modules
    items=identify_modules(body,md.relative_to(root).as_posix(),hash_)
    cat=load_catalog(root,pid)
    uploaded={row.get('module_request_id') for row in cat['items']
              if row.get('kind')=='user-upload-photo'
              and row.get('source',{}).get('technical_md_sha256')==hash_}
    for item in items:
        if item['id'] in uploaded:item['user_upload_status']='uploaded-pending-review'
    summary={'schema_version':1,'project_id':pid,'technical_md_sha256':hash_,
            'source_of_truth':'technical-md-only','requirements':items,
            'total':len(items),'missing':sum(x['user_upload_status']=='missing' for x in items),
            'notice':'仅从MD提取明确出现的硬件名称；不视为采购或使用证明。用户自行上传完整模块实物图。'}
    if save:
        path=requirements_path(root)
        old=json_read(path) if path.exists() else None
        if not old or old.get('technical_md_sha256')!=hash_ or old.get('requirements')!=items:
            from visual_assets import lock,audit
            with lock(root/'project-assets'):
                atomic_write(path,json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
                header=['# 模块实物图上传清单','', '> 本清单仅根据正式技术 Markdown 提取。出现名称不代表已经实际采购/安装。','',
                        '| MD模块名称 | 原文行号 | 证据性质 | 上传状态 |','|---|---|---|---|']
                for x in items:
                    name=x['name_from_md'].replace('|','\\|')
                    header.append(f"| {name} | {','.join(map(str,x['evidence']['lines'][:5]))} | {x['claim_strength']} | {x['user_upload_status']} |")
                atomic_write(path.with_suffix('.md'),'\n'.join(header)+'\n')
                audit(root/'project-assets',pid,'module-upload-requirements-refreshed',{'total':len(items),'md_hash':hash_})
    return {'status':'UPLOAD_REQUIREMENTS','project_id':pid,**summary,
            'saved_to':requirements_path(root).relative_to(root).as_posix() if save else None}


def user_upload_photo(root,md,pid,body,hash_,args):
    from visual_assets import (lock,audit,load_manifest,write_manifest,
        safe_source_copy,assert_image_format,image_dimensions)
    req=module_requirements(root,md,pid,body,hash_,save=False)
    target=next((r for r in req['requirements'] if r['id']==args.module_id),None)
    if target is None:raise ValueError('未知模块请求ID，必须先依据 MD 生成上传清单')
    if not args.rights_declaration or len(args.rights_declaration.strip())<12:
        raise ValueError('必须记录用户提供图片的来源/权利声明（至少12字）')
    p=Path(args.file).expanduser().resolve(strict=True)
    upload_dir=root/'user-uploads'
    if upload_dir.is_symlink():
        raise ValueError('项目上传目录不能是符号链接')
    inpath=upload_dir.resolve()
    if not inpath.is_relative_to(root) or not p.is_relative_to(inpath) or not p.is_file() or p.is_symlink():
        raise ValueError('只允许读取本项目 user-uploads/ 下的实际用户上传文件')
    data=assert_image_format(p)
    dims=image_dimensions(p)
    if not dims or min(dims)<240 or max(dims)<400:
        raise ValueError('图片分辨率不足以核实完整设备主体')
    h=sha(data)
    vid='VIS-'+h[:12].upper()
    asset_id=rid('module-photo',args.module_id+'\n'+h)
    suffix=p.suffix.lower()
    vas=root/'project-assets'/'visual-assets'
    dst=vas/'images'/(vid+suffix)
    ev=target['evidence']
    with lock(root/'project-assets'):
        vis=load_manifest(vas,pid)
        existing=next((x for x in vis['items'] if x['id']==vid),None)
        if existing and existing.get('technical_module')!=target['name_from_md']:
            raise ValueError('该图片已绑定另一模块；请先人工核对，不静默跨模块复用')
        safe_source_copy(p,dst)
        if existing and existing['evidence_locations'][0].get('technical_md_sha256')!=hash_:
            existing.setdefault('previous_md_evidence',[]).extend(existing['evidence_locations'])
            existing['evidence_locations']=[{'technical_md':ev['technical_md'],
                  'technical_md_sha256':hash_,'module_line':ev['lines'][0]}]
            existing['review_status']='pending-visual-rights-and-fact-review'
            existing['fact_ids']=[]
            existing['fact_status']='unmapped'
        if not existing:
            record={'id':vid,'kind':'user-module-image','title':target['name_from_md']+' 用户实物图',
                'visual_category':None,'category_hint':'module-photo',
                'subject_scope':'unverified','technical_module':target['name_from_md'],
                'fact_ids':[],'fact_status':'unmapped','origin':'user-upload',
                'source_path':None,'image_path':dst.relative_to(root).as_posix(),
                'content_sha256':h,'copyright_holder':'user-to-confirm',
                'license':'unverified','rights_status':'user-declared-pending-review',
                'review_status':'pending-visual-rights-and-fact-review',
                'user_rights_declaration':args.rights_declaration.strip(),
                'evidence_locations':[{'technical_md':ev['technical_md'],
                   'technical_md_sha256':hash_,'module_line':ev['lines'][0]}],
                'created_at':now(),'updated_at':now()}
            vis['items'].append(record)
        write_manifest(vas,vis)
        cat=load_catalog(root,pid)
        old_catalog_item=next((x for x in cat['items'] if x['id']==asset_id),None)
        if old_catalog_item and old_catalog_item['source']['technical_md_sha256']!=hash_:
            old_catalog_item['source']['technical_md_sha256']=hash_
            old_catalog_item['review_status']='pending-review'
            old_catalog_item['status']='source-revision-needs-review'
        if not old_catalog_item:
            cat['items'].append({'id':asset_id,'kind':'user-upload-photo','category':'module-photo',
                'title':target['name_from_md'],'module_request_id':args.module_id,
                'source':{'technical_md':ev['technical_md'],'technical_md_sha256':hash_,
                          'start_line':ev['lines'][0],'end_line':ev['lines'][0]},
                'status':'user-upload-pending-review','review_status':'pending-review',
                'rights_status':'user-declared-pending-review',
                'image_asset':dst.relative_to(root).as_posix(),'legacy_vis_id':vid,
                'content_sha256':h,'created_at':now()})
        save_catalog(root,cat)
        audit(root/'project-assets',pid,'user-photo-candidate-uploaded',{'vis_id':vid,'resource_id':asset_id,
                         'module_id':args.module_id,'path':dst.relative_to(root).as_posix()})
    return {'status':'UPLOADED_PENDING_REVIEW','module':target['name_from_md'],'id':asset_id,
            'vis_id':vid,'image_path':dst.relative_to(root).as_posix(),
            'dimensions':dims,'next_step':'核对全貌、准确型号、用户拥有版权/授权、FACT 与 A4 插图尺寸'}


def attach_editable_diagram(root,md,pid,hash_,args):
    """Bind an actually rendered edit-friendly diagram to an existing MD-derived RES.

    Never claims document/Word visual acceptance; checks physical template width.
    """
    from visual_assets import lock,audit
    from a4_layout import inspect_template
    from xml.etree import ElementTree as ET
    catalog_dir=(root/'project-assets'/'resource-catalog'/'diagrams').resolve()
    svg=Path(args.svg).expanduser().resolve(strict=True)
    drawio=Path(args.drawio).expanduser().resolve(strict=True)
    if svg.suffix.lower()!='.svg' or drawio.suffix.lower()!='.drawio':
        raise ValueError('必须提供真实 .svg 和可编辑 .drawio 文件')
    for f in (svg,drawio):
        if not f.is_relative_to(catalog_dir) or f.is_symlink():
            raise ValueError('图稿必须保存于当前项目 resource-catalog/diagrams/ 内')
        if f.stat().st_size>5_000_000:raise ValueError('图源太大，不能安全入库')
    if not args.evidence or len(args.evidence.strip())<16:
        raise ValueError('必须提供至少16字的MD技术节点/连线核验说明')
    try:
        root_svg=ET.fromstring(svg.read_bytes());root_edit=ET.fromstring(drawio.read_bytes())
    except ET.ParseError as e:raise ValueError('SVG/drawio 并非有效XML') from e
    if not root_svg.tag.endswith('svg') or root_edit.tag!='mxfile':
        raise ValueError('文件内容并非可识别 SVG/drawio')
    vsdx=None
    vsdx_report=None
    if getattr(args,'vsdx',None):
        vsdx=Path(args.vsdx).expanduser().resolve(strict=True)
        if vsdx.suffix.lower()!='.vsdx':raise ValueError('--vsdx 必须是 .vsdx 文件')
        if not vsdx.is_relative_to(catalog_dir) or vsdx.is_symlink():
            raise ValueError('VSDX 必须保存于当前项目 resource-catalog/diagrams/ 内')
        if vsdx.stat().st_size>8_000_000:raise ValueError('VSDX 文件过大，不能安全入库')
        from vsdx_writer import validate_vsdx
        vsdx_report=validate_vsdx(vsdx)
        if vsdx_report.get('status')!='STRUCTURALLY_VALID_VSDX':
            raise ValueError('VSDX 结构校验失败：'+'；'.join(vsdx_report.get('issues', [])))
    def dimension_mm(key):
        value=root_svg.attrib.get(key,'')
        if not value.endswith('mm'):raise ValueError('SVG 必须显式指定毫米宽高')
        return float(value[:-2])
    w,h=dimension_mm('width'),dimension_mm('height')
    sections=inspect_template(args.template)['sections']
    section=sections[args.section-1]
    if not section['is_a4']:
        raise ValueError('目标模板当前节不是A4，不得假称完成A4插图适配')
    if w>section['figure_max_width_mm']+0.01 or h>section['figure_max_height_mm']+0.01:
        raise ValueError('图像宽高超出版心预算，须重新排布/拆图')
    template_digest=sha(Path(args.template).read_bytes())
    # v1.4.0: bilingual caption metadata is bound to the same RES record.  The
    # caption is never drawn into the image; it is data for the Word/HTML layer.
    meta=None
    meta_path=None
    if getattr(args,'figure_meta',None):
        meta_path=Path(args.figure_meta).expanduser().resolve(strict=True)
        if not meta_path.is_relative_to(catalog_dir) or meta_path.is_symlink():
            raise ValueError('figure-meta 必须位于当前项目 resource-catalog/diagrams/ 内')
        try:
            meta=json.loads(meta_path.read_text('utf-8'))
        except json.JSONDecodeError as e:
            raise ValueError('figure-meta 不是有效 JSON') from e
        if meta.get('schema')!='tva-figure-meta/1.0':
            raise ValueError('figure-meta schema 必须为 tva-figure-meta/1.0')
        if meta.get('geometry_mm') and [round(float(x),2) for x in meta['geometry_mm']]!=[round(w,2),round(h,2)]:
            raise ValueError('figure-meta 记录的尺寸与 SVG 不一致，禁止错配图题')
        if meta.get('svg') and Path(meta['svg']).name!=svg.name:
            raise ValueError('figure-meta 记录的 SVG 与当前 SVG 不一致')
        from visio_diagram import validate_caption
        validate_caption(meta,require=True)
    elif getattr(args,'require_caption',False):
        from visio_diagram import validate_caption
        candidate={'figure_number':getattr(args,'figure_number',None),
                   'caption_zh':getattr(args,'caption_zh',None),
                   'caption_en':getattr(args,'caption_en',None)}
        meta=validate_caption(candidate,require=True)
    with lock(root/'project-assets'):
        cat=load_catalog(root,pid)
        item=next((x for x in cat['items'] if x['id']==args.id),None)
        if not item or item.get('category') not in ('system-framework','functional-architecture','flowchart'):
            raise ValueError('只允许绑定已有、可验证的技术图类RES资源')
        if item['source']['technical_md_sha256']!=hash_:
            raise ValueError('源MD已变更，必须重新同步并校核技术图')
        item['editable_drawio']=drawio.relative_to(root).as_posix()
        item['print_svg']=svg.relative_to(root).as_posix()
        item['editable_drawio_sha256']=sha(drawio.read_bytes())
        item['print_svg_sha256']=sha(svg.read_bytes())
        if vsdx:
            item['print_vsdx']=vsdx.relative_to(root).as_posix()
            item['print_vsdx_sha256']=sha(vsdx.read_bytes())
            item['native_visio_vsdx']=True
            item['vsdx_verification']=vsdx_report.get('visio_open_verification','pending-visio-open')
        item['diagram_technical_review_evidence']=args.evidence.strip()
        item['template_sha256']=template_digest
        item['a4_section_index']=args.section
        item['a4_geometry_mm']=[w,h]
        item['a4_layout_status']='geometry-pass-pending-Word-page-review'
        if meta:
            item['figure_meta']=meta_path.relative_to(root).as_posix() if meta_path else None
            for key in ('figure_number','caption_zh','caption_en','caption_zh_full',
                        'caption_en_full','caption_position','semantic_check'):
                item['caption_'+key if key=='semantic_check' else key]=meta.get(key,'')
            item['caption_review_status']='pending-human-semantic-and-Word-page-review'
            item['routing_status']=meta.get('routing','unknown')
        save_catalog(root,cat)
        audit(root/'project-assets',pid,'a4-diagram-layout-attached',{'resource_id':args.id,'template_sha256':template_digest,
              'caption_figure_number':(meta or {}).get('figure_number')})
    result={'status':'A4_GEOMETRY_PASS_NEEDS_WORD_VISUAL_REVIEW','id':args.id,
            'editable_drawio':drawio.relative_to(root).as_posix(),'print_svg':svg.relative_to(root).as_posix(),
            'a4_width_mm':w,'a4_height_mm':h,'template_sha256':template_digest,
            'print_vsdx':vsdx.relative_to(root).as_posix() if vsdx else None,
            'vsdx_verification':(vsdx_report or {}).get('visio_open_verification')}
    if meta:
        result['caption']={k:meta.get(k) for k in ('figure_number','caption_zh','caption_en',
                            'caption_zh_full','caption_en_full','semantic_check')}
    return result


def execute(args):
    root,md,pid,body,hash_=validate_project(args.root,args.technical_md,args.project_id)
    if args.command=='scan':
        rows=extract_markdown(body,md.relative_to(root).as_posix(),hash_)
        summary={k:sum(r['category']==k for r in rows) for k in RESOURCE_TYPES}
        requirement=module_requirements(root,md,pid,body,hash_,False)
        return {'status':'SCANNED','source_of_truth':'technical-md-only',
                'technical_md':str(md),'technical_md_sha256':hash_,
                'module_photo_requirements':requirement['total'],
                'total':len(rows),'categories':summary,
                'resources':[{k:v for k,v in r.items() if k!='content'} for r in rows],
                'downloaded':0,'installed_packages':0}
    if args.command=='sync':
        rows=extract_markdown(body,md.relative_to(root).as_posix(),hash_)
        result=merge_resources(root,pid,rows,hash_)
        req=module_requirements(root,md,pid,body,hash_,True)
        return {'status':'SYNCED','source_of_truth':'technical-md-only',
                'technical_md_sha256':hash_,**result,'module_photo_requirements':req['total'],
                'downloaded':0,'installed_packages':0}
    if args.command=='attach-layout':
        return attach_editable_diagram(root,md,pid,hash_,args)
    if args.command=='module-list':
        return module_requirements(root,md,pid,body,hash_,args.save)
    if args.command=='upload-photo':
        return user_upload_photo(root,md,pid,body,hash_,args)
    if args.command=='report':
        cat=load_catalog(root,pid)
        bycat={k:{'total':0,'approved':0,'pending':0} for k in RESOURCE_TYPES}
        for item in cat['items']:
            c=item.get('category')
            if c in bycat:
                bycat[c]['total']+=1
                bycat[c]['approved' if item.get('review_status')=='approved' else 'pending']+=1
        req=module_requirements(root,md,pid,body,hash_,False)
        return {'status':'REPORT','source_of_truth':'technical-md-only',
                'technical_md_sha256':hash_,'module_photo_requirements':req['requirements'],
                'coverage':bycat,'items':cat['items']}
    if args.command=='review':
        if args.decision=='approved' and (not args.evidence or len(args.evidence.strip())<12):
            raise ValueError('批准前必须提供至少12字的人工实际核验说明')
        from visual_assets import lock,audit
        base=root/'project-assets'
        with lock(base):
            cat=load_catalog(root,pid)
            target=next((r for r in cat['items'] if r['id']==args.id),None)
            if target is None:raise ValueError('未知资源ID')
            if target['source'].get('technical_md_sha256')!=hash_:
                raise ValueError('MD源文件发生变化，必须先重新同步并审查')
            if args.decision=='approved':
                if target.get('category')=='unclassified':
                    raise ValueError('未明确分类不能批准')
                if target.get('kind') in ('web-image-candidate','user-upload-photo'):
                    raise ValueError('实物图必须在正式 VIS 审核中核对照片、型号、权利、FACT 与纸张适配')
                if target.get('kind') in ('mermaid','ascii-tree') and target.get('render_status')!='rendered':
                    raise ValueError('技术图未完成实际渲染，不能批准')
                if target.get('kind')=='local-image-reference':
                    raise ValueError('本地图像只登记了路径，尚未目检，不能作为正式素材批准')
            target['review_status']=args.decision
            target['review_evidence']=args.evidence or ''
            target['reviewed_by']=args.reviewer
            target['reviewed_at']=now()
            save_catalog(root,cat)
            audit(base,pid,'md-resource-reviewed',{'ids':[args.id],
                'decision':args.decision,'reviewer':args.reviewer})
        return {'status':args.decision,'id':args.id,'source_of_truth':'technical-md-only'}
    raise ValueError('未知命令')


def main(argv=None):
    ap=argparse.ArgumentParser(description='完全离线：技术MD图表/模块上传清单/用户照片归档')
    sub=ap.add_subparsers(dest='command',required=True)
    for name in ('scan','sync','module-list','upload-photo','attach-layout','report','review'):
        p=sub.add_parser(name)
        p.add_argument('--root',required=True)
        p.add_argument('--technical-md',required=True)
        p.add_argument('--project-id')
        if name=='module-list':p.add_argument('--save',action='store_true')
        if name=='attach-layout':
            p.add_argument('--id',required=True)
            p.add_argument('--svg',required=True)
            p.add_argument('--drawio',required=True)
            p.add_argument('--vsdx')
            p.add_argument('--template',required=True)
            p.add_argument('--section',type=int,default=1)
            p.add_argument('--evidence',required=True)
            p.add_argument('--figure-meta',dest='figure_meta')
            p.add_argument('--require-caption',dest='require_caption',action='store_true')
            p.add_argument('--figure-number',dest='figure_number')
            p.add_argument('--caption-zh',dest='caption_zh')
            p.add_argument('--caption-en',dest='caption_en')
        if name=='upload-photo':
            p.add_argument('--module-id',required=True)
            p.add_argument('--file',required=True)
            p.add_argument('--rights-declaration',required=True)
        if name=='review':
            p.add_argument('--id',required=True)
            p.add_argument('--decision',required=True,choices=('approved','rejected','pending-review'))
            p.add_argument('--evidence',default='')
            p.add_argument('--reviewer',required=True)
    args=ap.parse_args(argv)
    try:
        print(json.dumps(execute(args),ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError,UnicodeError,json.JSONDecodeError) as ex:
        print(json.dumps({'status':'BLOCK','reason':str(ex),'downloaded':0,
            'installed_packages':0},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
