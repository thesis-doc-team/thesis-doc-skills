# literature-review-write｜文献综述编写 Skill

> **基于用户最新上传的 `literature-review-write.zip` 增量升级**，参考 `thesis-midterm-check-write.zip` 的四范本脱敏、模板锁定、格式统计和回归门禁。保留原有资产协议和代码执行方式，不把它改造成任务书、中期检查表或开题报告 Skill。

## 这个 Skill 能做什么

接收当前项目技术文档及（最好）已有的项目 `project-assets/` 数据，根据**真实且可核验的学术论文资料**编写不少于2500字的毕业设计文献综述，在官方原始 DOCX 母版中填写正文/参考文献/指导教师评语**拟稿**，自动做正文上标引用和结构审计，输出可由人工逐页验证的 PNG，最后版本化保存 Word。

严格禁止修改官方原件、复制旧范本身份资料、抄用范本文献作为项目证据、冒充教师签名或未经实际截图检查就报告最终排版通过。

## 安装与调用

把本压缩包里的**`literature-review-write/` 目录本身**解压到你的 Claude Code Skills 目录（例如项目 `.claude/skills/literature-review-write/`）或 Codex Skills 搜索目录，读取 `SKILL.md`。不要把 `project-assets/` 放进 Skill 安装目录。

要求本机有 Python 3.10+、`python-docx`、`lxml`；截图预检额外需要 `PyMuPDF`；DOCX→PDF 转换链依次探测 soffice（LibreOffice）→ Word COM → WPS COM，亦可 `--pdf` 直通本机已转换的 PDF。安装依赖：`python -m pip install -r requirements.txt`。

参考指令：

> 请使用 `literature-review-write` Skill，根据我提供的技术文档和当前项目的 `project-assets/`，编写符合官方 Word 模板的文献综述。先核验引文，再填原模板；完成后执行结构审计并逐页打开渲染截图，重点检查题目两行、所有下划线、Word 上标与教师审阅区；发现问题继续修改。保留历史版本，最后给我 DOCX 和执行报告。

## 项目数据保持兼容

一个项目 = 一个资产包（数据+成品+运行区）；使用项目根 `project-assets/{project,facts,references,schedule}.json` 与 `activity.jsonl`，与任务书和中期检查 Skill 共用数据真源，文献综述只读周计划。每轮临时文件放 `.skill-tmp/literature-review-write/<run-id>/`，不触碰其他 Skill 运行区。

## 核心文件

| 路径 | 作用 |
|---|---|
| `SKILL.md` | 执行政策、边界、完整流程 |
| `assets/official-literature-review-template.docx` | 学校空白原件副本（严禁改写） |
| `assets/template-lock.json` | 官方原件 SHA-256、封面段落与表格位置锁 |
| `assets/reference-samples/` | **最初四份**脱敏范本 + 内容边界说明 + manifest |
| `examples/anonymized-style-reference.docx` | 旧版兼容的第一份匿名范本（不作为主入口） |
| `references/format-reverse-engineering.md` | 四份范本求同存异的写作规则和反面规则 |
| `references/sample-style-audit.json` | 从 DOCX 实际统计的段落格式值 |
| `scripts/project_assets.py` | 兼容统一项目资产协议，带隔离运行区清理 |
| `scripts/template_tools.py` | 原版模板锁与原位填写 guard |
| `scripts/compose_review.py` | 核验 REF-ID → 本文编号，并生成严格写作输入 |
| `scripts/fill_review.py` | 在学校既有段落/表格内写 Word，不重新建封面 |
| `scripts/validate_review.py` | Word 原结构、真实上标、字体字号、引文对应与教师固定区审计 |
| `scripts/render_visual.py` | 实际渲染 PNG/PDF + 自动预警（**不是自动视觉验收**） |
| `tests/smoke_test.py` | 正向端到端隔离模拟 |
| `tests/test_regression.py` | 负向故障回归：防伪模板、防覆写、防普通引用和篡改固定区 |
| `templates/execution-report.md` | 本轮执行证据与待用户审核的交付报告 |

## 测试

```bash
python tests/smoke_test.py
python tests/test_regression.py
# 按需：有格式争议时才跑（非固定开销，格式真源是 fill_review/validate_review 校验实现）
python scripts/inspect_reference_styles.py --report /tmp/literature-sample-audit.json
```

测试只会创建虚构内容，绝不可作为真实研究文献。截图工具和人工看图是独立于以上代码测试的**正式成品门禁**。
