"""Offline regression tests for v1.3: MD only, upload-only photos and A4 geometry."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from argparse import Namespace
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1];SCRIPTS=ROOT/'scripts';sys.path.insert(0,str(SCRIPTS))
import md_pipeline as m
from hardware_requests import identify_modules
from visio_diagram import svg_diagram,drawio_diagram,validate
from a4_layout import inspect_template,fit_figure,audit_docx
from table_layout import parse_md_table,plan
from visual_assets import load_manifest,build_parser

DOC='''# 产品技术文档
## 1. 硬件架构
已完成树莓派 4B（8GB）开发环境配置；通过麦克风采集信号。
SHT40 传感器芯片为备用方案，当前未接入。
STM32F103C8T6 核心板通过 RS485 模块连接水浸传感器。
## 2. 功能树
```
系统
├── 数据采集
│   └── 传感器
└── 上传
```
## 3. 数据表
| 模块 | 接口 |
|---|---|
| 主控 | STM32F103C8T6 |
| 湿度 | SHT40 |
## 4. 关键流程
```mermaid
flowchart LR
  A[采集] --> B[确认]
```
'''

def sample_template(path,width=11906,height=16838,left=1417,right=1417):
    xml=f'''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:body><w:p/><w:sectPr><w:pgSz w:w="{width}" w:h="{height}"/><w:pgMar w:top="1417" w:bottom="1417" w:left="{left}" w:right="{right}" w:header="600" w:footer="600"/></w:sectPr></w:body></w:document>'''
    with ZipFile(path,'w') as z:z.writestr('word/document.xml',xml)

class OfflineSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project';self.root.mkdir()
        (self.root/'project-assets').mkdir()
        (self.root/'project-assets'/'project.json').write_text(json.dumps({'schema_version':1,'project_id':'P1'}),'utf-8')
        (self.root/'deliverables'/'technical-document').mkdir(parents=True)
        self.md=self.root/'deliverables'/'technical-document'/'tech.md';self.md.write_text(DOC,'utf-8')
        self.template=Path(self.tmp.name)/'official.docx';sample_template(self.template)

    def execute(self,command,**kw):
        data=dict(root=str(self.root),technical_md=str(self.md),project_id='P1',
                save=False,module_id='',file='',rights_declaration='',id='',decision='approved',
                evidence='',reviewer='human')
        data.update(kw)
        return m.execute(Namespace(command=command,**data))

    def test_extract_photo_modules_without_online_queries(self):
        out=self.execute('module-list')
        names=[x['name_from_md'] for x in out['requirements']]
        self.assertTrue(any('树莓派' in x for x in names))
        self.assertTrue(any('STM32' in x for x in names))
        self.assertTrue(any('SHT40' in x for x in names))
        self.assertTrue(any('麦克风' in x for x in names))
        self.assertTrue(any(x['claim_strength']=='spare-or-unconfirmed' for x in out['requirements'] if 'SHT40' in x['name_from_md']))
        self.assertTrue(all(x['user_upload_status']=='missing' for x in out['requirements']))

    def test_sync_idempotent_and_user_list(self):
        a=self.execute('sync');b=self.execute('sync')
        self.assertGreater(a['created'],0);self.assertEqual(b['created'],0)
        req=json.loads((self.root/'project-assets'/'resource-catalog'/'module-requests.json').read_text('utf-8'))
        self.assertEqual(req['total'],a['module_photo_requirements'])
        cat=m.load_catalog(self.root,'P1')
        self.assertTrue(all(x.get('a4_layout_status')=='pending-official-template-and-Word-render' for x in cat['items'] if x['kind'] in ('mermaid','markdown-table','ascii-tree')))

    def test_unauthorized_outside_upload_rejected(self):
        self.execute('sync');req=self.execute('module-list')['requirements'][0]
        x=Path(self.tmp.name)/'outside.png';x.write_bytes(b'garbage')
        with self.assertRaisesRegex(ValueError,'只允许读取本项目'):
            self.execute('upload-photo',module_id=req['id'],file=str(x),rights_declaration='用户提供自己的实物板卡照片并确认拥有使用权')

    def test_photo_upload_pending_review_and_dedup(self):
        # A valid tiny all-white PNG built with Python stdlib (no Pillow dependency).
        import struct,zlib
        def chunk(kind,data):
            return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        ihdr=struct.pack('>IIBBBBB',800,600,8,2,0,0,0)
        image_data=b''.join(b'\x00'+b'\xff\xff\xff'*800 for _ in range(600))
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',ihdr)+chunk(b'IDAT',zlib.compress(image_data))+chunk(b'IEND',b'')
        self.execute('sync');req=self.execute('module-list')['requirements'][0]
        up=self.root/'user-uploads';up.mkdir();photo=up/'actual.png'
        photo.write_bytes(png)
        k={'module_id':req['id'],'file':str(photo),'rights_declaration':'我自己拍摄的设备照片并且允许此项目的毕业文书使用'}
        a=self.execute('upload-photo',**k);b=self.execute('upload-photo',**k)
        self.assertEqual(a['vis_id'],b['vis_id'])
        self.assertEqual(a['status'],'UPLOADED_PENDING_REVIEW')
        records=m.load_catalog(self.root,'P1')['items']
        self.assertEqual(len([x for x in records if x['kind']=='user-upload-photo']),1)
        vis=load_manifest(self.root/'project-assets'/'visual-assets','P1')
        self.assertEqual(len(vis['items']),1)
        self.assertEqual(vis['items'][0]['origin'],'user-upload')
        self.assertNotEqual(vis['items'][0]['review_status'],'approved')
        with self.assertRaisesRegex(ValueError,'实物图必须在正式 VIS'):
            self.execute('review',id=a['id'],evidence='完成了实际审核并确认图片正确符合原技术文档的型号')

    def test_no_old_web_commands_or_code(self):
        self.assertFalse((SCRIPTS/'search_candidates.py').exists())
        self.assertFalse((SCRIPTS/'download_selected_image.py').exists())
        self.assertNotIn('search',m.main.__code__.co_consts)
        parsers=build_parser()
        # No CLI add-external flag remains.
        self.assertNotIn('add-external',parsers.format_help())
        self.assertNotIn('search', (SCRIPTS/'md_pipeline.py').read_text('utf-8').split('def main(')[-1])

    def test_project_isolation(self):
        bad=Path(self.tmp.name)/'outside.md';bad.write_text(DOC,'utf-8')
        with self.assertRaisesRegex(ValueError,'必须放在本项目'):
            self.execute('scan',technical_md=str(bad))
        with self.assertRaisesRegex(ValueError,'project_id 不一致'):
            self.execute('scan',project_id='P2')

    def test_a4_profile_real_margin(self):
        r=inspect_template(self.template)['sections'][0]
        self.assertTrue(r['is_a4']);self.assertAlmostEqual(r['content_width_mm'],160.02,delta=1)
        self.assertLess(r['figure_max_width_mm'],r['content_width_mm'])

    def test_fit_too_wide_makes_font_illegible(self):
        sec=inspect_template(self.template)['sections'][0]
        p=fit_figure(300,90,sec,9)
        self.assertEqual(p['status'],'NEEDS_RELAYOUT')
        self.assertLess(p['effective_text_pt'],9)

    def test_fit_still_needs_page_render(self):
        sec=inspect_template(self.template)['sections'][0]
        p=fit_figure(150,85,sec,10)
        self.assertEqual(p['status'],'PLANNED_NEEDS_PAGE_RENDER')

    def test_a4_audit_overflow_image(self):
        p=Path(self.tmp.name)/'bad.docx'
        root=f'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:body><w:p><w:r><w:drawing><wp:inline><wp:extent cx="7200000" cy="3000000"/></wp:inline></w:drawing></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:bottom="1417" w:left="1417" w:right="1417"/></w:sectPr></w:body></w:document>'''
        with ZipFile(p,'w') as z:z.writestr('word/document.xml',root)
        r=audit_docx(p)
        self.assertEqual(r['status'],'BLOCK_STATIC_ISSUES')
        self.assertIn('图片宽度超出版心',r['issues'][0])

    def test_table_as_word_columns_fit(self):
        rows=parse_md_table('| 项目 | 值 |\n|---|---|\n| A | 结果 |')
        p=plan(rows,inspect_template(self.template)['sections'][0])
        self.assertEqual(p['status'],'PLAN_READY_NEEDS_WORD_RENDER')
        self.assertLessEqual(p['table_width_mm'],160.5)

    def test_wide_table_must_split(self):
        rows=[['a']*13,['b']*13]
        p=plan(rows,inspect_template(self.template)['sections'][0])
        self.assertEqual(p['status'],'NEEDS_TABLE_SPLIT')

    def test_diagram_editable_and_white_black(self):
        spec=json.loads((ROOT/'examples'/'visio-style-example.json').read_text('utf-8'))
        svg=Path(self.tmp.name)/'graph.svg';edit=Path(self.tmp.name)/'graph.drawio'
        svg_diagram(spec,svg,inspect_template(self.template)['sections'][0])
        drawio_diagram(spec,edit,inspect_template(self.template)['sections'][0])
        content=svg.read_text('utf-8')
        self.assertIn('数据采集',content)
        self.assertIn('#fff',content)
        self.assertIn('marker-end',content)
        self.assertIn('mxGraphModel',edit.read_text('utf-8'))

    def test_attach_layout_checks_a4_and_catalog_link(self):
        self.execute('sync')
        cat=m.load_catalog(self.root,'P1')
        item=next(x for x in cat['items'] if x['kind']=='mermaid')
        spec=json.loads((ROOT/'examples'/'visio-style-example.json').read_text('utf-8'))
        svg=self.root/'project-assets'/'resource-catalog'/'diagrams'/'adopted.svg'
        editable=svg.with_suffix('.drawio')
        svg_diagram(spec,svg,inspect_template(self.template)['sections'][0])
        drawio_diagram(spec,editable,inspect_template(self.template)['sections'][0])
        result=self.execute('attach-layout',id=item['id'],svg=str(svg),drawio=str(editable),
            template=str(self.template),section=1,
            evidence='经逐条核对正式技术MD的流程关系并确认节点与箭头来源一致')
        self.assertEqual(result['status'],'A4_GEOMETRY_PASS_NEEDS_WORD_VISUAL_REVIEW')
        item2=next(x for x in m.load_catalog(self.root,'P1')['items'] if x['id']==item['id'])
        self.assertEqual(item2['a4_layout_status'],'geometry-pass-pending-Word-page-review')
        self.assertTrue(item2['editable_drawio'].endswith('.drawio'))

    def test_diagram_off_page_rejected(self):
        spec=json.loads((ROOT/'examples'/'visio-style-example.json').read_text('utf-8'))
        spec['width_mm']=190
        with self.assertRaisesRegex(ValueError,'超过实际 DOCX'):
            validate(spec,inspect_template(self.template)['sections'][0])

    def test_diagram_tiny_font_rejected(self):
        spec=json.loads((ROOT/'examples'/'visio-style-example.json').read_text('utf-8'))
        spec['font_pt']=7.5
        with self.assertRaisesRegex(ValueError,'9pt'):
            validate(spec,None)

    def test_seven_reference_images_packaged(self):
        refs=list((ROOT/'assets'/'word-figure-references').glob('*.png'))
        self.assertEqual(len(refs),7)
        text=(ROOT/'references'/'visio-style-a4-guide.md').read_text('utf-8')
        for f in refs:self.assertIn(f.name,text)

if __name__=='__main__':unittest.main()
