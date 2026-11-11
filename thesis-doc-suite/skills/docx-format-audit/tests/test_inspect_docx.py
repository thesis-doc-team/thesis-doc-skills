#!/usr/bin/env python3
"""docx-format-audit 回归测试（仅标准库）。"""
import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inspect_docx import inspect_docx  # noqa: E402

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

DOCUMENT = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document {NS}><w:body>
  <w:p><w:pPr><w:pStyle w:val="BodyText"/><w:jc w:val="center"/></w:pPr>
    <w:r><w:rPr><w:b/><w:rFonts w:asciiTheme="minorHAnsi"/></w:rPr><w:t>正文段落</w:t></w:r>
  </w:p>
  <w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr><w:r><w:t>1.5 倍行距</w:t></w:r></w:p>
  <w:p><w:pPr><w:spacing w:line="360" w:lineRule="exact"/></w:pPr><w:r><w:t>固定 18 磅</w:t></w:r></w:p>
  <w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr>
    <w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="6000"/></w:tblGrid>
    <w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/><w:shd w:fill="F2F2F2"/></w:tcPr>
      <w:p><w:r><w:t>合并单元格</w:t></w:r></w:p></w:tc></w:tr>
  </w:tbl>
  <w:p><w:r><w:drawing><wp:inline><wp:extent cx="914400" cy="457200"/>
    <wp:docPr id="1" name="图片 1" descr="示例图片"/>
    <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
      <pic:pic><pic:blipFill><a:blip r:embed="rId2"/></pic:blipFill></pic:pic>
    </a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>
  <w:sectPr><w:pgSz w:w="11906" w:h="16838"/>
    <w:pgMar w:top="1440" w:bottom="1440" w:left="1800" w:right="1800" w:header="851" w:footer="992"/>
    <w:cols w:num="1"/><w:headerReference w:type="default" r:id="rId1"/>
  </w:sectPr>
</w:body></w:document>'''

STYLES = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {NS}>
  <w:docDefaults>
    <w:rPrDefault><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="宋体"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="BodyText"><w:name w:val="Body Text"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="120" w:line="360" w:lineRule="auto"/><w:ind w:firstLine="480"/></w:pPr>
    <w:rPr><w:sz w:val="28"/><w:rFonts w:eastAsia="仿宋_GB2312"/></w:rPr></w:style>
</w:styles>'''

THEME = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <a:themeElements>
    <a:clrScheme name="Office"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1></a:clrScheme>
    <a:fontScheme name="Office">
      <a:majorFont><a:latin typeface="Calibri Light"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="Times New Roman"/><a:ea typeface="宋体"/><a:cs typeface="Arial"/></a:minorFont>
    </a:fontScheme>
  </a:themeElements>
</a:theme>'''

NUMBERING = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering {NS}>
  <w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>
    <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/>
      <w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
      <w:rPr><w:rFonts w:ascii="Times New Roman"/></w:rPr></w:lvl>
  </w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>'''

HEADER = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr {NS}><w:p><w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t>页眉文字</w:t></w:r></w:p></w:hdr>'''

RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>'''

PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')


def build_docx(path):
    with ZipFile(path, 'w') as archive:
        archive.writestr('[Content_Types].xml',
                         '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        archive.writestr('word/document.xml', DOCUMENT)
        archive.writestr('word/styles.xml', STYLES)
        archive.writestr('word/theme/theme1.xml', THEME)
        archive.writestr('word/numbering.xml', NUMBERING)
        archive.writestr('word/_rels/document.xml.rels', RELS)
        archive.writestr('word/header1.xml', HEADER)
        archive.writestr('word/media/image1.png', PNG)


class DocxFormatAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / 'sample.docx'
        build_docx(cls.path)
        cls.data = inspect_docx(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_defaults_and_effective_inheritance(self):
        paragraph = self.data['paragraphs'][0]
        self.assertEqual(paragraph['style_chain'], ['Normal', 'BodyText'])
        effective = paragraph['effective']
        self.assertEqual(effective['font_size_pt'], 14.0)
        self.assertEqual(effective['font_east_asia'], '仿宋_GB2312')
        self.assertEqual(effective['alignment'], 'center')
        self.assertEqual(effective['spacing_before_pt'], 6.0)
        self.assertEqual(effective['line_spacing'], {'rule': 'auto', 'multiple': 1.5})
        self.assertEqual(effective['indent']['first_line_pt'], 24.0)
        run = paragraph['runs'][0]
        self.assertTrue(run['effective']['bold'])
        self.assertEqual(run['effective']['font_size_pt'], 14.0)
        self.assertEqual(run['effective']['font_ascii_resolved'], 'Times New Roman')
        self.assertEqual(run['effective']['font_east_asia'], '仿宋_GB2312')

    def test_line_spacing_rules(self):
        self.assertEqual(self.data['paragraphs'][1]['effective']['line_spacing'],
                         {'rule': 'auto', 'multiple': 1.5})
        self.assertEqual(self.data['paragraphs'][2]['effective']['line_spacing'],
                         {'rule': 'exact', 'pt': 18.0})

    def test_section_and_header(self):
        section = self.data['sections'][0]
        self.assertEqual(section['page_size_cm'], {'width': 21.001, 'height': 29.7})
        self.assertEqual(section['margins_cm']['left'], 3.175)
        self.assertEqual(section['headers'][0], {'type': 'default', 'part': 'word/header1.xml'})
        header = self.data['headers_footers'][0]
        self.assertEqual(header['type'], 'header')
        self.assertEqual(header['paragraphs'][0]['text'], '页眉文字')
        self.assertEqual(header['paragraphs'][0]['runs'][0]['effective']['font_size_pt'], 9.0)

    def test_table_and_numbering(self):
        table = self.data['tables'][0]
        self.assertEqual(table['columns_cm'], [5.292, 10.583])
        cell = table['rows'][0]['cells'][0]
        self.assertEqual(cell['grid_span'], 2)
        self.assertEqual(cell['shading'], 'F2F2F2')
        self.assertEqual(cell['paragraphs'][0]['text'], '合并单元格')
        numbering = self.data['numbering']
        self.assertEqual(numbering['abstract_numbers'][0]['levels'][0]['num_format'], 'decimal')
        self.assertEqual(numbering['instances'][0]['abstract_num_id'], 0)

    def test_image_dimensions_and_hash(self):
        image = self.data['images'][0]
        self.assertEqual(image['width_cm'], 2.54)
        self.assertEqual(image['height_cm'], 1.27)
        self.assertEqual(image['pixel_size'], [1, 1])
        self.assertEqual(len(image['sha256']), 64)
        self.assertEqual(image['description'], '示例图片')

    def test_theme_parsed(self):
        self.assertEqual(self.data['theme']['fonts']['minor']['latin'], 'Times New Roman')
        self.assertEqual(self.data['theme']['fonts']['minor']['ea'], '宋体')

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            inspect_docx(Path(self.tmp.name) / 'missing.docx')

    def test_invalid_package_raises(self):
        bad = Path(self.tmp.name) / 'bad.docx'
        bad.write_bytes(b'not a zip')
        with self.assertRaises(ValueError):
            inspect_docx(bad)


if __name__ == '__main__':
    unittest.main()
