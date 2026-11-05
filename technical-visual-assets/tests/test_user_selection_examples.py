"""Regression gate for user-provided 3 negative / 2 positive visual examples.
This test checks packaging/linkage, not computer vision semantics.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
CASES={
 'negative-01-bare-sensor-chip.png': '反例 1',
 'negative-02-standalone-small-part.png': '反例 2',
 'negative-03-mcu-internal-block-diagram.png': '反例 3',
 'positive-01-complete-stepper-motor.png': '正例 1',
 'positive-02-complete-sensor-breakout-boards.png': '正例 2',
}
class UserImageSelectionTests(unittest.TestCase):
 def test_all_five_user_images_are_packaged(self):
  ref=(ROOT/'references/image-selection-examples.md').read_text('utf-8')
  for name,caption in CASES.items():
   with self.subTest(name=name):
    path=ROOT/'assets/image-selection-examples'/name
    self.assertTrue(path.is_file())
    self.assertGreater(path.stat().st_size,1000)
    self.assertEqual(path.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
    self.assertIn(name,ref)
    self.assertIn(caption,ref)
 def test_skill_loads_reference_and_never_relabels_negative_as_module(self):
  txt=(ROOT/'SKILL.md').read_text('utf-8')
  self.assertIn('references/image-selection-examples.md',txt)
  self.assertIn('裸芯片',txt)
  self.assertIn('完整步进电机',txt)
  self.assertIn('--subject-level',txt)
if __name__=='__main__':unittest.main()
