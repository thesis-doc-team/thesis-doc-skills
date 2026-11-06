#!/usr/bin/env python3
"""Thesis Doc Suite — plugin structure & consistency verification (stdlib only).

Checks:
  1. .claude-plugin/plugin.json manifest (valid JSON, kebab-case name, semver)
  2. skills/ directory: SKILL.md present, frontmatter name == directory name,
     description present; business skills declare explicit invocation
  3. Internal path references: files cited in each SKILL.md (scripts/, assets/,
     references/, templates/, examples/) actually exist inside the skill
  4. Official template SHA-256 locks (via core/template-protection/template_guard.py)
  5. skill-catalog.json <-> skills/ directory consistency
  6. Lint: no hard-coded personal absolute paths in SKILL.md / core / scripts

Usage: python verify_plugin.py [--plugin-root <dir>] [--json out.json]
Exit codes: 0 = PASS (warnings allowed); 1 = FAIL; 2 = usage/IO error.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import importlib.util

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$')
SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$')
# reference paths of the form <known-asset-dir>/<file> inside SKILL.md text.
# The lookbehind also excludes '-' so that "project-assets/references.json"
# does not yield a false "assets/references.json" match.
REF_RE = re.compile(r'(?<![\w/\-])((?:scripts|assets|references|templates|examples|tests)/'
                    r'[A-Za-z0-9_\-./一-龥]+\.(?:py|md|json|docx|html|txt|svg))')
ABS_PATH_RE = re.compile(r'(?:[A-Za-z]:\\\\|/home/|/Users/|C:\\\\Users\\\\)')

results = []


def record(level, area, message):
    results.append({'level': level, 'area': area, 'message': message})
    print(f'{level}: [{area}] {message}')


def parse_frontmatter(text):
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if not line or line.lstrip().startswith('#') or ':' not in line:
            continue
        key, _, val = line.partition(':')
        fm[key.strip()] = val.strip()
    return fm


def check_manifest(root):
    manifest = root / '.claude-plugin' / 'plugin.json'
    if not manifest.is_file():
        record('FAIL', 'manifest', f'缺少 {manifest}')
        return None
    try:
        with manifest.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        record('FAIL', 'manifest', f'plugin.json 解析失败：{exc}')
        return None
    name = data.get('name', '')
    if NAME_RE.match(name):
        record('PASS', 'manifest', f'name 合法：{name}')
    else:
        record('FAIL', 'manifest', f'name 不符合 kebab-case 规范：{name!r}')
    ver = data.get('version', '0.1.0')
    if SEMVER_RE.match(ver):
        record('PASS', 'manifest', f'version 合法：{ver}')
    else:
        record('FAIL', 'manifest', f'version 非语义化版本：{ver!r}')
    if data.get('description'):
        record('PASS', 'manifest', 'description 已填写')
    else:
        record('WARN', 'manifest', '缺少 description')
    return data


def check_skills(root):
    skills_root = root / 'skills'
    catalog_path = root / 'core' / 'contracts' / 'skill-catalog.json'
    catalog_names = []
    if catalog_path.is_file():
        with catalog_path.open('r', encoding='utf-8') as f:
            catalog_names = [s['name'] for s in json.load(f).get('skills', [])]
    else:
        record('FAIL', 'catalog', '缺少 core/contracts/skill-catalog.json')

    dir_names = sorted(d.name for d in skills_root.iterdir() if d.is_dir()) if skills_root.is_dir() else []
    if catalog_names:
        if sorted(catalog_names) == dir_names:
            record('PASS', 'catalog', f'skill-catalog.json 与 skills/ 目录一致（{len(dir_names)} 个）')
        else:
            only_cat = set(catalog_names) - set(dir_names)
            only_dir = set(dir_names) - set(catalog_names)
            record('FAIL', 'catalog', f'目录与注册表不一致；仅注册表={sorted(only_cat)} 仅目录={sorted(only_dir)}')

    for name in dir_names:
        skill_dir = skills_root / name
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.is_file():
            record('FAIL', 'skills', f'{name}: 缺少 SKILL.md')
            continue
        text = skill_md.read_text(encoding='utf-8')
        fm = parse_frontmatter(text)
        if fm.get('name') == name:
            record('PASS', 'skills', f'{name}: frontmatter name 与目录一致')
        else:
            record('FAIL', 'skills', f'{name}: frontmatter name={fm.get("name")!r} 与目录不一致')
        if fm.get('description'):
            record('PASS', 'skills', f'{name}: description 已声明')
        else:
            record('FAIL', 'skills', f'{name}: 缺少 description')
        if fm.get('version'):
            record('PASS', 'skills', f'{name}: version={fm.get("version")}')
        else:
            record('WARN', 'skills', f'{name}: frontmatter 未声明 version')
        if fm.get('disable-model-invocation') == 'true':
            record('PASS', 'skills', f'{name}: 仅显式调用（disable-model-invocation）')
        elif name in ('project-technical-doc', 'thesis-taskbook-write', 'opening-report-writer',
                      'literature-review-write', 'thesis-guidance-record-write',
                      'thesis-midterm-check-write', 'project-solution-write', 'init-project'):
            record('WARN', 'skills', f'{name}: 文书/写入类 Skill 建议声明 disable-model-invocation: true')


def check_internal_paths(root):
    broken = 0
    checked = 0
    for skill_dir in sorted((root / 'skills').iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding='utf-8')
        for ref in sorted(set(REF_RE.findall(text))):
            if '<' in ref or '$' in ref or ref.startswith('tests/'):
                continue  # templated paths or test-run artifacts
            checked += 1
            target = skill_dir / ref
            if not target.is_file():
                record('FAIL', 'paths', f'{skill_dir.name}/SKILL.md 引用的文件不存在：{ref}')
                broken += 1
    if not broken:
        record('PASS', 'paths', f'内部路径引用检查通过（共 {checked} 处引用）')


def check_template_locks(root):
    guard_path = root / 'core' / 'template-protection' / 'template_guard.py'
    spec = importlib.util.spec_from_file_location('template_guard', guard_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for skill_dir in sorted(d for d in (root / 'skills').iterdir() if d.is_dir()):
        status, msg = mod.verify_skill(skill_dir)
        record('FAIL' if status == 'BLOCK' else status, 'templates', msg)


def lint_paths(root):
    offenders = []
    targets = list((root / 'skills').glob('*/SKILL.md'))
    targets += list((root / 'core').rglob('*.md'))
    for path in targets:
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        for line in text.splitlines():
            if ABS_PATH_RE.search(line) and 'example' not in line.lower():
                offenders.append(f'{path.relative_to(root)}: {line.strip()[:80]}')
    if offenders:
        record('WARN', 'lint', f'疑似硬编码个人绝对路径 {len(offenders)} 处：{offenders[:5]}')
    else:
        record('PASS', 'lint', '未发现硬编码个人绝对路径')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plugin-root', default=str(PLUGIN_ROOT))
    p.add_argument('--json')
    args = p.parse_args(argv)
    root = Path(args.plugin_root).resolve()
    if not (root / '.claude-plugin').is_dir():
        print(f'ERROR: {root} 不是插件根目录', file=sys.stderr)
        return 2

    check_manifest(root)
    check_skills(root)
    check_internal_paths(root)
    check_template_locks(root)
    lint_paths(root)

    counts = {k: sum(1 for r in results if r['level'] == k) for k in ('PASS', 'WARN', 'FAIL')}
    print(f"\nSUMMARY: PASS={counts['PASS']} WARN={counts['WARN']} FAIL={counts['FAIL']}")
    if args.json:
        with Path(args.json).open('w', encoding='utf-8', newline='\n') as f:
            json.dump({'summary': counts, 'results': results}, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f'REPORT: {args.json}')
    return 1 if counts['FAIL'] else 0


if __name__ == '__main__':
    sys.exit(main())
