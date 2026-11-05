import importlib.util
import pathlib
import unittest
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

S = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'three_line_table.py'
spec = importlib.util.spec_from_file_location('three_line_table', S)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def new_table():
    d=Document()
    t=d.add_table(rows=3, cols=3, style='Table Grid')
    for i,row in enumerate(t.rows):
        for j,cell in enumerate(row.cells):cell.text=f'R{i}C{j}'
    return d,t

class ThreeLineTests(unittest.TestCase):
    def test_new_table_can_be_converted_to_strict_three_line(self):
        _,t=new_table();module.apply_three_line(t)
        result=module.audit_three_line(t)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['rule_count'],3)
    def test_vertical_line_causes_block(self):
        _,t=new_table();module.apply_three_line(t)
        b=module.border_container(t.cell(0,0)._tc.get_or_add_tcPr(),'tcBorders')
        module.set_border(b,'right','single',8)
        self.assertEqual(module.audit_three_line(t)['status'],'BLOCK')
    def test_extra_inner_horizontal_causes_block(self):
        _,t=new_table();module.apply_three_line(t)
        b=module.border_container(t.cell(1,0)._tc.get_or_add_tcPr(),'tcBorders')
        module.set_border(b,'bottom','single',8)
        self.assertEqual(module.audit_three_line(t)['status'],'BLOCK')
    def test_grid_without_conversion_must_not_pass(self):
        _,t=new_table()
        self.assertEqual(module.audit_three_line(t)['status'],'BLOCK')
    def test_reject_merged_cell_without_deleting_data(self):
        _,t=new_table();t.cell(1,0).merge(t.cell(1,1))
        with self.assertRaises(ValueError):module.apply_three_line(t)
    def test_cells_are_centered_horizontally_and_vertically(self):
        _,t=new_table();module.apply_three_line(t)
        r=module.audit_three_line(t)
        self.assertEqual(r['status'],'PASS')
        self.assertTrue(r['alignment_centered'])
        for row in t.rows:
            for cell in row.cells:
                self.assertEqual(cell.vertical_alignment,WD_CELL_VERTICAL_ALIGNMENT.CENTER)
                for para in cell.paragraphs:
                    self.assertEqual(para.alignment,WD_ALIGN_PARAGRAPH.CENTER)
    def test_non_centered_alignment_blocks(self):
        _,t=new_table();module.apply_three_line(t)
        t.cell(1,1).paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.LEFT
        t.cell(1,2).vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.TOP
        r=module.audit_three_line(t)
        self.assertEqual(r['status'],'BLOCK')
        self.assertTrue(any('未水平居中' in x for x in r['problems']))
        self.assertTrue(any('未垂直居中' in x for x in r['problems']))
    def test_reject_missing_indices(self):
        with self.assertRaises(ValueError):module.table_indices(None,2)
    def test_roundtrip_save_still_passes(self):
        import tempfile
        d,t=new_table();module.apply_three_line(t)
        with tempfile.TemporaryDirectory() as p:
            path=pathlib.Path(p)/'test.docx';d.save(path)
            again=Document(path)
            self.assertEqual(module.audit_three_line(again.tables[0])['status'],'PASS')
if __name__=='__main__':unittest.main()
