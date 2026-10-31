#!/usr/bin/env python3
"""Generic official-template integrity guard (stdlib only).

Verifies each Skill's official Word template against its assets/template-lock.json
(SHA-256 pin + structural audit metadata). Never modifies templates.

Usage:
  python template_guard.py verify --skill-dir <path-to-skill> [--template <docx>]
  python template_guard.py verify-all --skills-root <path-to-skills>
  python template_guard.py hash --file <docx>     # print sha256 (for re-audits)

Exit code 0 = all PASS; 1 = any FAIL; 2 = usage/IO error.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

# Skills that pin their template via assets/template-lock.json (sha256 field).
# project-technical-doc has no Word template and is skipped automatically.
DEFAULT_TEMPLATE_NAMES = {
    'thesis-taskbook-write': 'official-taskbook-template.docx',
    'opening-report-writer': 'official-opening-report-template.docx',
    'literature-review-write': 'official-literature-review-template.docx',
    'thesis-guidance-record-write': 'official-guidance-template.docx',
    'thesis-midterm-check-write': 'official-midterm-template.docx',
}


def sha256_of(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_lock(skill_dir):
    lock_path = Path(skill_dir) / 'assets' / 'template-lock.json'
    if not lock_path.is_file():
        return None
    with lock_path.open('r', encoding='utf-8') as f:
        return json.load(f)


def verify_skill(skill_dir, template=None):
    """Return (status, message). status in PASS/WARN/BLOCK."""
    skill_dir = Path(skill_dir).resolve()
    name = skill_dir.name
    lock = load_lock(skill_dir)
    if lock is None:
        if name in DEFAULT_TEMPLATE_NAMES:
            return 'BLOCK', f'{name}: 缺少 assets/template-lock.json，无法保护官方模板'
        return 'PASS', f'{name}: 无 Word 模板（不需要模板锁）'
    pinned = lock.get('sha256')
    if not pinned:
        return 'BLOCK', f'{name}: template-lock.json 缺少 sha256 字段'
    if template is None:
        template = skill_dir / 'assets' / DEFAULT_TEMPLATE_NAMES.get(name, '')
        if not template.is_file():
            # fall back: first .docx directly under assets/ (not reference-samples)
            candidates = sorted((skill_dir / 'assets').glob('*.docx'))
            template = candidates[0] if candidates else None
    if template is None or not Path(template).is_file():
        return 'BLOCK', f'{name}: 找不到官方模板文件，无法核验哈希'
    actual = sha256_of(template)
    if actual != pinned:
        return 'BLOCK', (f'{name}: 官方模板哈希不匹配（期望 {pinned[:12]}…，实际 {actual[:12]}…）；'
                         '须停用填充坐标，重新审计适配，不得强灌')
    return 'PASS', f'{name}: 官方模板哈希匹配（{actual[:12]}…）'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('verify'); v.add_argument('--skill-dir', required=True)
    v.add_argument('--template', default=None)
    a = sub.add_parser('verify-all'); a.add_argument('--skills-root', required=True)
    h = sub.add_parser('hash'); h.add_argument('--file', required=True)
    args = p.parse_args(argv)
    try:
        if args.cmd == 'hash':
            print(sha256_of(args.file))
            return 0
        if args.cmd == 'verify':
            status, msg = verify_skill(args.skill_dir, args.template)
            print(f'{status}: {msg}')
            return 0 if status == 'PASS' else 1
        failed = 0
        root = Path(args.skills_root)
        for skill_dir in sorted(d for d in root.iterdir() if d.is_dir()):
            status, msg = verify_skill(skill_dir)
            print(f'{status}: {msg}')
            if status == 'BLOCK':
                failed = 1
        return failed
    except OSError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
