#!/usr/bin/env python3
"""thesis-doc-suite visual asset registry (stdlib, project scoped).

Technical diagrams are imported ONLY from project-technical-doc's published Markdown.
External images require a separate, documented web investigation; this CLI does not
assert a source/licence was verified just because metadata was supplied.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
import shutil
import struct
import sys
import uuid

SCHEMA = 1
ALLOWED_FACT_STATES = {'implemented', 'declared', 'proposed'}
APPROVED_RIGHTS = {'owned', 'public-domain', 'cc-by', 'cc-by-sa', 'express-permission'}
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.svg'}
CATEGORIES = ('system-framework', 'functional-architecture', 'flowchart', 'module-photo')
FENCE_RE = re.compile(r'(?m)^```mermaid[^\S\r\n]*\r?\n(.*?)^```[^\S\r\n]*$', re.S | re.M | re.I)
IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def lf_bytes(text: str) -> bytes:
    """UTF-8 bytes with LF newlines: the single hash canonical form for text sources.

    Windows text I/O rewrites LF as CRLF; hashing raw bytes then diverges from the
    registered digest. Every Mermaid/text source hash MUST go through here.
    """
    return text.replace('\r\n', '\n').encode('utf-8')


def read_lf(path: Path) -> bytes:
    """File bytes with CRLF normalized to LF before hashing/compare (text sources only)."""
    return path.read_bytes().replace(b'\r\n', b'\n')


def jread(path: Path):
    return json.loads(path.read_text('utf-8'))


def atomic_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    try:
        with temp.open('w', encoding='utf-8', newline='\n') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def lock(base: Path):
    # Reuses canonical asset-management lock; do NOT introduce an incompatible lock.
    file = base / '.asset-write.lock'
    try:
        fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as e:
        raise ValueError('项目共享资产正在写入；禁止强制覆盖 .asset-write.lock') from e
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(utc())
        yield
    finally:
        file.unlink(missing_ok=True)


def context(root_str: str, requested_project_id: str | None = None):
    root = Path(root_str).expanduser().resolve(strict=True)
    base = root / 'project-assets'
    pfile = base / 'project.json'
    if not pfile.is_file():
        raise ValueError('项目尚未初始化：先使用 /thesis-doc-suite:init-project')
    project = jread(pfile)
    pid = project.get('project_id')
    if project.get('schema_version') != SCHEMA or not pid:
        raise ValueError('不支持的项目 schema 或缺少 project_id')
    if requested_project_id and requested_project_id != pid:
        raise ValueError('project_id 不匹配：拒绝串项目')
    facts_path = base / 'facts.json'
    facts = jread(facts_path) if facts_path.is_file() else {'items': []}
    if facts.get('project_id') != pid or facts.get('schema_version') != SCHEMA:
        raise ValueError('facts.json 的项目标识或版本不一致')
    fdict = {f['id']: f for f in facts.get('items', [])}
    vas = base / 'visual-assets'
    return root, base, vas, pid, fdict


def load_manifest(vas: Path, pid: str):
    path = vas / 'index.json'
    if not path.is_file():
        return {'schema_version': SCHEMA, 'project_id': pid, 'updated_at': utc(), 'items': []}
    data = jread(path)
    if data.get('schema_version') != SCHEMA or data.get('project_id') != pid:
        raise ValueError('视觉资产索引标识不匹配：拒绝混用')
    if not isinstance(data.get('items'), list):
        raise ValueError('视觉资产索引结构损坏')
    return data


def write_manifest(vas: Path, obj):
    obj['updated_at'] = utc()
    atomic_json(vas / 'index.json', obj)


def audit(base: Path, pid: str, action: str, obj: dict):
    event = {'at': utc(), 'action': action, 'actor': 'technical-visual-assets', 'project_id': pid, **obj}
    with (base / 'activity.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')


def rel(root: Path, file: Path) -> str:
    resolved = file.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('禁止登记项目根目录以外的目标文件')
    return resolved.relative_to(root).as_posix()


def safe_source_copy(source: Path, destination: Path):
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if digest(destination.read_bytes()) != digest(source.read_bytes()):
            raise ValueError('同名资产内容不同：禁止静默覆盖')
    else:
        # No overwrite, no modifying user source files.
        with destination.open('xb') as out, source.open('rb') as src:
            shutil.copyfileobj(src, out)


def previous_heading(text: str, pos: int):
    for line in reversed(text[:pos].splitlines()[-35:]):
        if re.match(r'^#{2,6}\s+', line):
            return re.sub(r'^#{2,6}\s+', '', line).strip()[:120]
    return '技术流程图'


def category_hint(label: str) -> str | None:
    """A suggestion only. Labels never constitute image-content verification."""
    h = label.casefold()
    if any(x in h for x in ('功能架构', '功能结构', '功能模块关系', '功能树', 'functional architecture')):
        return 'functional-architecture'
    if any(x in h for x in ('系统框架', '系统架构', '总体架构', '软硬件架构', 'system architecture', 'framework')):
        return 'system-framework'
    if any(x in h for x in ('流程图', '业务流程', '控制流程', '执行流程', '状态流程', 'flowchart', 'workflow')):
        return 'flowchart'
    return None


def assert_image_format(image: Path):
    if not image.is_file() or image.suffix.lower() not in IMAGE_EXTS:
        raise ValueError('仅支持 PNG/JPG/WEBP/SVG 的真实图像文件')
    if image.stat().st_size > 30 * 1024 * 1024:
        raise ValueError('单张图片超过 30MB')
    raw = image.read_bytes()
    ext = image.suffix.lower()
    if ext == '.png' and (not raw.startswith(b'\x89PNG\r\n\x1a\n') or raw[12:16] != b'IHDR'):
        raise ValueError('PNG 文件头无效')
    if ext in ('.jpg', '.jpeg') and not raw.startswith(b'\xff\xd8\xff'):
        raise ValueError('JPEG 文件头无效')
    if ext == '.webp' and (raw[:4] != b'RIFF' or raw[8:12] != b'WEBP'):
        raise ValueError('WEBP 文件头无效')
    if ext == '.svg':
        # SVG from untrusted internet is not a safe module photograph; reject rather than attempt to sanitize.
        raise ValueError('外部 SVG 不可作为模块实物图入库；请使用经过核实的 PNG/JPEG/WEBP')
    return raw


def image_dimensions(image: Path):
    """No Pillow dependency. A minimal metadata check, NOT semantic verification."""
    b=image.read_bytes()
    if image.suffix.lower()=='.png' and b.startswith(b'\x89PNG\r\n\x1a\n') and len(b)>=24:
        return struct.unpack('>II',b[16:24])
    if image.suffix.lower() in ('.jpg','.jpeg') and b.startswith(b'\xff\xd8'):
        pos=2
        while pos+4<len(b):
            if b[pos]!=0xFF:
                pos+=1; continue
            while pos<len(b) and b[pos]==0xFF:pos+=1
            if pos>=len(b):break
            marker=b[pos];pos+=1
            if marker in (0xD8,0xD9,0x01) or 0xD0<=marker<=0xD7:continue
            if pos+2>len(b):break
            length=int.from_bytes(b[pos:pos+2],'big')
            if length<2 or pos+length>len(b):break
            if marker in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                if length>=7:return (int.from_bytes(b[pos+5:pos+7],'big'),int.from_bytes(b[pos+3:pos+5],'big'))
            pos+=length
    if image.suffix.lower()=='.webp' and b[:4]==b'RIFF' and b[8:12]==b'WEBP':
        if b[12:16]==b'VP8X' and len(b)>=30:
            return (1+int.from_bytes(b[24:27],'little'),1+int.from_bytes(b[27:30],'little'))
        if b[12:16]==b'VP8 ' and len(b)>=30 and b[23:26]==b'\x9d\x01\x2a':
            return (int.from_bytes(b[26:28],'little')&0x3FFF,int.from_bytes(b[28:30],'little')&0x3FFF)
    return None


def is_valid_https(url):
    try:
        u = urlsplit(url)
        return u.scheme == 'https' and bool(u.hostname) and not u.username and not u.password
    except ValueError:
        return False


def technical_md(root: Path, md_arg: str):
    md = Path(md_arg).expanduser().resolve(strict=True)
    parent = (root / 'deliverables' / 'technical-document').resolve()
    if not md.is_relative_to(parent) or not md.is_file() or md.suffix.lower() != '.md':
        raise ValueError('仅接受 <PROJECT_ROOT>/deliverables/technical-document/ 中 project-technical-doc 的正式 Markdown')
    return md


def browser_candidates():
    """Installed Chrome executables that headless rendering can drive.

    Edge is deliberately excluded: its single-instance forwarding makes
    `--headless` exits return code 0 with empty output on this platform.
    """
    out = [Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
           Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe')]
    local = os.environ.get('LOCALAPPDATA')
    if local:
        out.append(Path(local) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe')
    return out


def resolve_renderer(plugin_root: Path) -> Path:
    """Locate diagram_svg.py without installing anything.

    Packaged sibling (INTEGRATION.md layout) first, then TVA_DIAGRAM_SVG override
    and known pre-existing trees, so a missing copy fails loudly but recoverably.
    """
    candidates = [plugin_root / 'skills' / 'project-technical-doc' / 'scripts' / 'diagram_svg.py']
    env = os.environ.get('TVA_DIAGRAM_SVG')
    if env:
        candidates.append(Path(env))
    candidates += [plugin_root.parent / 'project-technical-doc' / 'scripts' / 'diagram_svg.py',
                   plugin_root.parent.parent / 'project-technical-doc-skill-v4' /
                   'project-technical-doc' / 'scripts' / 'diagram_svg.py']
    return next((c for c in candidates if c.is_file()), candidates[0])


def scan(args):
    root, base, vas, pid, facts = context(args.root, args.project_id)
    md = technical_md(root, args.technical_md)
    body = md.read_text('utf-8-sig')
    md_hash = digest(md.read_bytes())
    sources = list(FENCE_RE.finditer(body))
    inline_images = list(IMAGE_RE.finditer(body))
    if not sources and not inline_images:
        print(json.dumps({'status': 'WARN', 'created': 0, 'found': 0, 'message': '未发现 Mermaid 流程图；不凭空生成'}, ensure_ascii=False)); return
    items_new = []
    with lock(base):
        data = load_manifest(vas, pid)
        byid = {r['id']: r for r in data['items']}
        for m in sources:
            code = m.group(1).strip() + '\n'
            hash_code = digest(code.encode('utf-8'))
            id_ = 'VIS-' + hash_code[:12].upper()
            line = body.count('\n', 0, m.start()) + 1
            evidence = {'technical_md': rel(root, md), 'technical_md_sha256': md_hash,
                        'mermaid_line': line, 'technical_section': previous_heading(body, m.start())}
            if id_ in byid:
                existing = byid[id_]
                if evidence not in existing.setdefault('evidence_locations', []):
                    existing['evidence_locations'].append(evidence)
                    items_new.append({'id': id_, 'mode': 'reused'})
                continue
            target = vas / 'diagrams' / f'{id_}.mmd'
            target.parent.mkdir(parents=True, exist_ok=True)
            # LF bytes on disk == registered content_sha256, even on Windows.
            target.write_bytes(lf_bytes(code)) if not target.exists() else None
            item = {
                'id': id_, 'kind': 'technical-diagram', 'title': previous_heading(body, m.start()),
                'visual_category': None, 'category_hint': category_hint(previous_heading(body, m.start())),
                'subject_scope': 'full-diagram',
                'technical_module': None, 'fact_ids': [], 'fact_status': 'unmapped',
                'origin': 'project-technical-doc', 'source_path': rel(root, target),
                'image_path': None, 'content_sha256': hash_code,
                'source_page_url': None, 'original_image_url': None,
                'copyright_holder': 'project-author-to-confirm', 'license': 'unknown',
                'rights_status': 'unverified', 'web_verified_at': None,
                'review_status': 'needs-fact-mapping', 'evidence_locations': [evidence],
                'created_at': utc(), 'updated_at': utc(), 'notes': '仅来自已发表技术 MD；图中技术事实须逐项绑定 FACT ID 后可批准'
            }
            data['items'].append(item); byid[id_] = item
            items_new.append({'id': id_, 'mode': 'created'})
        # Additional MD-native figures (e.g. ![系统框架](figures/framework.png)).
        # No HTTP/image downloads; only files explicitly referenced by final MD.
        for m in inline_images:
            label, ref = m.group(1).strip(), m.group(2).strip().split(' ', 1)[0]
            if urlsplit(ref).scheme or ref.startswith('//'):
                continue
            try:
                local = (md.parent / unquote(ref)).resolve(strict=True)
                if not local.is_relative_to(root) or not local.is_file() or local.suffix.lower() not in IMAGE_EXTS:
                    continue
                blob=local.read_bytes()
                ext=local.suffix.lower()
                if ext=='.svg':
                    raw=blob.decode('utf-8','replace').lower()
                    if '<svg' not in raw or any(x in raw for x in ('<script','javascript:','<foreignobject','<iframe','onload=', 'onerror=')):
                        continue
                else:
                    assert_image_format(local)
                h=digest(blob)
                vid='VIS-'+h[:12].upper()
                line=body.count('\n',0,m.start())+1
                ev={'technical_md':rel(root,md),'technical_md_sha256':md_hash,
                    'image_line':line,'technical_section':previous_heading(body,m.start()),
                    'original_image_reference':rel(root,local)}
                if vid in byid:
                    old=byid[vid]
                    if ev not in old.setdefault('evidence_locations',[]):
                        old['evidence_locations'].append(ev)
                        items_new.append({'id':vid,'mode':'reused-local-figure'})
                    continue
                dest=vas/'diagrams'/(vid+ext)
                safe_source_copy(local,dest)
                item={'id':vid,'kind':'technical-figure','origin':'project-technical-doc',
                    'title':label or previous_heading(body,m.start()),
                    'visual_category':None,'category_hint':category_hint(label or previous_heading(body,m.start())),
                    'technical_module':None,'subject_scope':'needs-visual-review',
                    'fact_ids':[],'fact_status':'unmapped','source_path':rel(root,dest),
                    'image_path':rel(root,dest),'content_sha256':h,'render_sha256':None,
                    'source_page_url':None,'original_image_url':None,
                    'copyright_holder':'project-author-to-confirm','license':'unknown',
                    'rights_status':'unverified','web_verified_at':None,
                    'review_status':'needs-fact-mapping','evidence_locations':[ev],
                    'created_at':utc(),'updated_at':utc(),
                    'notes':'技术 Markdown 内引用的本地图像，仅候选，须逐图审查内容与权利。'}
                data['items'].append(item); byid[vid]=item
                items_new.append({'id':vid,'mode':'created-local-figure'})
            except (OSError,ValueError):
                continue
        if items_new:
            write_manifest(vas, data)
            audit(base, pid, 'visual-assets-scanned', {'ids': [i['id'] for i in items_new], 'technical_md': rel(root, md)})
    print(json.dumps({'status': 'PASS', 'found': len(sources)+len(inline_images), 'changed': items_new, 'index': str(vas/'index.json')}, ensure_ascii=False, indent=2))


def external(args):
    root, base, vas, pid, facts = context(args.root, args.project_id)
    md = technical_md(root, args.technical_md)
    md_text = md.read_text('utf-8-sig')
    module_pos = md_text.casefold().find(args.module.casefold())
    if module_pos < 0 or not args.module.strip():
        raise ValueError('模块名称未在 project-technical-doc 的最终技术 MD 中找到，不能凭外部图片自行新增模块')
    md_evidence = {'technical_md': rel(root, md), 'technical_md_sha256': digest(md.read_bytes()),
                   'module_line': md_text.count('\n', 0, module_pos) + 1}
    image = Path(args.file).expanduser().resolve(strict=True)
    assert_image_format(image)
    if not (is_valid_https(args.source_page) and is_valid_https(args.image_url)):
        raise ValueError('外部图片必须提供有效 HTTPS 来源页面和原图 URL')
    bodyhash = digest(image.read_bytes())
    id_ = 'VIS-' + bodyhash[:12].upper()
    copy_to = vas / 'images' / (id_ + image.suffix.lower())
    with lock(base):
        data = load_manifest(vas, pid)
        if any(r['id'] == id_ or (r.get('content_sha256') == bodyhash) for r in data['items']):
            print(json.dumps({'status': 'EXISTS', 'id': id_}, ensure_ascii=False)); return
        safe_source_copy(image, copy_to)
        item = {
            'id': id_, 'kind': 'external-module-image', 'title': args.title,
            'visual_category': None, 'category_hint': 'module-photo',
            'subject_scope': 'unverified',
            'technical_module': args.module, 'fact_ids': [], 'fact_status': 'unmapped',
            'origin': 'external-web', 'source_path': None, 'image_path': rel(root, copy_to),
            'content_sha256': bodyhash,
            'source_page_url': args.source_page, 'original_image_url': args.image_url,
            'copyright_holder': args.author or 'unknown', 'license': args.license or 'unknown',
            'rights_status': 'unverified', 'web_verified_at': None,
            'review_status': 'needs-fact-mapping-and-rights-review',
            'evidence_locations': [md_evidence], 'created_at': utc(), 'updated_at': utc(),
            'notes': '网络候选图；URL/授权/型号必须人工或工具实际核实；此命令并未联网核验'
        }
        data['items'].append(item)
        write_manifest(vas, data)
        audit(base, pid, 'visual-asset-external-candidate', {'ids': [id_], 'source_page_url': args.source_page})
    print(json.dumps({'status': 'CANDIDATE', 'id': id_, 'image_path': rel(root, copy_to), 'review_status': item['review_status']}, ensure_ascii=False, indent=2))


def render(args):
    """Render with the existing project-technical-doc engine, or strict stdlib SVG.

    Only a source-preserving render. Neither path confirms the technical meaning.
    No package is installed or fetched.
    """
    import importlib.util
    from svg_fallback import render as fallback_render
    root, base, vas, pid, facts = context(args.root, args.project_id)
    plugin_root = Path(__file__).resolve().parents[3]
    renderer = resolve_renderer(plugin_root)
    if not os.environ.get('PUPPETEER_EXECUTABLE_PATH'):
        found = next((str(c) for c in browser_candidates() if c.is_file()), None)
        if found:
            # mermaid-cli's puppeteer cache is often empty on this platform; point
            # it at the already-installed system Chrome (Edge silently exits).
            os.environ['PUPPETEER_EXECUTABLE_PATH'] = found
    with lock(base):
        data = load_manifest(vas, pid)
        target = next((x for x in data['items'] if x['id'] == args.id), None)
        if target is None or target.get('kind') != 'technical-diagram':
            raise ValueError('未找到技术图示资产 ID')
        src = (root / target['source_path']).resolve()
        # LF口径哈希：Windows 下文本工具写回 CRLF 不算「已经修改」。
        if not src.is_relative_to(vas.resolve()) or not src.is_file() or digest(read_lf(src)) != target['content_sha256']:
            raise ValueError('Mermaid 源码丢失、路径不安全或已经修改')
        out = vas / 'diagrams' / f"{target['id']}.svg"
        if out.exists() and not target.get('render_sha256'):
            raise ValueError('发现未登记的同名 SVG，禁止无记录覆盖')
        if out.exists() and digest(out.read_bytes()) != target.get('render_sha256'):
            raise ValueError('已有 SVG 与登记的哈希不同，禁止覆盖')
        if out.exists():
            engine = 'reuse-existing-render'
        else:
            engine, reason = None, None
            if renderer.is_file():
                try:
                    spec = importlib.util.spec_from_file_location('project_technical_diagram_svg', renderer)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    engine, reason = mod.render_one(src.read_text('utf-8'), out)
                    raw = src.read_bytes()
                    if b'\r\n' in raw:
                        # render_one 写回 .mmd 会引入 CRLF；登记哈希按 LF 口径，立即归一。
                        src.write_bytes(raw.replace(b'\r\n', b'\n'))
                except Exception as exc:
                    reason = str(exc)[:400]
            if not engine:
                # Prior render may leave an invalid intermediate. It has not been
                # approved or registered and is safe to remove from THIS asset path.
                if out.exists() and not target.get('render_sha256'):
                    out.unlink()
                try:
                    info = fallback_render(src.read_text('utf-8'), out)
                    engine = info['engine']
                except ValueError as exc:
                    print(json.dumps({'status':'WARN','id':args.id,
                        'reason':str(exc),'previous_engine_reason':reason,
                        'message':'复杂图无法由现有引擎或零依赖回退渲染；保留可编辑源文件'},
                        ensure_ascii=False))
                    return
        if not out.exists() or '<svg' not in out.read_text('utf-8', errors='replace'):
            raise ValueError('生成结果缺少 SVG 根元素')
        target['image_path'] = rel(root, out)
        target['render_engine'] = engine
        target['render_sha256'] = digest(out.read_bytes())
        target['updated_at'] = utc()
        write_manifest(vas, data)
        audit(base, pid, 'visual-asset-rendered', {'ids':[args.id], 'engine':engine})
    print(json.dumps({'status':'PASS','id':args.id,'svg':rel(root,out),
        'engine':engine,'installed_packages':0},ensure_ascii=False))


def set_review(args):
    root, base, vas, pid, facts = context(args.root, args.project_id)
    requested = [s.strip() for s in args.fact_ids.split(',') if s.strip()]
    if not requested:
        raise ValueError('必须提供来自 project-technical-doc 的 FACT-xxx 关联，不能仅凭网络图片推断事实')
    missing = [i for i in requested if i not in facts]
    if missing:
        raise ValueError('FACT ID 不存在：' + ', '.join(missing))
    if any(facts[x].get('status') not in ALLOWED_FACT_STATES for x in requested):
        raise ValueError('存在 unverified 技术事实，不得批准用于正式文书')
    if args.rights not in APPROVED_RIGHTS and args.rights not in ('unverified','internal-only'):
        raise ValueError('不支持的授权状态')
    if args.approve and args.rights not in APPROVED_RIGHTS:
        raise ValueError('无法确认复用权限时只能保留候选')
    if args.category and args.category not in CATEGORIES:
        raise ValueError('未知图片类别')
    if args.approve and not args.category:
        raise ValueError('批准图片前必须确认系统框架/功能架构/流程图/模块实物图类别')
    if args.approve and (not args.visual_evidence or len(args.visual_evidence.strip()) < 16):
        raise ValueError('需实际观察图片并记录至少16字的内容核对证据 --visual-evidence')
    with lock(base):
        data = load_manifest(vas, pid)
        target = next((x for x in data['items'] if x['id'] == args.id), None)
        if target is None: raise ValueError('未知的视觉资产 ID')
        if not target.get('evidence_locations'):
            raise ValueError('缺少上游技术 Markdown 证据定位，禁止批准')
        if (args.approve and target.get('category_hint') and args.category != target.get('category_hint')
                and not args.category_override_reason):
            raise ValueError('审批类别与图原始候选类型冲突；必须提供 --category-override-reason 并核对技术含义')
        if target['origin'] == 'external-web':
            if args.category and args.category != 'module-photo':
                raise ValueError('外部网络模块实物图只允许按 module-photo 分类；其他技术图必须从事实绘制')
            if args.approve and not args.full_module_confirmed:
                raise ValueError('尚未确认图像完整展示模块主体；局部电阻、裸芯片、单独配件或芯片内部框图不能代替模块实物图')
            if args.approve and args.subject_level not in ('complete-device', 'complete-module', 'complete-board'):
                raise ValueError('审批外部实物图必须使用 --subject-level 声明完整设备/模组/整板主体；不能将裸芯片或零件局部图充当模块照')
            if args.approve and (not args.model_evidence or len(args.model_evidence.strip()) < 12):
                raise ValueError('缺少实际核对厂家、完整模块型号和版本的 --model-evidence')
            if args.approve:
                fstatements=[facts[x].get('statement','').casefold() for x in requested]
                if target.get('technical_module','').casefold() not in '\n'.join(fstatements):
                    raise ValueError('关联 FACT 未直接提及该模块名称：不得把其他 FACT 冒充为模块型号证据')
                image_file=(root/target['image_path']).resolve()
                size=image_dimensions(image_file)
                if not size or min(size)<240 or max(size)<400:
                    raise ValueError('外部实物图分辨率过低或尺寸不可核验，不足以清晰展示完整模块')
            if not args.source_checked_at or not args.checked_by:
                raise ValueError('网络图片需填写实际来源核验时间及核验人/工具')
            if args.approve and not args.permission_evidence:
                raise ValueError('外部图片批准前必须提供实际授权依据：--permission-evidence')
            if not target.get('source_page_url') or not target.get('original_image_url'):
                raise ValueError('外部图片缺少来源页面和原图 URL')
            target['web_verified_at'] = args.source_checked_at
            target['checked_by'] = args.checked_by
            target['permission_evidence'] = args.permission_evidence
        if target['origin'] != 'external-web' and args.category == 'module-photo':
            raise ValueError('技术流程图不能冒充模块实物照片')
        if args.approve and target['kind'] == 'technical-diagram' and not target.get('image_path'):
            raise ValueError('技术流程图须先执行 render，生成可见 SVG 后才能批准配图复用')
        if args.category:
            target['visual_category'] = args.category
        if args.visual_evidence:
            target['visual_evidence'] = args.visual_evidence
        if args.category_override_reason:
            target['category_override_reason'] = args.category_override_reason
        if target['origin']=='external-web' and args.model_evidence:
            target['model_evidence'] = args.model_evidence
        if target['origin'] == 'external-web' and args.full_module_confirmed:
            target['subject_scope'] = 'whole-module-reviewed'
        if target['origin'] == 'external-web' and args.subject_level:
            target['subject_level'] = args.subject_level
        target['fact_ids'] = requested
        target['fact_status'] = 'linked'
        target['rights_status'] = args.rights
        target['review_status'] = 'approved' if args.approve else 'pending-review'
        target['updated_at'] = utc()
        target['review_reason'] = args.reason
        write_manifest(vas, data)
        audit(base, pid, 'visual-asset-reviewed', {'ids': [args.id], 'fact_ids': requested,
                    'approved': args.approve, 'reason': args.reason})
    print(json.dumps({'status': target['review_status'], 'id': args.id, 'fact_ids': requested}, ensure_ascii=False))


def report(args):
    root, base, vas, pid, facts = context(args.root, args.project_id)
    data = load_manifest(vas, pid)
    rows = data['items']
    if args.approved_only: rows = [r for r in rows if r.get('review_status') == 'approved']
    print(json.dumps({'project_id': pid, 'total': len(rows), 'assets': rows}, ensure_ascii=False, indent=2))


def verify(args):
    root, base, vas, pid, facts = context(args.root, args.project_id)
    data = load_manifest(vas, pid)
    failures, warnings = [], []
    for rec in data['items']:
        p = rec.get('source_path') if rec['kind'] in ('technical-diagram','technical-figure') else rec.get('image_path')
        if not p: failures.append(f"{rec['id']}: 缺少本地源文件"); continue
        local = (root / p).resolve()
        if not local.is_relative_to(root) or not local.is_file():
            failures.append(f"{rec['id']}: 资源文件丢失或路径越界"); continue
        if digest(local.read_bytes()) != rec.get('content_sha256') and rec['kind'] == 'external-module-image':
            failures.append(f"{rec['id']}: 图片内容哈希已变化")
        # .mmd 文本源用 LF 口径哈希；technical-figure 是真实图像文件，保持原始字节哈希。
        if rec['kind'] == 'technical-diagram' and digest(read_lf(local)) != rec.get('content_sha256'):
            failures.append(f"{rec['id']}: Mermaid 源码哈希变化")
        if rec['kind'] == 'technical-figure' and digest(local.read_bytes()) != rec.get('content_sha256'):
            failures.append(f"{rec['id']}: 图像内容哈希已变化")
        if rec.get('image_path') and rec.get('render_sha256'):
            rend = (root / rec['image_path']).resolve()
            if not rend.is_relative_to(root) or not rend.is_file() or digest(rend.read_bytes()) != rec['render_sha256']:
                failures.append(f"{rec['id']}: 渲染图像丢失或与哈希不一致")
        if rec.get('review_status') == 'approved':
            for fid in rec.get('fact_ids', []):
                if fid not in facts or facts[fid].get('status') not in ALLOWED_FACT_STATES:
                    failures.append(f"{rec['id']}: 引用 FACT 已删除或改为 unverified")
            if rec.get('origin') == 'external-web' and not rec.get('web_verified_at'):
                failures.append(f"{rec['id']}: 外部来源无核验记录")
            if rec.get('rights_status') not in APPROVED_RIGHTS:
                failures.append(f"{rec['id']}: 授权不满足")
            if rec.get('visual_category') not in CATEGORIES or len(rec.get('visual_evidence','').strip()) < 16:
                failures.append(f"{rec['id']}: 缺少已核验的图像类型或内容说明")
            if rec.get('origin') == 'external-web' and (rec.get('visual_category') != 'module-photo' or rec.get('subject_scope') != 'whole-module-reviewed' or rec.get('subject_level') not in ('complete-device','complete-module','complete-board') or not rec.get('model_evidence')):
                failures.append(f"{rec['id']}: 外部图尚未确认完整模块主体")
        else:
            warnings.append(f"{rec['id']}: 尚未批准使用")
        for ev in rec.get('evidence_locations', []):
            md = root / ev.get('technical_md', '')
            if not md.is_file() or digest(md.read_bytes()) != ev.get('technical_md_sha256'):
                warnings.append(f"{rec['id']}: 上游技术 MD 已变化或不可读，建议复核")
    result = {'status': 'FAIL' if failures else ('WARN' if warnings else 'PASS'),
              'project_id': pid, 'checked': len(data['items']), 'errors': failures, 'warnings': warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures: raise ValueError('资产校验失败')


def workdir(args):
    root, base, vas, pid, facts = context(args.root, args.project_id)
    run_id = args.run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:7]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', run_id) or run_id in ('.', '..'):
        raise ValueError('非法 run-id')
    parent = root / '.skill-tmp' / 'technical-visual-assets'
    if parent.is_symlink(): raise ValueError('运行区为符号链接，拒绝创建')
    parent.mkdir(parents=True, exist_ok=True)
    out = parent / run_id
    if out.exists() or out.is_symlink(): raise ValueError('运行目录已存在；不能覆盖')
    out.mkdir()
    (out / '.owned-by-technical-visual-assets').write_text(pid, 'utf-8')
    print(json.dumps({'status':'PASS','run_id':run_id,'path':str(out)},ensure_ascii=False))


def cleanup(args):
    root, base, vas, pid, facts = context(args.root, args.project_id)
    rid = args.run_id
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',rid) or rid in ('.','..'):
        raise ValueError('非法 run-id')
    parent = root / '.skill-tmp' / 'technical-visual-assets'
    path = parent / rid
    marker = path / '.owned-by-technical-visual-assets'
    if parent.is_symlink() or path.is_symlink() or not path.is_dir() or not marker.is_file():
        raise ValueError('运行目录不存在、是符号链接或缺少所有权标记')
    if marker.read_text('utf-8') != pid:
        raise ValueError('运行目录所有权/项目不匹配')
    for part in path.rglob('*'):
        if part.is_symlink(): raise ValueError('发现符号链接，拒绝清理')
    if path.resolve().parent != parent.resolve() or not path.resolve().is_relative_to(root):
        raise ValueError('路径越界')
    shutil.rmtree(path)
    print(json.dumps({'status':'PASS','removed_run_id':rid},ensure_ascii=False))


def add_diagram(args):
    """Add a NEW editable diagram grounded in the final MD and existing FACTs.

    A CLI cannot prove a drawn node/arrow is correct. New diagram is strictly
    a candidate requiring visual + source review before approval.
    """
    root, base, vas, pid, facts = context(args.root, args.project_id)
    md = technical_md(root, args.technical_md)
    if args.category not in ('system-framework','functional-architecture','flowchart'):
        raise ValueError('新绘制技术图必须属于框架/功能架构/流程三类，不能伪造实物照片')
    ids = [x.strip() for x in args.fact_ids.split(',') if x.strip()]
    if not ids or any(fid not in facts or facts[fid].get('status') not in ALLOWED_FACT_STATES for fid in ids):
        raise ValueError('新增技术图必须关联存在的且非 unverified 的 FACT-xxx')
    src = Path(args.file).expanduser().resolve(strict=True)
    if src.suffix.lower() != '.mmd' or not src.is_file() or src.stat().st_size > 150_000:
        raise ValueError('只接收小于150KB的 .mmd 可编辑 Mermaid 源文件')
    code = src.read_text('utf-8-sig').strip() + '\n'
    if not re.match(r'^\s*(flowchart|graph|sequenceDiagram|stateDiagram|classDiagram)\b',code,re.I):
        raise ValueError('不是可识别的 Mermaid 技术图源；请检查真实节点和关系')
    h=digest(code.encode('utf-8')); vid='VIS-'+h[:12].upper()
    target=vas/'diagrams'/(vid+'.mmd')
    with lock(base):
        data=load_manifest(vas,pid)
        if any(item['id']==vid for item in data['items']):
            print(json.dumps({'status':'EXISTS','id':vid},ensure_ascii=False)); return
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=code.encode('utf-8'):
            raise ValueError('目标同名图内容冲突')
        if not target.exists():
            with target.open('xb') as f:f.write(code.encode('utf-8'))
        item={'id':vid,'kind':'technical-diagram','origin':'derived-from-technical-doc',
              'title':args.title,'visual_category':None,'category_hint':args.category,
              'subject_scope':'full-diagram','technical_module':None,'fact_ids':ids,
              'fact_status':'linked','source_path':rel(root,target),'image_path':None,
              'content_sha256':h,'source_page_url':None,'original_image_url':None,
              'copyright_holder':'project-author-to-confirm','license':'unknown',
              'rights_status':'unverified','web_verified_at':None,
              'review_status':'pending-review', 'evidence_locations':[{'technical_md':rel(root,md),
                     'technical_md_sha256':digest(md.read_bytes()),'source_note':args.reason,
                     'source_line_range':getattr(args,'source_line_range',None),
                     'strict_conversion_provenance':getattr(args,'strict_conversion_provenance',None)}],
              'created_at':utc(),'updated_at':utc(),
              'notes':'基于用户最终技术MD/FACT新绘制的技术图候选。仍需审查每个节点和连接，并渲染。'}
        data['items'].append(item)
        write_manifest(vas,data)
        audit(base,pid,'visual-diagram-drafted',{'ids':[vid],'fact_ids':ids,'category_hint':args.category})
    print(json.dumps({'status':'CANDIDATE','id':vid,'source_path':rel(root,target)},ensure_ascii=False))



def draft_from_ascii(args):
    """Draft a candidate diagram from *explicit* relations in exact MD source lines.

    No relation is added without a source line. The actual graph needs review
    and subsequent render; it never becomes approved automatically.
    """
    import tempfile
    import io
    from contextlib import redirect_stdout
    from ascii_to_mermaid import build_mermaid
    root, base, vas, pid, facts = context(args.root, args.project_id)
    md = technical_md(root, args.technical_md)
    lines = md.read_text('utf-8-sig').splitlines()
    if args.start_line < 1 or args.end_line < args.start_line or args.end_line > len(lines):
        raise ValueError('指定的技术 MD 行号无效')
    if args.end_line - args.start_line + 1 > 55:
        raise ValueError('单次最多处理55行，请缩小选区')
    ids = [x.strip() for x in args.fact_ids.split(',') if x.strip()]
    if not ids or any(x not in facts or facts[x].get('status') not in ALLOWED_FACT_STATES for x in ids):
        raise ValueError('必须绑定已存在且非 unverified 的 FACT')
    code, provenance = build_mermaid(lines[args.start_line-1:args.end_line], args.start_line, args.category)
    if not args.reason.strip():
        raise ValueError('必须说明所选原文和 FACT 与此图的关联')
    with tempfile.TemporaryDirectory(prefix='visual-draft-') as tmp:
        candidate = Path(tmp)/'source.mmd'
        candidate.write_text(code, 'utf-8')
        # Reuse the same candidate and audit path; never directly write to MD.
        import argparse as ap
        new_args=ap.Namespace(root=args.root, project_id=args.project_id, technical_md=args.technical_md,
            file=str(candidate), title=args.title, category=args.category, fact_ids=args.fact_ids,
            reason=args.reason, source_line_range=[args.start_line,args.end_line],
            strict_conversion_provenance=provenance)
        output = io.StringIO()
        with redirect_stdout(output):
            add_diagram(new_args)
        added = json.loads(output.getvalue())
    print(json.dumps({'status':'DRAFT_ONLY','id':added.get('id'),
        'source_path':added.get('source_path'),
        'source_lines':[args.start_line,args.end_line],
        'method':provenance['method'], 'nodes':len(provenance['nodes']),
        'edges':len(provenance['edges']), 'must_review_before_approval':True,
        'message':'已提交候选；请核对原文、FACT、图义及渲染效果。'},ensure_ascii=False))


def scope_module(args):
    """Register a whole, project-evidenced core hardware module as a photo target.

    Doesn't infer BOM entries or download anything. Agent selects only meaningful
    functional modules; 0201 passives / connectors / cropped chip parts are excluded.
    """
    root, base, vas, pid, facts = context(args.root, args.project_id)
    md = technical_md(root, args.technical_md)
    md_text = md.read_text('utf-8-sig')
    name = args.module.strip()
    # ≥2 字符：像 D1 这样的真实位号/型号必须可登记；仍然禁止单字符占位。
    if len(name) < 2 or name.casefold() not in md_text.casefold():
        raise ValueError('核心模块名称必须在正式技术 Markdown 中明确出现')
    ids = [x.strip() for x in args.fact_ids.split(',') if x.strip()]
    if not ids or any(fid not in facts or facts[fid].get('status') not in ALLOWED_FACT_STATES for fid in ids):
        raise ValueError('核心模块必须关联存在且非 unverified 的 FACT-xxx')
    if not any(name.casefold() in facts[fid].get('statement','').casefold() for fid in ids):
        raise ValueError('关联 FACT 必须明确提及当前核心模块名称，不得错配技术事实')
    with lock(base):
        path = vas / 'requirements.json'
        data = jread(path) if path.is_file() else {'schema_version': 1, 'project_id': pid, 'core_modules': []}
        if data.get('schema_version') != 1 or data.get('project_id') != pid:
            raise ValueError('视觉范围文件的项目标识不匹配')
        for existing in data['core_modules']:
            if existing['name'].casefold() == name.casefold():
                if existing['fact_ids'] != ids:
                    raise ValueError('核心模块已登记但事实 ID 不同；拒绝自动覆盖，需人工复核')
                print(json.dumps({'status':'EXISTS','module':name},ensure_ascii=False)); return
        data['core_modules'].append({'name':name,'fact_ids':ids,
            'technical_md':rel(root,md),'technical_md_sha256':digest(md.read_bytes()),
            'reason':args.reason, 'created_at':utc()})
        atomic_json(path, data)
        audit(base,pid,'visual-scope-module',{'module':name,'fact_ids':ids})
    print(json.dumps({'status':'PASS','module':name,'fact_ids':ids},ensure_ascii=False))


def coverage(args):
    """Four required figure groups. Photo coverage is per registered core module."""
    root, base, vas, pid, facts = context(args.root, args.project_id)
    idx = load_manifest(vas,pid)
    rows = idx['items']
    categories = {}
    for cat in CATEGORIES:
        approved = [x for x in rows if x.get('visual_category') == cat and x.get('review_status') == 'approved']
        pending = [x for x in rows if x.get('category_hint') == cat and x.get('review_status') != 'approved']
        categories[cat] = {'status':'PASS' if approved else ('PENDING' if pending else 'MISSING'),
                           'approved_ids':[x['id'] for x in approved],
                           'pending_ids':[x['id'] for x in pending]}
    scope = vas/'requirements.json'
    req = jread(scope) if scope.is_file() else {'schema_version':1,'project_id':pid,'core_modules':[]}
    if req.get('project_id') != pid:raise ValueError('核心模块范围登记的项目 ID 不一致')
    module_gaps = []
    for m in req.get('core_modules',[]):
        found=[x['id'] for x in rows if x.get('visual_category')=='module-photo' and x.get('review_status')=='approved'
              and x.get('technical_module','').casefold()==m['name'].casefold()
              and set(m['fact_ids']).intersection(x.get('fact_ids',[]))]
        module_gaps.append({'module':m['name'],'fact_ids':m['fact_ids'],'status':'PASS' if found else 'MISSING',
                            'approved_ids':found})
    if not module_gaps:
        categories['module-photo']['status'] = 'SCOPE-REQUIRED'
    status='PASS' if all(x['status']=='PASS' for x in categories.values()) and all(x['status']=='PASS' for x in module_gaps) else 'INCOMPLETE'
    print(json.dumps({'status':status,'project_id':pid,'categories':categories,
                      'core_module_photos':module_gaps,
                      'note':'四类图必须在真实技术事实允许的范围内完成；缺少证据不能凑图。若为纯软件项目，应在执行汇报中说明 module-photo 不适用，不能伪造。'},ensure_ascii=False,indent=2))


def preview(args):
    """Self-check a rendered SVG, then rasterize an exact-size PNG preview.

    v1.0.0 的预览截图用固定画布截 SVG，mmdc 的 width="100%" 输出被截成大片
    空白。本命令先校验 XML/根元素并推算真实像素尺寸（显式 width/height 优先，
    否则 viewBox 第 3/4 值），再按该尺寸无头截图；每次调用都打印自检报告。
    仅调用本机已安装 Chrome；不安装任何依赖、不联网。
    """
    import subprocess
    from xml.etree import ElementTree as ET
    root, base, vas, pid, facts = context(args.root, args.project_id)
    data = load_manifest(vas, pid)
    target = next((x for x in data['items'] if x['id'] == args.id), None)
    if target is None or not target.get('image_path'):
        raise ValueError('该资产没有已渲染 SVG：先执行 render')
    svg = (root / target['image_path']).resolve()
    if not svg.is_relative_to(root.resolve()) or not svg.is_file() or svg.suffix.lower() != '.svg':
        raise ValueError('SVG 路径不安全或文件缺失')
    text = svg.read_text('utf-8', errors='replace')
    try:
        xml_root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f'SVG 不是合法 XML：{exc}') from exc
    if xml_root.tag.split('}')[-1] != 'svg':
        raise ValueError('文件根元素不是 <svg>')
    tag_m = re.search(r'<svg\b[^>]*>', text, re.S)
    tag = tag_m.group(0) if tag_m else ''
    w_m = re.search(r'\swidth="([\d.]+)(?:px)?"', tag)
    h_m = re.search(r'\sheight="([\d.]+)(?:px)?"', tag)
    if w_m and h_m:
        width, height, size_source = float(w_m.group(1)), float(h_m.group(1)), 'width/height'
    else:
        vb_m = re.search(r'\sviewBox="([^"]+)"', tag)
        if not vb_m:
            raise ValueError('SVG 无显式 width/height 也无 viewBox，无法确定真实尺寸')
        parts = re.split(r'[\s,]+', vb_m.group(1).strip())
        if len(parts) != 4:
            raise ValueError('viewBox 不是四个数值')
        try:
            width, height = float(parts[2]), float(parts[3])
        except ValueError as exc:
            raise ValueError('viewBox 含非数值') from exc
        size_source = 'viewBox'
    w, h = int(round(width)), int(round(height))
    if not (40 <= w <= 8000 and 40 <= h <= 8000):
        raise ValueError(f'推算尺寸 {w}x{h} 超出可预览范围（40..8000）')
    browser = args.browser or os.environ.get('PUPPETEER_EXECUTABLE_PATH') \
        or next((str(c) for c in browser_candidates() if c.is_file()), None)
    if not browser or not Path(browser).is_file():
        raise ValueError('未找到可驱动的本机 Chrome；请用 --browser 指定已安装浏览器可执行文件')
    run_id = args.run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:7]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', run_id) or run_id in ('.', '..'):
        raise ValueError('非法 run-id')
    parent = root / '.skill-tmp' / 'technical-visual-assets'
    parent.mkdir(parents=True, exist_ok=True)
    run = parent / run_id
    if run.exists() and not (run / '.owned-by-technical-visual-assets').is_file():
        raise ValueError('运行目录缺少所有权标记，拒绝写入')
    if not run.exists():
        run.mkdir()
        (run / '.owned-by-technical-visual-assets').write_text(pid, 'utf-8')
    out_dir = run / 'preview'
    out_dir.mkdir(exist_ok=True)
    png = out_dir / f"{target['id']}.png"
    proc = subprocess.run([browser, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                           '--force-device-scale-factor=1', f'--screenshot={png}',
                           f'--window-size={w},{h}', svg.as_uri()],
                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
    if not png.is_file() or png.stat().st_size < 200:
        raise ValueError('浏览器截图失败：' + (proc.stderr or proc.stdout or '')[-300:])
    audit(base, pid, 'visual-asset-previewed', {'ids': [target['id']], 'run_id': run_id,
          'width': w, 'height': h, 'size_source': size_source})
    print(json.dumps({'status': 'PASS', 'id': target['id'], 'svg': rel(root, svg),
                      'xml_wellformed': True, 'root': 'svg',
                      'size_source': size_source, 'width': w, 'height': h,
                      'preview_png': str(png), 'preview_bytes': png.stat().st_size,
                      'installed_packages': 0}, ensure_ascii=False, indent=2))


def build_parser():
    p=argparse.ArgumentParser(description='项目范围内的技术图示与外部模块图片资产管理（不执行文书插图）')
    sub=p.add_subparsers(dest='command', required=True)
    for name,fn in [('scan-md',scan),('add-external',external),('render',render),('review',set_review),('list',report),('verify',verify),('workdir',workdir),('cleanup',cleanup),('scope-module',scope_module),('coverage',coverage),('add-diagram',add_diagram),('draft-from-ascii',draft_from_ascii),('preview',preview)]:
        q=sub.add_parser(name);q.add_argument('--root',required=True);q.add_argument('--project-id');q.set_defaults(func=fn)
        if name=='scan-md':q.add_argument('--technical-md',required=True)
        if name=='add-diagram':
            q.add_argument('--file',required=True);q.add_argument('--technical-md',required=True)
            q.add_argument('--category',required=True,choices=CATEGORIES);q.add_argument('--title',required=True)
            q.add_argument('--fact-ids',required=True);q.add_argument('--reason',required=True)
        if name=='draft-from-ascii':
            q.add_argument('--technical-md',required=True);q.add_argument('--category',required=True,choices=('system-framework','functional-architecture','flowchart'))
            q.add_argument('--start-line',type=int,required=True);q.add_argument('--end-line',type=int,required=True)
            q.add_argument('--title',required=True);q.add_argument('--fact-ids',required=True);q.add_argument('--reason',required=True)
        if name=='scope-module':
            q.add_argument('--technical-md',required=True);q.add_argument('--module',required=True)
            q.add_argument('--fact-ids',required=True);q.add_argument('--reason',required=True)
        if name=='add-external':
            for key in ['file','title','module','technical-md','source-page','image-url']:
                q.add_argument('--'+key,required=True)
            q.add_argument('--author');q.add_argument('--license')
        if name in ('render','preview'): q.add_argument('--id',required=True)
        if name=='preview':
            q.add_argument('--run-id',help='写入既有运行区（须含所有权标记），缺省新建')
            q.add_argument('--browser',help='本机 Chrome 可执行文件路径；缺省自动探测')
        if name in ('workdir','cleanup'): q.add_argument('--run-id',required=(name=='cleanup'))
        if name=='review':
            q.add_argument('--id',required=True);q.add_argument('--fact-ids',required=True)
            q.add_argument('--rights',required=True);q.add_argument('--reason',required=True)
            q.add_argument('--approve',action='store_true')
            q.add_argument('--category', choices=CATEGORIES, help='图像经核验后的四大类别')
            q.add_argument('--category-override-reason', help='类别与候选提示不符时，说明实际图义并承担审核责任')
            q.add_argument('--visual-evidence', help='实际查看图片后对图中主体/模块/节点的核对说明')
            q.add_argument('--full-module-confirmed', action='store_true', help='已逐图确认展示完整功能单元，而非裸芯片/电阻或局部零件')
            q.add_argument('--subject-level',choices=('complete-device','complete-module','complete-board'), help='实际目视确认的完整主体层级：独立设备/模组/整板')
            q.add_argument('--model-evidence', help='实际核对精确模块型号/厂家的说明，不得凭空编造')
            q.add_argument('--source-checked-at',help='确实执行核验的 ISO 日期/时间')
            q.add_argument('--checked-by',help='实际核验者/工具')
            q.add_argument('--permission-evidence',help='实际许可页面/授权文件或完整证据定位')
        if name=='list':q.add_argument('--approved-only',action='store_true')
    return p


def main():
    args=build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__': main()
