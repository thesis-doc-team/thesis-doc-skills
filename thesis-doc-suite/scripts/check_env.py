#!/usr/bin/env python3
"""Thesis Doc Suite — environment & project readiness checks (stdlib only).

Prints PASS / WARN / BLOCK lines for runtime environment, plugin structure and
(optionally) project asset status. BLOCK means the current operation cannot be
executed reliably; WARN means it can continue with reduced completeness.

Usage:
  python check_env.py                                  # environment + plugin structure
  python check_env.py --root <PROJECT_ROOT>            # + project asset checks
  python check_env.py --root <PROJECT_ROOT> --skill thesis-taskbook-write
  python check_env.py --json report.json               # also write machine-readable report

Exit codes: 0 = no BLOCK; 1 = at least one BLOCK; 2 = usage/IO error.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PLUGIN_ROOT / 'skills'
CATALOG = PLUGIN_ROOT / 'core' / 'contracts' / 'skill-catalog.json'

# reference-count thresholds that a document Skill requires before final delivery
REF_THRESHOLDS = {'thesis-taskbook-write': 10, 'opening-report-writer': 10,
                  'literature-review-write': 8}

results = []


def record(level, area, message):
    results.append({'level': level, 'area': area, 'message': message})
    print(f'{level}: [{area}] {message}')


def check_python():
    v = sys.version_info
    if v < (3, 9):
        record('BLOCK', 'python', f'Python {v.major}.{v.minor} 过旧，需要 3.10+（最低 3.9）')
    elif v < (3, 10):
        record('WARN', 'python', f'Python {v.major}.{v.minor}，建议 3.10+')
    else:
        record('PASS', 'python', f'Python {v.major}.{v.minor}.{v.micro}')


def check_module(mod, pip_name, area, required_by, hard):
    if importlib.util.find_spec(mod) is not None:
        record('PASS', area, f'{pip_name} 已安装')
        return True
    level = 'BLOCK' if hard else 'WARN'
    record(level, area, f'缺少 {pip_name}（{required_by}）；pip install {pip_name}')
    return False


def check_environment(skill=None):
    check_python()
    word_hard = skill in REF_THRESHOLDS or skill in (
        'thesis-guidance-record-write', 'thesis-midterm-check-write')
    html_hard = skill == 'project-technical-doc'
    check_module('docx', 'python-docx', 'deps', 'Word 文书生成', word_hard)
    check_module('lxml', 'lxml', 'deps', 'Word 结构校验', word_hard)
    check_module('fitz', 'PyMuPDF', 'deps', '逐页渲染截图', word_hard)
    check_module('markdown_it', 'markdown-it-py', 'deps', '技术文档 HTML', html_hard)
    check_module('bs4', 'beautifulsoup4', 'deps', '技术文档 HTML', html_hard)

    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if soffice:
        record('PASS', 'render', f'LibreOffice 可用：{soffice}')
    else:
        record('WARN', 'render', '未检测到 LibreOffice；逐页渲染/截图验证将无法执行（Word 文书交付前必须完成截图验证分析，届时此项升为 BLOCK 级障碍，须安装或提供等价渲染器）')
    record('PASS', 'wps', 'WPS 客户端无法自动检测；只有用户实际用 WPS 打开后才可声明"WPS 已验证"')


def check_plugin_structure():
    manifest = PLUGIN_ROOT / '.claude-plugin' / 'plugin.json'
    if not manifest.is_file():
        record('BLOCK', 'plugin', f'缺少插件清单 {manifest}')
        return
    try:
        with manifest.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        record('BLOCK', 'plugin', f'plugin.json 解析失败：{exc}')
        return
    name = data.get('name', '')
    if name == 'thesis-doc-suite':
        record('PASS', 'plugin', f'插件清单合法（name={name}, version={data.get("version")}）')
    else:
        record('BLOCK', 'plugin', f'插件 name 异常：{name!r}（应为 thesis-doc-suite）')

    if not CATALOG.is_file():
        record('BLOCK', 'plugin', '缺少 core/contracts/skill-catalog.json')
        return
    with CATALOG.open('r', encoding='utf-8') as f:
        catalog = json.load(f)
    missing = []
    for item in catalog.get('skills', []):
        skill_md = SKILLS_ROOT / item['name'] / 'SKILL.md'
        if not skill_md.is_file():
            missing.append(item['name'])
    if missing:
        record('BLOCK', 'plugin', f'SKILL.md 缺失：{missing}')
    else:
        record('PASS', 'plugin', f'{len(catalog.get("skills", []))} 个 Skill 目录齐全')

    guard = PLUGIN_ROOT / 'core' / 'template-protection' / 'template_guard.py'
    spec = importlib.util.spec_from_file_location('template_guard', guard)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for skill_dir in sorted(d for d in SKILLS_ROOT.iterdir() if d.is_dir()):
        status, msg = mod.verify_skill(skill_dir)
        record(status, 'template', msg)


def check_project(root, skill=None):
    root = Path(root).resolve()
    if not root.is_dir():
        record('BLOCK', 'project', f'项目根目录不存在或不可读：{root}')
        return
    if not os_access_write(root):
        record('BLOCK', 'project', f'项目根目录不可写：{root}')
        return
    record('PASS', 'project', f'项目根目录可用：{root}')

    base = root / 'project-assets'
    proj = base / 'project.json'
    if not proj.is_file():
        record('WARN', 'assets', '项目资产包尚未初始化；先运行 /thesis-doc-suite:init-project 或 core/asset-management/project_assets.py init')
        return
    try:
        with proj.open('r', encoding='utf-8') as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        record('BLOCK', 'assets', f'project.json 解析失败：{exc}')
        return
    if meta.get('schema_version') != 1 or not meta.get('project_id'):
        record('BLOCK', 'assets', 'project.json 缺少 schema_version=1 或 project_id')
        return
    record('PASS', 'assets', f'资产包已初始化（project_id={meta["project_id"]}, name={meta.get("name")}）')

    def items(kind):
        p = base / f'{kind}.json'
        if not p.is_file():
            return []
        with p.open('r', encoding='utf-8') as f:
            return json.load(f).get('items', [])

    refs = items('references')
    facts = items('facts')
    prog = items('progress')
    verified = sum(1 for r in refs if r.get('verified') is True)
    record('PASS', 'assets', f'数据规模：facts={len(facts)}, references={len(refs)}（已核验 {verified}）, progress={len(prog)}')

    sched = base / 'schedule.json'
    plan = None
    if sched.is_file():
        with sched.open('r', encoding='utf-8') as f:
            plan = json.load(f).get('plan')
    if plan is None:
        record('WARN', 'assets', '尚无共享周计划（schedule.json plan 为空）；任务书/开题/中期需要计划时可现场拟定 draft')
    else:
        record('PASS', 'assets', f'共享周计划：id={plan.get("id")}, status={plan.get("status")}, total_weeks={plan.get("total_weeks")}')

    if not (root / 'deliverables').is_dir():
        record('WARN', 'assets', 'deliverables/ 成品目录尚未创建（生成时会自动建立）')

    if skill:
        threshold = REF_THRESHOLDS.get(skill)
        if threshold:
            if verified >= threshold:
                record('PASS', 'skill', f'{skill}: 已核验文献 {verified} 篇 ≥ 门槛 {threshold}')
            else:
                record('WARN', 'skill', f'{skill}: 已核验文献 {verified} 篇 < 门槛 {threshold}；执行时需补检索真实文献，禁止伪造凑数')
        if skill in ('thesis-taskbook-write', 'opening-report-writer', 'literature-review-write',
                     'thesis-guidance-record-write', 'thesis-midterm-check-write'):
            if facts:
                record('PASS', 'skill', f'{skill}: 有 {len(facts)} 条共享技术事实可复用')
            else:
                record('WARN', 'skill', f'{skill}: 尚无共享技术事实；建议先运行 project-technical-doc 或直接依据本轮技术资料写作并入库')


def os_access_write(path):
    try:
        probe = Path(path) / '.write-probe'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink()
        return True
    except OSError:
        return False


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', help='项目根目录 <PROJECT_ROOT>')
    p.add_argument('--skill', help='目标 Skill 名称（按其门槛检查）')
    p.add_argument('--json', help='将结构化结果写入 JSON 文件')
    args = p.parse_args(argv)

    check_environment(args.skill)
    check_plugin_structure()
    if args.root:
        check_project(args.root, args.skill)
    else:
        record('PASS', 'project', '未指定 --root，跳过项目数据检查')

    counts = {k: sum(1 for r in results if r['level'] == k) for k in ('PASS', 'WARN', 'BLOCK')}
    print(f"\nSUMMARY: PASS={counts['PASS']} WARN={counts['WARN']} BLOCK={counts['BLOCK']}")
    if args.json:
        with Path(args.json).open('w', encoding='utf-8', newline='\n') as f:
            json.dump({'summary': counts, 'results': results}, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f'REPORT: {args.json}')
    return 1 if counts['BLOCK'] else 0


if __name__ == '__main__':
    sys.exit(main())
