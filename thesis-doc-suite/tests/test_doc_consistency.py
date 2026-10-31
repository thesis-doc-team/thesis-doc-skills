#!/usr/bin/env python3
"""Doc/site/catalog consistency checks.

The shared metadata (core/contracts/skill-catalog.json) is the single source for
Skill names and commands. README.md and site/index.html must state exactly the
same commands and must not invent skills that do not exist.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'core' / 'contracts' / 'skill-catalog.json'


def read(path):
    return Path(path).read_text(encoding='utf-8')


class DocConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CATALOG.open('r', encoding='utf-8') as f:
            cls.catalog = json.load(f)
        cls.commands = [s['command'] for s in cls.catalog['skills']]
        cls.names = [s['name'] for s in cls.catalog['skills']]
        cls.readme = read(ROOT / 'README.md') if (ROOT / 'README.md').is_file() else ''
        cls.site = read(ROOT / 'site' / 'index.html') if (ROOT / 'site' / 'index.html').is_file() else ''

    def test_readme_exists_and_lists_all_commands(self):
        self.assertTrue(self.readme, 'README.md 缺失')
        for cmd in self.commands:
            self.assertIn(cmd, self.readme, f'README.md 缺少命令 {cmd}')

    def test_site_lists_all_commands(self):
        self.assertTrue(self.site, 'site/index.html 缺失')
        for cmd in self.commands:
            self.assertIn(cmd, self.site, f'site/index.html 缺少命令 {cmd}')

    def test_no_invented_commands(self):
        # any /thesis-doc-suite:xxx token in README or site must be a registered command
        known = set(self.commands)
        for label, text in (('README.md', self.readme), ('site/index.html', self.site)):
            for token in re.findall(r'/thesis-doc-suite:[a-z0-9\-]+', text):
                self.assertIn(token, known, f'{label} 出现未注册命令 {token}')

    def test_plugin_version_matches_catalog(self):
        with (ROOT / '.claude-plugin' / 'plugin.json').open('r', encoding='utf-8') as f:
            manifest = json.load(f)
        self.assertEqual(manifest['version'], self.catalog['plugin']['version'])
        self.assertEqual(manifest['name'], self.catalog['plugin']['name'])

    def test_skill_catalog_doc_lists_all_commands(self):
        path = ROOT / 'docs' / 'skill-catalog.md'
        self.assertTrue(path.is_file(), 'docs/skill-catalog.md 缺失')
        text = read(path)
        for cmd in self.commands:
            self.assertIn(cmd, text, f'docs/skill-catalog.md 缺少命令 {cmd}')

    def test_site_offline_no_cdn(self):
        self.assertTrue(self.site)
        for pattern in (r'(?:src|href)="https?://', r'@import\s+url\(\s*["\']?https?://'):
            self.assertIsNone(re.search(pattern, self.site),
                              f'site/index.html 存在外部资源引用：{pattern}')


if __name__ == '__main__':
    unittest.main(verbosity=1)
