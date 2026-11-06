#!/usr/bin/env python3
"""用结构化输入检查选题路由：允许专业/技术/想法混合；正式项目才需要题目+功能。"""
import argparse, json
from pathlib import Path


def route(d):
    if not isinstance(d,dict): raise ValueError('输入需要 JSON 对象')
    major = bool(str(d.get('major') or '').strip())
    tech = d.get('technologies') or d.get('keywords') or []
    tech = bool(tech if isinstance(tech,list) else str(tech).strip())
    title = bool(str(d.get('project_title') or d.get('title') or '').strip())
    features = d.get('features') or d.get('functional_requirements') or []
    features = bool(features if isinstance(features,list) else str(features).strip())
    intent = d.get('intent') or 'auto'
    if intent not in ('auto','discovery','formal'):
        raise ValueError('intent 仅允许 auto / discovery / formal')
    if intent=='formal' or (intent=='auto' and title and features and not d.get('still_exploring')):
        missing=[]
        if not title: missing.append('project_title')
        if not features: missing.append('features')
        return {'flow':'formal','status':'NEEDS_INPUT' if missing else 'READY',
                'missing':missing,'preserve_context':['major','technologies','keywords','resources','constraints']}
    if title: return {'flow':'discovery','entry':'project_idea','status':'READY','missing':[],
                      'note':'已有题目想法但未立项；可围绕想法推荐或迭代，不自动生成正式方案'}
    if tech: return {'flow':'discovery','entry':'technology_keywords','status':'READY','missing':[],
                     'note':'技术关键词与专业、兴趣、资源等混合分析'}
    if major: return {'flow':'discovery','entry':'major','status':'READY','missing':[],
                      'note':'只凭专业也允许开始发散探索'}
    return {'flow':'intake','status':'NEEDS_INPUT','missing':['major_or_technologies_or_project_idea'],
            'note':'直接询问想找什么方向的毕设/课程设计题目；入口只作内部路由'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(route(json.loads(args.input.read_text('utf-8'))),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
