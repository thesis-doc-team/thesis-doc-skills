#!/usr/bin/env python3
"""Offline smoke tests; run `python tests/test_pipeline.py`."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLISH=ROOT/'scripts'/'publish.py'
MD='''# 测试系统 — 技术文档

> 仅为工具验证使用，没有任何真实产品结论。

## 目录
1. [项目概述](#1-项目概述)
2. [功能说明](#2-功能说明)
3. [关键流程](#3-关键流程)

## 1. 项目概述
### 1.1 测试范围
本项目只用于文档转换能力的测试，带有一般技术描述与参考文本。

| 名称 | 数值 | 说明 |
|---|---|---|
| 参数 A | 7 | 示例值 |

## 2. 功能说明
### 2.1 输入输出
测试输入从接口 A 进入处理模块，再将状态返回页面。

- 输入：模拟数据包
- 输出：状态与回显

```json
{"module":"example","value":7}
```

## 3. 关键流程
### 3.1 处理链

```mermaid
flowchart TD
  A[接收] --> B{校验通过?}
  B -- 是 --> C[输出结果]
  B -- 否 --> D[输出无效标志]
```
'''


def run():
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp)
        md=folder/'测试系统-技术文档.md'
        md.write_text(MD,'utf-8')
        sidecar=folder/'physical-modules.json'
        sidecar.write_text(json.dumps({'schema_version':1,'generated_by':'project-technical-doc','modules':[]},ensure_ascii=False),'utf-8')
        output=subprocess.run([sys.executable,str(PUBLISH),str(md)],text=True,encoding="utf-8",errors="replace",capture_output=True)
        assert output.returncode==0,(output.stdout,output.stderr)
        page=folder/'测试系统_用户展示.html'
        assert page.is_file()
        report=json.loads(page.with_suffix('.report.json').read_text('utf-8'))
        assert report['status'] in ('PASS','WARN'),report
        assert report['html_validation']['chapters']==3
        assert report['html_validation']['source_atoms_missing']==0
        assert report['html_validation']['svg_diagrams']+report['html_validation']['fallback_diagrams']==1
        content=page.read_text('utf-8')
        assert '测试系统' in content and '示例值' in content
        assert '<script>' in content and 'id="sidebar"' in content
        assert '已知问题与改进建议' not in content
        # 固定伴随产物：缺少 physical-modules.json 必须拒绝发布
        sidecar.unlink()
        missing=subprocess.run([sys.executable,str(PUBLISH),str(md)],text=True,encoding="utf-8",errors="replace",capture_output=True)
        assert missing.returncode!=0,(missing.stdout,missing.stderr)
        assert 'physical-modules.json' in (missing.stdout+missing.stderr)
        sidecar.write_text(json.dumps({'schema_version':1,'generated_by':'project-technical-doc','modules':[]},ensure_ascii=False),'utf-8')
        # Fail closed: forbidden chapters in the MD stop second-stage creation.
        forbidden=folder/'不合法文档.md'
        forbidden.write_text(MD+'\n## 4. 已知问题与改进建议\n内容不应进入正文。\n','utf-8')
        bad=subprocess.run([sys.executable,str(PUBLISH),str(forbidden)],text=True,encoding="utf-8",errors="replace",capture_output=True)
        assert bad.returncode!=0,(bad.stdout,bad.stderr)
        assert not (folder/'不合法文档_用户展示.html').exists()
        # A second run must version, not overwrite existing site.
        again=subprocess.run([sys.executable,str(PUBLISH),str(md)],text=True,encoding="utf-8",errors="replace",capture_output=True)
        assert again.returncode==0,(again.stdout,again.stderr)
        assert (folder/'测试系统_用户展示-v2.html').exists()
    print('PASS：原文一致、离线页面、越界拦截、重复生成不覆盖')


if __name__=='__main__':run()
