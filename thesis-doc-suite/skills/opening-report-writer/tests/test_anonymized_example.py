import hashlib
import sys
import unittest
from pathlib import Path
from zipfile import ZipFile
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_reference_example import check

class AnonymizedExampleTests(unittest.TestCase):
    def test_anonymized_example_no_leaks(self):
        self.assertEqual(check(),[])

    def test_example_not_official(self):
        sample=ROOT/'assets'/'reference-samples'/'sample-a-smart-interaction-anonymized.docx'
        official=ROOT/'assets'/'official-opening-report-template.docx'
        self.assertNotEqual(hashlib.sha256(sample.read_bytes()).digest(),hashlib.sha256(official.read_bytes()).digest())
        self.assertEqual(hashlib.sha256(official.read_bytes()).hexdigest(),(ROOT/'assets'/'template.sha256').read_text().strip())
        self.assertIn('【脱敏写作范本',Document(sample).tables[0].cell(0,0).text)

    def test_sample_does_not_ship_source(self):
        names=[p.name for p in (ROOT/'assets'/'reference-samples').iterdir() if p.is_file()]
        self.assertEqual(len([n for n in names if n.lower().endswith('.docx')]),1)
        self.assertIn('sample-a-smart-interaction-anonymized.docx',names)

if __name__=='__main__':unittest.main()
