"""Minimal regression tests. No network and no Word editing."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'visual_assets.py'


class VisualAssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        a = self.root/'project-assets'; a.mkdir()
        (a/'project.json').write_text(json.dumps({'project_id':'P-001','schema_version':1,'name':'测试'}), 'utf-8')
        (a/'facts.json').write_text(json.dumps({'project_id':'P-001','schema_version':1,'items':[
            {'id':'FACT-001','statement':'采用STM32F407','source':'技术文档 §4','status':'declared'},
            {'id':'FACT-002','statement':'待确认串口号','source':'技术文档 §5','status':'unverified'}]}), 'utf-8')
        (a/'activity.jsonl').write_text('', 'utf-8')
        d=self.root/'deliverables'/'technical-document';d.mkdir(parents=True)
        self.md=d/'测试-技术文档.md'
        self.md.write_text('# 系统技术文档\n\n## 系统架构\n\n```mermaid\nflowchart TD\n A[STM32F407] --> B[传感器]\n```\n', 'utf-8')

    def tearDown(self):self.tmp.cleanup()

    def cli(self,*args,ok=True):
        cmd=[sys.executable,str(SCRIPT),*args,'--root',str(self.root),'--project-id','P-001']
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace')
        if ok:self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        else:self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
        return json.loads(p.stdout or p.stderr)

    def test_scan_deduplicate_and_project_isolation(self):
        r=self.cli('scan-md','--technical-md',str(self.md));self.assertEqual(r['found'],1)
        idx=self.root/'project-assets'/'visual-assets'/'index.json'
        data=json.loads(idx.read_text('utf-8'));self.assertEqual(len(data['items']),1)
        id_=data['items'][0]['id'];self.assertTrue((self.root/data['items'][0]['source_path']).is_file())
        self.cli('scan-md','--technical-md',str(self.md))
        self.assertEqual(len(json.loads(idx.read_text('utf-8'))['items']),1)
        self.cli('review','--id',id_,'--fact-ids','FACT-001','--rights','owned',
                 '--reason','先渲染才能批准','--approve',ok=False)
        p=subprocess.run([sys.executable,str(SCRIPT),'list','--root',str(self.root),'--project-id','OTHER'],capture_output=True,text=True,encoding='utf-8',errors='replace')
        self.assertNotEqual(p.returncode,0)

    def test_external_candidate_needs_real_review_and_fact(self):
        # Synthetic 640x480 valid PNG fixture. This tests metadata and command gates,
        # NOT whether the file actually depicts a STM32 board or has real permissions.
        import struct, zlib
        def chunk(tag, data):
            return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
        img=self.root/'sample.png'
        rows=(b'\x00'+b'\xff\xff\xff'*640)*480
        img.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',640,480,8,2,0,0,0))+
                        chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))
        r=self.cli('add-external','--file',str(img),'--title','模块候选','--module','STM32F407','--technical-md',str(self.md),
                   '--source-page','https://example.org/page','--image-url','https://example.org/image.png')
        self.assertEqual(r['status'],'CANDIDATE'); id_=r['id']
        self.assertEqual(self.cli('list','--approved-only')['total'],0)
        self.cli('review','--id',id_,'--fact-ids','FACT-002','--rights','owned','--reason','test',
                 '--category','module-photo','--visual-evidence','模拟测试核查图片完整模块外观与型号一致','--full-module-confirmed','--model-evidence','模拟测试核对厂家完整型号 STM32F407 与技术MD一致',
                 '--approve','--source-checked-at','2026-10-31','--checked-by','reviewer',ok=False)
        self.cli('review','--id',id_,'--fact-ids','FACT-001','--rights','unverified','--reason','test',
                 '--category','module-photo','--visual-evidence','模拟测试核查图片完整模块外观与型号一致','--full-module-confirmed','--model-evidence','模拟测试核对厂家完整型号 STM32F407 与技术MD一致',
                 '--approve','--source-checked-at','2026-10-31','--checked-by','reviewer',ok=False)
        self.cli('review','--id',id_,'--fact-ids','FACT-001','--rights','owned','--reason','test',
                 '--category','module-photo','--visual-evidence','模拟测试核查图片完整模块外观与型号一致','--full-module-confirmed','--model-evidence','模拟测试核对厂家完整型号 STM32F407 与技术MD一致',
                 '--approve',ok=False)
        self.cli('review','--id',id_,'--fact-ids','FACT-001','--rights','owned','--reason','test',
                 '--category','module-photo','--visual-evidence','模拟测试核查图片完整模块外观与型号一致','--full-module-confirmed','--model-evidence','模拟测试核对厂家完整型号 STM32F407 与技术MD一致',
                 '--approve','--source-checked-at','2026-10-31','--checked-by','reviewer','--permission-evidence','https://example.org/license',ok=False)  # 缺完整主体层级声明
        self.cli('review','--id',id_,'--fact-ids','FACT-001','--rights','owned','--reason','test',
                 '--category','module-photo','--visual-evidence','模拟测试核查图片完整模块外观与型号一致','--full-module-confirmed','--model-evidence','模拟测试核对厂家完整型号 STM32F407 与技术MD一致',
                 '--approve','--subject-level','complete-board','--source-checked-at','2026-10-31','--checked-by','reviewer','--permission-evidence','https://example.org/license')
        self.assertEqual(self.cli('list','--approved-only')['total'],1)
        self.assertEqual(self.cli('verify')['status'],'PASS')
        self.assertEqual(self.cli('add-external','--file',str(img),'--title','模块候选','--module','STM32F407','--technical-md',str(self.md),
                   '--source-page','https://example.org/page','--image-url','https://example.org/image.png')['status'],'EXISTS')

    def test_scope_and_four_categories_missing(self):
        res=self.cli('coverage');self.assertEqual(res['status'],'INCOMPLETE')
        self.assertEqual(res['categories']['module-photo']['status'],'SCOPE-REQUIRED')
        self.cli('scope-module','--technical-md',str(self.md),'--module','STM32F407',
                 '--fact-ids','FACT-001','--reason','核心主控板型来自技术文档')
        res=self.cli('coverage')
        self.assertEqual(len(res['core_module_photos']),1)
        self.assertEqual(res['core_module_photos'][0]['status'],'MISSING')
        self.cli('scope-module','--technical-md',str(self.md),'--module','未出现的板卡型号',
                 '--fact-ids','FACT-001','--reason','假模块',ok=False)

    def test_new_diagram_requires_evidence_and_review(self):
        src=self.root/'functional.mmd'
        src.write_text('flowchart TD\n A[采集] --> B[显示]\n','utf-8')
        self.cli('add-diagram','--file',str(src),'--technical-md',str(self.md),
                 '--title','功能架构图','--category','functional-architecture','--fact-ids','FACT-002',
                 '--reason','测试',ok=False)
        out=self.cli('add-diagram','--file',str(src),'--technical-md',str(self.md),
                 '--title','功能架构图','--category','functional-architecture','--fact-ids','FACT-001',
                 '--reason','项目技术事实可支持此示例关系')
        self.assertEqual(out['status'],'CANDIDATE')
        c=self.cli('coverage')
        self.assertEqual(c['categories']['functional-architecture']['status'],'PENDING')
        self.cli('review','--id',out['id'],'--fact-ids','FACT-001',
                 '--category','module-photo','--rights','owned','--reason','非法分类',
                 '--visual-evidence','已核查所有节点与真实技术事实对应一致', '--approve',ok=False)

    def test_local_project_figure_from_final_md(self):
        import struct,zlib
        def chunk(tag,data):
            return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
        local=self.md.parent/'system.png'
        pixels=(b'\x00'+b'\xff\xff\xff'*16)*16
        local.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',16,16,8,2,0,0,0))+
                          chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b''))
        self.md.write_text(self.md.read_text('utf-8')+'\n![系统总体架构图](system.png)\n','utf-8')
        result=self.cli('scan-md','--technical-md',str(self.md))
        self.assertEqual(result['found'],2)
        index=json.loads((self.root/'project-assets'/'visual-assets'/'index.json').read_text('utf-8'))
        rec=[x for x in index['items'] if x['kind']=='technical-figure'][0]
        self.assertEqual(rec['category_hint'],'system-framework')
        self.assertTrue((self.root/rec['image_path']).is_file())
        self.assertEqual(self.cli('verify')['status'],'WARN') # candidate pending fact/license review

    def test_image_download_requires_explicit_optin(self):
        script=Path(__file__).resolve().parents[1]/'scripts'/'download_selected_image.py'
        p=subprocess.run([sys.executable,str(script),'--root',str(self.root),'--run-id','r',
                '--image-url','https://example.org/image.png'],capture_output=True,text=True,encoding='utf-8',errors='replace')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('allow-image-download',p.stderr)

    def test_workdir_cleanup_scope(self):
        p=self.cli('workdir','--run-id','test-run');self.assertTrue(Path(p['path']).is_dir())
        self.cli('cleanup','--run-id','test-run')
        self.assertFalse(Path(p['path']).exists())
        self.cli('cleanup','--run-id','test-run',ok=False)


if __name__=='__main__':unittest.main()
