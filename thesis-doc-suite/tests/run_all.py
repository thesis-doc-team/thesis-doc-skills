#!/usr/bin/env python3
"""Thesis Doc Suite — master test runner.

Runs plugin-level checks plus every migrated Skill's own regression suite and
prints an honest summary (never marks un-run items as passed).

Usage: python tests/run_all.py [--json report.json]
Requires: Python 3.10+ with the plugin's requirements installed (Word suites
need python-docx/lxml/PyMuPDF; tech-doc suites need markdown-it-py/beautifulsoup4).
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

# (label, argv, cwd) — cwd None means plugin root
ITEMS = [
    ('plugin-structure', [str(ROOT / 'scripts' / 'verify_plugin.py')], ROOT),
    ('asset-consistency', [str(ROOT / 'tests' / 'test_asset_consistency.py')], ROOT),
    ('asset-isolation', [str(ROOT / 'tests' / 'test_asset_isolation.py')], ROOT),
    ('doc-consistency', [str(ROOT / 'tests' / 'test_doc_consistency.py')], ROOT),
    # per-Skill migrated regression suites (run inside each skill directory)
    ('techdoc: pipeline', ['tests/test_pipeline.py'], ROOT / 'skills' / 'project-technical-doc'),
    ('techdoc: project-assets', ['tests/test_project_assets.py'], ROOT / 'skills' / 'project-technical-doc'),
    ('techdoc: screenshot-audit', ['tests/test_screenshot_audit.py'], ROOT / 'skills' / 'project-technical-doc'),
    ('techdoc: svg-pipeline', ['tests/test_svg_pipeline.py'], ROOT / 'skills' / 'project-technical-doc'),
    ('techdoc: physical-modules', ['tests/test_physical_modules.py'], ROOT / 'skills' / 'project-technical-doc'),
    ('taskbook: pipeline', ['tests/test_pipeline.py'], ROOT / 'skills' / 'thesis-taskbook-write'),
    ('taskbook: reference-samples', ['tests/test_reference_samples.py'], ROOT / 'skills' / 'thesis-taskbook-write'),
    ('taskbook: shared-assets', ['tests/test_shared_assets.py'], ROOT / 'skills' / 'thesis-taskbook-write'),
    ('opening: anonymized-example', ['tests/test_anonymized_example.py'], ROOT / 'skills' / 'opening-report-writer'),
    ('opening: guards', ['tests/test_guards.py'], ROOT / 'skills' / 'opening-report-writer'),
    ('opening: pipeline', ['tests/test_pipeline.py'], ROOT / 'skills' / 'opening-report-writer'),
    ('opening: project-assets', ['tests/test_project_assets.py'], ROOT / 'skills' / 'opening-report-writer'),
    ('opening: render-chain', ['tests/test_render_chain.py'], ROOT / 'skills' / 'opening-report-writer'),
    ('opening: upgraded-contract', ['tests/test_upgraded_contract.py'], ROOT / 'skills' / 'opening-report-writer'),
    ('lit-review: smoke', ['tests/smoke_test.py'], ROOT / 'skills' / 'literature-review-write'),
    ('lit-review: regression', ['tests/test_regression.py'], ROOT / 'skills' / 'literature-review-write'),
    ('guidance: pipeline', ['tests/test_pipeline.py'], ROOT / 'skills' / 'thesis-guidance-record-write'),
    ('midterm: pipeline', ['tests/test_pipeline.py'], ROOT / 'skills' / 'thesis-midterm-check-write'),
    ('midterm: shared-assets', ['tests/test_shared_assets.py'], ROOT / 'skills' / 'thesis-midterm-check-write'),
    ('solution: pipeline', ['tests/test_pipeline.py'], ROOT / 'skills' / 'project-solution-write'),
    ('solution: html', ['tests/test_html_generation.py'], ROOT / 'skills' / 'project-solution-write'),
    ('solution: compose', ['tests/test_compose_markdown.py'], ROOT / 'skills' / 'project-solution-write'),
    ('visual: three-line-table', ['tests/test_three_line_table.py'], ROOT / 'skills' / 'technical-visual-assets'),
    ('visual: selection-examples', ['tests/test_user_selection_examples.py'], ROOT / 'skills' / 'technical-visual-assets'),
    ('visual: v1.3-a4', ['tests/test_v13_offline_a4.py'], ROOT / 'skills' / 'technical-visual-assets'),
    ('visual: v1.4-orthogonal', ['tests/test_v14_orthogonal_layout.py'], ROOT / 'skills' / 'technical-visual-assets'),
    ('visual: v1.4-vsdx', ['tests/test_v14_vsdx.py'], ROOT / 'skills' / 'technical-visual-assets'),
    ('visual: v1.4-word-render', ['tests/test_v14_word_render.py'], ROOT / 'skills' / 'technical-visual-assets'),
    ('visual: shared-assets', ['tests/test_shared_assets.py'], ROOT / 'skills' / 'technical-visual-assets'),
]

# tests that exercise rendering without LibreOffice may print WARN-style notes;
# a non-zero exit code is still counted as FAIL.


def run_item(label, argv, cwd):
    try:
        proc = subprocess.run([PY, *argv], cwd=str(cwd), capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=600)
    except subprocess.TimeoutExpired:
        return label, 'FAIL', '超时（600s）'
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    tail = ' | '.join(tail[-2:])[:300]
    return label, ('PASS' if proc.returncode == 0 else 'FAIL'), tail


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--json')
    args = p.parse_args(argv)
    results = []
    for label, cmd, cwd in ITEMS:
        if not all(Path(cwd, c).exists() if not c.startswith(str(ROOT)) else Path(c).exists()
                   for c in cmd):
            results.append((label, 'NOT-TESTED', '文件缺失'))
            continue
        label, status, tail = run_item(label, cmd, cwd)
        results.append((label, status, tail))
        print(f'{status:11s} {label}  {tail}')

    counts = {}
    for _, status, _ in results:
        counts[status] = counts.get(status, 0) + 1
    print(f"\nSUMMARY: {counts}")
    if args.json:
        with Path(args.json).open('w', encoding='utf-8', newline='\n') as f:
            json.dump({'summary': counts,
                       'results': [{'item': l, 'status': s, 'tail': t} for l, s, t in results]},
                      f, ensure_ascii=False, indent=2)
            f.write('\n')
        print(f'REPORT: {args.json}')
    return 1 if counts.get('FAIL') or counts.get('NOT-TESTED') else 0


if __name__ == '__main__':
    sys.exit(main())
