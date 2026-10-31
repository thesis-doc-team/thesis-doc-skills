#!/usr/bin/env python3
"""Optional, read-only image candidate search; NEVER downloads or installs packages.

Providers:
  ddgs: uses an already installed ddgs Python module. Never runs pip.
  commons: Wikimedia Commons public API via Python standard library only.
  auto: ddgs if available, otherwise commons.

These are search leads, NOT verified original photos and NOT permission grants.
Official sites, CSDN, and Baidu can be inspected via the Claude Code's existing
WebSearch/WebFetch/browser capability, if present. Don't fabricate unavailable tools.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def ddgs_search(query, limit):
    if importlib.util.find_spec('ddgs') is None:
        raise RuntimeError('ddgs 未安装。本 Skill 禁止自动安装依赖；改用已有 WebSearch/WebFetch 或 commons。')
    from ddgs import DDGS
    results = DDGS().images(query, max_results=limit)
    return [{'title':v.get('title'), 'source_page_url':v.get('url'),
             'image_url':v.get('image'), 'thumbnail_url':v.get('thumbnail'),
             'publisher':None, 'license':'unverified', 'status':'candidate', 'provider':'ddgs'}
            for v in results if isinstance(v,dict)]


def commons_search(query, limit):
    params = urlencode({'action':'query','format':'json','generator':'search',
                        'gsrsearch':query,'gsrnamespace':'6','gsrlimit':str(limit),
                        'prop':'imageinfo','iiprop':'url|extmetadata'})
    url = 'https://commons.wikimedia.org/w/api.php?' + params
    request = Request(url,headers={'User-Agent':'ThesisDocSuite/0.2 (academic source discovery; no bulk downloads)'})
    with urlopen(request,timeout=15) as response:
        blob = response.read(2_000_000)
    doc=json.loads(blob)
    result=[]
    for page in doc.get('query',{}).get('pages',{}).values():
        info=(page.get('imageinfo') or [{}])[0]
        if not info.get('url') or not info.get('descriptionurl'):
            continue
        meta=info.get('extmetadata') or {}
        license_info={key:meta.get(key,{}).get('value') for key in ('LicenseShortName','LicenseUrl','UsageTerms')}
        result.append({'title':page.get('title'), 'source_page_url':info['descriptionurl'],
             'image_url':info['url'], 'thumbnail_url':None,'publisher':'Wikimedia Commons',
             'license_metadata_unverified':license_info,'license':'unverified',
             'status':'candidate','provider':'commons'})
    return result


def main():
    ap=argparse.ArgumentParser(description='只读搜图，不下载文件，不安装包，不代表图片已核验')
    ap.add_argument('--root',required=True,help='现有项目资产包根目录')
    ap.add_argument('--technical-md',required=True,help='正式 project-technical-doc 技术 Markdown')
    ap.add_argument('--module',required=True,help='技术 MD 与关联 FACT 均出现的精确模块/型号')
    ap.add_argument('--fact-ids',required=True,help='用逗号分隔的真实 FACT ID')
    ap.add_argument('--query',help='不填则自动使用模块名+官方整模块实物图；自定义查询必须包含模块原名')
    ap.add_argument('--provider',choices=('auto','ddgs','commons'),default='auto')
    ap.add_argument('--limit',type=int,default=6)
    args=ap.parse_args()
    if not (1<=args.limit<=15):ap.error('结果上限非法')
    try:
        # Search terms can NEVER be inferred from search results. They must be
        # explicitly present in the upstream project-technical-doc and FACT.
        from visual_assets import context, technical_md, ALLOWED_FACT_STATES
        root,_,_,_,facts=context(args.root)
        md=technical_md(root,args.technical_md)
        module=args.module.strip()
        if len(module)<3 or module.casefold() not in md.read_text('utf-8-sig').casefold():
            raise ValueError('搜索模块未出现在 project-technical-doc 的正式技术 MD 中')
        ids=[x.strip() for x in args.fact_ids.split(',') if x.strip()]
        if not ids or any(x not in facts or facts[x].get('status') not in ALLOWED_FACT_STATES for x in ids):
            raise ValueError('搜索必须绑定可核验的真实 FACT ID')
        if not any(module.casefold() in facts[x].get('statement','').casefold() for x in ids):
            raise ValueError('关联 FACT 中未出现对应模块/型号，拒绝查询无事实依据的图片')
        query=args.query.strip() if args.query else module+' 官方 整体 模块 实物图'
        if module.casefold() not in query.casefold():
            raise ValueError('图片搜索关键词必须包含已确认模块或型号原名')
        engine=args.provider
        if engine=='auto':engine='ddgs' if importlib.util.find_spec('ddgs') else 'commons'
        results=ddgs_search(query,args.limit) if engine=='ddgs' else commons_search(query,args.limit)
        print(json.dumps({'status':'CANDIDATES','provider':engine,'query':query,'module':module,'fact_ids':ids,
             'downloaded':0,'installed_packages':0,'results':results,
             'warning':'搜索结果仅是候选；须打开来源页、目视确认完整模块、验证许可后才能另行入库。'},ensure_ascii=False,indent=2))
    except Exception as ex:
        print(json.dumps({'status':'WARN','downloaded':0,'installed_packages':0,'reason':str(ex),
              'suggestion':'使用现有 Claude Code WebSearch/WebFetch 或已连接浏览器核查来源；不要自动安装依赖。'},ensure_ascii=False),file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':sys.exit(main())
