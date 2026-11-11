#!/usr/bin/env python3
"""pptx-format-audit 回归测试（仅标准库）。"""
import base64
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from inspect_pptx import inspect_pptx  # noqa: E402

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
      'xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"')

PRESENTATION = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation {NS}>
  <p:sldSz cx="12192000" cy="6858000"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>
  <p:defaultTextStyle><a:lvl1pPr><a:defRPr sz="1800"><a:latin typeface="+mn-lt"/><a:ea typeface="+mn-ea"/></a:defRPr></a:lvl1pPr></p:defaultTextStyle>
</p:presentation>'''

PRESENTATION_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
</Relationships>'''

THEME = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <a:themeElements>
    <a:clrScheme name="Office"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1></a:clrScheme>
    <a:fontScheme name="Office">
      <a:majorFont><a:latin typeface="Calibri Light"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="Arial"/><a:ea typeface="微软雅黑"/><a:cs typeface="Arial"/></a:minorFont>
    </a:fontScheme>
  </a:themeElements>
</a:theme>'''

MASTER = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster {NS}>
  <p:cSld name="Office 主题">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      <p:sp><p:nvSpPr><p:cNvPr id="2" name="标题占位符"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="838200" y="365125"/><a:ext cx="10515600" cy="1325563"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>
      <p:sp><p:nvSpPr><p:cNvPr id="3" name="内容占位符"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="838200" y="1825625"/><a:ext cx="10515600" cy="4351338"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>
    </p:spTree>
  </p:cSld>
  <p:txStyles>
    <p:titleStyle><a:lvl1pPr><a:defRPr sz="4000" b="1"><a:latin typeface="+mj-lt"/></a:defRPr></a:lvl1pPr></p:titleStyle>
    <p:bodyStyle><a:lvl1pPr><a:defRPr sz="2000"><a:latin typeface="+mn-lt"/></a:defRPr></a:lvl1pPr></p:bodyStyle>
    <p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle>
  </p:txStyles>
</p:sldMaster>'''

MASTER_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>'''

LAYOUT = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout {NS} type="obj">
  <p:cSld name="标题和内容">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      <p:sp><p:nvSpPr><p:cNvPr id="2" name="标题 1"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="838200" y="365125"/><a:ext cx="10515600" cy="1325563"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>
      <p:sp><p:nvSpPr><p:cNvPr id="3" name="内容 2"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="838200" y="1825625"/><a:ext cx="10515600" cy="4351338"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle>
          <a:lvl1pPr><a:defRPr><a:solidFill><a:srgbClr val="333333"/></a:solidFill></a:defRPr></a:lvl1pPr>
        </a:lstStyle><a:p/></p:txBody></p:sp>
    </p:spTree>
  </p:cSld>
</p:sldLayout>'''

LAYOUT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''

SLIDE = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld {NS}>
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      <p:sp><p:nvSpPr><p:cNvPr id="2" name="标题 1"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr/>
        <p:txBody><a:bodyPr/><a:lstStyle/>
          <a:p><a:r><a:rPr sz="3600" b="1"><a:latin typeface="+mn-lt"/></a:rPr><a:t>示例标题</a:t></a:r></a:p>
        </p:txBody></p:sp>
      <p:sp><p:nvSpPr><p:cNvPr id="3" name="内容 2"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr/>
        <p:txBody><a:bodyPr/><a:lstStyle/>
          <a:p><a:r><a:t>要点文字</a:t></a:r></a:p>
        </p:txBody></p:sp>
      <p:sp><p:nvSpPr><p:cNvPr id="4" name="文本框 4"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="1800000" y="3600000"/><a:ext cx="3600000" cy="900000"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr wrap="none" anchor="ctr"/><a:lstStyle/>
          <a:p><a:pPr><a:lnSpc><a:spcPct val="150000"/></a:lnSpc><a:spcBef><a:spcPts val="600"/></a:spcBef>
            <a:buChar char="•"/></a:pPr>
            <a:r><a:rPr sz="1400"><a:latin typeface="Calibri"/></a:rPr><a:t>自定义文本</a:t></a:r></a:p>
        </p:txBody></p:sp>
      <p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="5" name="表格 5"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>
        <p:xfrm><a:off x="1800000" y="4600000"/><a:ext cx="4320000" cy="720000"/></p:xfrm>
        <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">
          <a:tbl><a:tblGrid><a:gridCol w="1800000"/><a:gridCol w="2520000"/></a:tblGrid>
            <a:tr h="720000">
              <a:tc><a:txBody><a:bodyPr/><a:p><a:r><a:t>A1</a:t></a:r></a:p></a:txBody><a:tcPr/></a:tc>
              <a:tc><a:txBody><a:bodyPr/><a:p><a:r><a:t>B1</a:t></a:r></a:p></a:txBody><a:tcPr/></a:tc>
            </a:tr>
          </a:tbl>
        </a:graphicData></a:graphic></p:graphicFrame>
      <p:pic><p:nvPicPr><p:cNvPr id="6" name="图片 6" descr="示例图片"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="rId2"/></p:blipFill>
        <p:spPr><a:xfrm><a:off x="1800000" y="6000000"/><a:ext cx="914400" cy="457200"/></a:xfrm></p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
</p:sld>'''

SLIDE_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/>
</Relationships>'''

NOTES = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:notes {NS}><p:cSld><p:spTree>
  <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>
  <p:sp><p:nvSpPr><p:cNvPr id="2" name="备注"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
    <p:spPr/><p:txBody><a:bodyPr/><a:p><a:r><a:t>备注文字</a:t></a:r></a:p></p:txBody></p:sp>
