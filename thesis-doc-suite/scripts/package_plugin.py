#!/usr/bin/env python3
"""Thesis Doc Suite — build a distributable ZIP archive (stdlib only).

Packages the plugin directory with everything needed to run, excluding caches,
temporary run files and archives. Refuses to package if structure verification
reports FAIL (run verify_plugin.py logic first).

Usage: python package_plugin.py [--plugin-root <dir>] [--out <dir>]
Output: <out>/thesis-doc-suite-<version>.zip  (+ SHA-256 printed)

The ZIP is a portability/distribution convenience: installation is still done by
extracting it and loading the directory (claude --plugin-dir) or registering a
local marketplace. ZIP is not an official Claude Code install channel.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import importlib.util

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {'__pycache__', '.git', '.skill-tmp', 'dist', 'node_modules'}
EXCLUDE_SUFFIX = {'.pyc', '.pyo', '.zip', '.tmp'}
EXCLUDE_NAMES = {'.asset-write.lock', '.DS_Store', 'Thumbs.db', '.write-probe'}


def iter_files(root: Path):
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDE_NAMES or path.suffix in EXCLUDE_SUFFIX:
            continue
        yield path, rel


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plugin-root', default=str(PLUGIN_ROOT))
    p.add_argument('--out', default=str(PLUGIN_ROOT.parent / 'dist'))
    p.add_argument('--skip-verify', action='store_true',
                   help='not recommended: package even if verification fails')
    args = p.parse_args(argv)
    root = Path(args.plugin_root).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_verify:
        spec = importlib.util.spec_from_file_location(
            'verify_plugin', root / 'scripts' / 'verify_plugin.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rc = mod.main(['--plugin-root', str(root)])
        if rc != 0:
            print('ERROR: 结构校验未通过，拒绝打包（--skip-verify 可强制）', file=sys.stderr)
            return 1

    with (root / '.claude-plugin' / 'plugin.json').open('r', encoding='utf-8') as f:
        version = json.load(f).get('version', '0.0.0')
    zip_path = out_dir / f'thesis-doc-suite-{version}.zip'

    count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, rel in iter_files(root):
            # top-level folder inside the archive is the plugin directory name
            zf.write(path, Path('thesis-doc-suite') / rel)
            count += 1

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    size_kb = zip_path.stat().st_size / 1024
    print(f'PACKAGED: {zip_path} ({count} files, {size_kb:.0f} KB)')
    print(f'SHA256: {digest}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
