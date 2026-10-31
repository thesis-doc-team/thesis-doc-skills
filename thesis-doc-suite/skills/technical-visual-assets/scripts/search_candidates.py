#!/usr/bin/env python3
"""Find *leads*, not trusted photos. No pip/npx, no image downloads.

Provider `auto` tries an already-installed DDGS and then the stdlib-only
Wikimedia Commons API. Empty/blocked results fall through. All failures are
reported; no invented or silently 'verified' image results.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def ddgs_search(query, limit):
    if importlib.util.find_spec('ddgs') is None:
        raise RuntimeError('DDGS_NOT_INSTALLED')
    from ddgs import DDGS
    rows=DDGS().images(query,max_results=limit)
    return [{'title':x.get('title'), 'source_page_url':x.get('url'),
        'image_url':x.get('image'), 'thumbnail_url':x.get('thumbnail'),
        'publisher':None,'license':'unverified','status':'candidate',
        'provider':'ddgs','model_verified':False,'source_verified':False}
        for x in rows if isinstance(x,dict) and x.get('url') and x.get('image')]


def commons_search(query,limit):
    params=urlencode({'action':'query','format':'json','generator':'search',
        'gsrsearch':query,'gsrnamespace':'6','gsrlimit':str(limit),
        'prop':'imageinfo','iiprop':'url|extmetadata'})
    url='https://commons.wikimedia.org/w/api.php?'+params
    req=Request(url,headers={'User-Agent':'ThesisDocSuite/0.4 (academic image lead discovery; no media download)'})
    with urlopen(req,timeout=12) as resp:
        doc=json.loads(resp.read(1_500_000))
    result=[]
    for p in doc.get('query',{}).get('pages',{}).values():
        info=(p.get('imageinfo') or [{}])[0]
        if not info.get('url') or not info.get('descriptionurl'):continue
        meta=info.get('extmetadata') or {}
        result.append({'title':p.get('title'), 'source_page_url':info['descriptionurl'],
            'image_url':info['url'],'thumbnail_url':None,'publisher':'Wikimedia Commons',
            'license_metadata_unverified':{key:meta.get(key,{}).get('value')
                for key in ('LicenseShortName','LicenseUrl','UsageTerms')},
            'license':'unverified','status':'candidate','provider':'commons',
            'model_verified':False,'source_verified':False})
    return result


def openverse_search(query,limit):
    """Public API metadata only. Cataloged license is NOT automatic reuse approval."""
    params=urlencode({'q':query,'page_size':str(min(limit,20)),'page':'1'})
    req=Request('https://api.openverse.org/v1/images/?'+params,
        headers={'User-Agent':'ThesisDocSuite/1.0 (academic image lead discovery; no downloads)',
                 'Accept':'application/json'})
    with urlopen(req,timeout=12) as resp:
        data=json.loads(resp.read(2_000_000))
    out=[]
    for row in data.get('results',[]):
        if not isinstance(row,dict):continue
        page=row.get('foreign_landing_url') or row.get('detail_url')
        media=row.get('url')
        if not page or not media:continue
        out.append({'title':row.get('title'),'source_page_url':page,
            'image_url':media,'thumbnail_url':row.get('thumbnail'),
            'publisher':row.get('provider') or row.get('source'),
            'creator_metadata_unverified':row.get('creator'),
            'license_metadata_unverified':{'license':row.get('license'),
                'license_version':row.get('license_version'),
                'license_url':row.get('license_url')},
            'license':'unverified','status':'candidate','provider':'openverse',
            'model_verified':False,'source_verified':False})
    return out


def plan_queries(module,engine,limit):
    # The *only* identifiers in generated queries come from the upstream MD + FACT.
    # Search modifiers describe image viewpoint; they are NOT project claims.
    if engine=='commons':
        return [module, module+' module', module+' board'][:limit]
    return [module+' full module product photo', module+' breakout board complete product',
            module+' 官方 模块 整板 实物图'][:limit]


def gather(module, provider='auto',limit=6,query=None,max_queries=3):
    channels=([provider] if provider!='auto' else
        (['ddgs','openverse','commons'] if importlib.util.find_spec('ddgs') else ['openverse','commons']))
    attempts=[]; results=[]; seen=set()
    for engine in channels:
        if len(results)>=limit:break
        queries=[query] if query else plan_queries(module,engine,max_queries)
        for q in queries:
            if len(results)>=limit:break
            try:
                matches=(ddgs_search(q, min(limit-len(results),10)) if engine=='ddgs'
                         else openverse_search(q,min(limit-len(results),10)) if engine=='openverse'
                         else commons_search(q,min(limit-len(results),10)))
                attempts.append({'provider':engine,'query':q,'count':len(matches),'status':'OK'})
                for cand in matches:
                    key=cand.get('image_url')
                    if not key or key in seen:continue
                    seen.add(key);cand['query_used']=q;results.append(cand)
            except Exception as e:
                attempts.append({'provider':engine,'query':q,'count':0,'status':'ERROR',
                                 'reason':str(e)[:250]})
        if engine=='ddgs' and not results and provider=='auto':
            continue
    return attempts,results[:limit]


def main():
    ap=argparse.ArgumentParser(description='保守搜索图片候选 URL，不下载文件、不安装软件、不核准授权')
    ap.add_argument('--root',required=True)
    ap.add_argument('--technical-md',required=True)
    ap.add_argument('--module',required=True)
    ap.add_argument('--fact-ids',required=True)
    ap.add_argument('--query',help='自定义关键词必须含有已确认的模块原名')
    ap.add_argument('--provider',choices=('auto','ddgs','openverse','commons'),default='auto')
    ap.add_argument('--limit',type=int,default=6)
    ap.add_argument('--max-queries',type=int,default=3)
    args=ap.parse_args()
    if not (1<=args.limit<=15 and 1<=args.max_queries<=3):ap.error('结果/查询次数超限')
    try:
        from visual_assets import context, technical_md, ALLOWED_FACT_STATES
        root,_,_,_,facts=context(args.root)
        md=technical_md(root,args.technical_md)
        module=args.module.strip()
        if len(module)<3 or module.casefold() not in md.read_text('utf-8-sig').casefold():
            raise ValueError('检索对象必须确实出现在正式技术 MD 中')
        ids=[i.strip() for i in args.fact_ids.split(',') if i.strip()]
        if not ids or any(fid not in facts or facts[fid].get('status') not in ALLOWED_FACT_STATES for fid in ids):
            raise ValueError('检索必须关联非 unverified 的 FACT ID')
        if not any(module.casefold() in facts[i].get('statement','').casefold() for i in ids):
            raise ValueError('关联的 FACT 未出现该对象，无法验证目标模块')
        if args.query and module.casefold() not in args.query.casefold():
            raise ValueError('自定义搜索词必须保留已确认的模块名称')
        attempts, results=gather(module,args.provider,args.limit,args.query,args.max_queries)
        status='CANDIDATES' if results else 'WARN'
        print(json.dumps({'status':status,'module':module,'fact_ids':ids,
            'attempts':attempts,'downloaded':0,'installed_packages':0,
            'results':results,'notice':'这里只得到搜索线索。项目实物型号、完整主体、原图和版权须分别核实；不要用相似板卡冒充项目硬件。'},
            ensure_ascii=False,indent=2))
        return 0
    except Exception as ex:
        print(json.dumps({'status':'WARN','reason':str(ex),'downloaded':0,
            'installed_packages':0,'results':[],
            'suggestion':'利用已有 WebSearch/浏览器继续找来源；本程序绝不安装额外包。'},
            ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
