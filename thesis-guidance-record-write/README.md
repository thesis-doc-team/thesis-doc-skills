# thesis-guidance-record-write

针对毕业论文（设计）**指导记录**的可复用 Skill：复制学校正式空白表原始表格骨架，逆向学习去标识化范本写法；从项目技术文档生成8次以上**待教师审核**的分点指导草稿；共用项目资产（数据+成品+运行区），不增加模板原本没有的栏目。

## 安装与使用

1. 将本文件夹放到 Codex/Claude Code 的 Skills 可发现目录（具体路径按客户端配置）。打开 `SKILL.md` 并交给代理执行。依赖 Python 3.10+、`python-docx`、`lxml`、`PyMuPDF`、LibreOffice（截图校验）；`pip install -r requirements.txt`。
2. 准备用户当前技术资料、真实项目根目录和学校原版Word；AI先阅读资料并复用项目资产，再写 JSON 草稿，最后运行脚本。
3. `scripts/fill_guidance.py` **只支持本包 SHA 锁定的官方模板版本**；用户换模板需要重新审计，不能略过 SHA 锁。
4. 输出示例`deliverables/guidance/<课题简称>-指导记录-v1.docx`。正式归档前由真实教师逐条审阅、按学校要求手写勾选/签名。未经确认的会面日期/地点留空。

## 自测命令

```bash
python -m unittest discover -s tests -v
python scripts/fill_guidance.py --template assets/official-guidance-template.docx --data tests/format-smoke-input.json --out /tmp/guidance-demo.docx
python scripts/validate_guidance.py --template assets/official-guidance-template.docx --file /tmp/guidance-demo.docx --data tests/format-smoke-input.json --report /tmp/guidance-qa.json
python scripts/render_visual.py --file /tmp/guidance-demo.docx --outdir /tmp/guidance-render
```

`tests/format-smoke-input.json`只是胡杨林监测的**演示草稿**，不包含真实学生或导师会面事实。要写其他项目，AI必须从该项目技术文档重新产生 `issue_pairs`，不能重复套演示正文。

## 格式取舍（必须告知用户）

官方原表13行总高度可能大于A4可用打印高度。严格不改官方行高时**跨页是源格式固有问题**。本包默认选择**100%保留固定框架**，不为页数擅自改行高或边距；截图报告将提示跨页。需要以每次记录独立一页的美观版为目标时，应先请用户授权**派生版式**，不能把修改版冒称“官方模板原样”。

该包不包含任何真实用户个人记录，也不负责代替教师签字和学院管理系统上传。