</p:spTree></p:cSld></p:notes>'''

PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')


def build_pptx(path):
    with ZipFile(path, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0"?>'
                         '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        archive.writestr('ppt/presentation.xml', PRESENTATION)
        archive.writestr('ppt/_rels/presentation.xml.rels', PRESENTATION_RELS)
        archive.writestr('ppt/theme/theme1.xml', THEME)
        archive.writestr('ppt/slideMasters/slideMaster1.xml', MASTER)
        archive.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels', MASTER_RELS)
        archive.writestr('ppt/slideLayouts/slideLayout1.xml', LAYOUT)
        archive.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels', LAYOUT_RELS)
        archive.writestr('ppt/slides/slide1.xml', SLIDE)
        archive.writestr('ppt/slides/_rels/slide1.xml.rels', SLIDE_RELS)
        archive.writestr('ppt/notesSlides/notesSlide1.xml', NOTES)
        archive.writestr('ppt/media/image1.png', PNG)


class PptxFormatAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / 'sample.pptx'
        build_pptx(cls.path)
        cls.data = inspect_pptx(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def slide(self):
        return self.data['slides'][0]

    def shape(self, shape_id):
        for item in self.slide()['shapes']:
            if item.get('id') == shape_id:
                return item
        raise AssertionError(f'shape {shape_id} not found')

    def test_presentation_and_theme(self):
        self.assertEqual(self.data['presentation']['slide_size_cm'],
                         {'width_cm': 33.867, 'height_cm': 19.05})
        self.assertEqual(self.data['presentation']['slide_count'], 1)
        self.assertEqual(self.data['theme']['fonts']['minor']['latin'], 'Arial')
        self.assertEqual(self.data['theme']['fonts']['minor']['ea'], '微软雅黑')

    def test_master_and_layout(self):
        self.assertEqual(self.data['masters'][0]['name'], 'Office 主题')
        self.assertEqual(self.data['layouts'][0]['name'], '标题和内容')
        self.assertEqual(self.data['layouts'][0]['master_index'], 0)
        self.assertEqual(len(self.data['masters'][0]['placeholders']), 2)
        self.assertEqual(self.slide()['layout_name'], '标题和内容')

    def test_title_inherits_master_title_style(self):
        title = self.shape(2)
        self.assertEqual(title['placeholder']['type'], 'title')
        # 位置从版式占位符继承
        self.assertEqual(title['position_cm']['left_cm'], 2.328)
        paragraph = title['text_body']['paragraphs'][0]
        run = paragraph['runs'][0]
        self.assertEqual(run['text'], '示例标题')
        self.assertEqual(run['effective']['font_size_pt'], 36.0)
        self.assertTrue(run['effective']['bold'])
        self.assertEqual(run['effective']['font_latin'], '+mn-lt')
        self.assertEqual(run['effective']['font_latin_resolved'], 'Arial')

    def test_body_inherits_layout_color_and_master_size(self):
        body = self.shape(3)
        paragraph = body['text_body']['paragraphs'][0]
        run = paragraph['runs'][0]
        self.assertEqual(run['effective']['font_size_pt'], 20.0)
        self.assertEqual(run['effective']['color'], '333333')
        self.assertEqual(run['effective']['font_latin_resolved'], 'Arial')
        self.assertEqual(run['effective']['font_ea'], '+mn-ea')
        self.assertEqual(run['effective']['font_ea_resolved'], '微软雅黑')

    def test_free_text_box_paragraph_format(self):
        textbox = self.shape(4)
        self.assertIsNone(textbox['placeholder'])
        paragraph = textbox['text_body']['paragraphs'][0]
        self.assertEqual(paragraph['line_spacing'], {'percent': 150.0})
        self.assertEqual(paragraph['space_before'], {'pt': 6.0})
        self.assertEqual(paragraph['bullet'], {'type': 'char', 'char': '•'})
        self.assertEqual(paragraph['runs'][0]['effective']['font_size_pt'], 14.0)
        self.assertEqual(textbox['text_body']['body']['wrap'], 'none')
        self.assertEqual(textbox['text_body']['body']['anchor'], 'ctr')

    def test_table(self):
        table = self.shape(5)
        self.assertEqual(table['kind'], 'table')
        self.assertEqual(table['table']['columns_cm'], [5.0, 7.0])
        self.assertEqual(table['table']['rows'][0]['height_cm'], 2.0)
        cells = table['table']['rows'][0]['cells']
        self.assertEqual(cells[0]['text_body']['paragraphs'][0]['runs'][0]['text'], 'A1')
        self.assertEqual(cells[1]['text_body']['paragraphs'][0]['runs'][0]['text'], 'B1')

    def test_picture_and_notes(self):
        picture = self.shape(6)
        self.assertEqual(picture['kind'], 'picture')
        self.assertEqual(picture['position_cm']['width_cm'], 2.54)
        self.assertEqual(picture['pixel_size'], [1, 1])
        self.assertEqual(len(picture['sha256']), 64)
        self.assertIn('备注文字', self.slide()['notes_text'])

    def test_invalid_package_raises(self):
        bad = Path(self.tmp.name) / 'bad.pptx'
        bad.write_bytes(b'not a zip')
        with self.assertRaises(ValueError):
            inspect_pptx(bad)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            inspect_pptx(Path(self.tmp.name) / 'missing.pptx')


if __name__ == '__main__':
    unittest.main()
