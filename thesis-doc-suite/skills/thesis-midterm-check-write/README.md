# thesis-midterm-check-write

**毕业论文（设计）中期检查记录表专用 Skill。** 参考 `thesis-taskbook-write v1.1` 的项目资产协议，使用官方附件 6 DOCX 原版，结合用户当次技术资料和可核实的中期进展完成填充。**不是任务书 Skill，也不是开题报告 Skill。**

## 安装

把整个 `thesis-midterm-check-write/` 目录放入你使用的 Claude Code / Codex 支持的 Skills 位置，并将 Skill 名 `thesis-midterm-check-write` 用作调用名称。建议先阅读 `SKILL.md`；运行时必须能访问 Python 和 DOCX 渲染工具。安装依赖：

```bash
python -m pip install -r requirements.txt
```

可在 `SKILL.md` 查看端到端命令。**以真实项目根目录作为 PROJECT_ROOT，不能把整个项目资产放在 Skills 安装位置。** 同一个项目的任务书/技术文档/开题报告/中期表共享 `project-assets`，各自负责 `deliverables` 下的成品（文件带 `-vN` 版本号，重生成不覆盖、不删除历史版本），临时操作都放自己的 `.skill-tmp` 子目录。

## 包含的内容

- `SKILL.md`：完整 AI 执行指令、模板边界、事实/状态逻辑和验收步骤。
- `assets/reference-samples/`：从用户最早给出的4份已填写中期检查表去标识化得到的**Word参考范本**（编号A-D），保留格式与行文层级；只读，不含原学生姓名/班级/原具体课题全称。详细见该目录`README.md`。另外提供 `references/anonymized-sample-text.md` 的可搜索文字镜像，便于 Agent 不依赖 Word 文本提取也能参考语气、结构。
- `references/numbered-issue-remediation.md`：问题整改栏**分点 + 同号一一对应**的硬规则；`issue_pairs` 结构化草稿、自动编号、QA校验。
- `assets/official-midterm-template.docx`：本次上传的**学校官方空白模板原样副本**。`assets/template-lock.json`：SHA256 固定版锁。
- `scripts/project_assets.py`：与任务书 v1.1 兼容的项目资产库 init/status/merge/compose/workdir/cleanup/record-use，并支持可选 `progress.json`。
- `scripts/inspect_template.py`：只读检查模板结构及空白位置；`scripts/fill_midterm.py`：只写允许的空白文字；`scripts/validate_midterm.py`：严格结构、首行缩进、字体/字数审计；`scripts/render_visual.py`：逐页截图及页数、孤页自动预检。
- `references/`：范本文体逆向、项目资产协议、参考来源政策、技术状态、官方模板保护及清理与质量门禁。
- `templates/`：草稿字段 JSON Schema、项目引用/进展输入示例、执行汇报结构。
- `tests/`：离线回归测试，仅使用模拟内容，不混入真实项目资产。

## 本工具的真实性限制

程序可以核验字数、表格结构、原固定格式、资产 ID 和文件存在，但**不能仅凭技术文档证明作品在特定中期日期实测成功**，也不会自行验证知网论文真实性。AI 必须先读取相关技术材料并严谨判断，再撰写有内容的文字。指导教师意见始终是拟稿，需要教师自行审核并签字。

## 更新学校官方模板

不要直接覆盖内置原版并继续使用旧脚本。先将新的 DOCX 和新版审计结果交给 Agent 检查，重新建立模板定位/锁定信息并测试；若没有可编辑 DOCX 不能声称“原版保真填充”。

## 验收

`python -m unittest discover -s tests -v` 应离线通过；生成真实文档后先运行 `validate_midterm.py`，再运行 `render_visual.py --file <文件> --outdir <本次运行目录/render>` 并逐张打开PNG检查。不在 WPS 中实际打开，不可称“已在 WPS 验收”。最终是否采用由用户决定。

### 关于页数

官方 DOCX **原件从不修改**；仅成品已填写的三个正文格会回收尚未使用的写字占位空段，固定栏目/签名/合并关系保持不变。新增加的正文必须按栏目首行缩进：进度12pt、问题整改/教师意见24pt、宋体+Times New Roman、12pt、1.5倍行距。原模板空白基准为3页，若正文过长产生第4页或落款孤页，自动预检失败，必须优先精简重复描述，不能通过缩字号/行距/页边距作弊。

## v1.2 修复重点

- **旧版错误**：只设文本 run，正文 `first_line_indent=None`，生成内容从行首顶格；且旧校验器保护空白 `pPr` 的逻辑反过来禁止恢复正文缩进。
- **当前修复**：完成进度12pt、问题整改及教师意见24pt的分栏缩进（问题/整改小标签0pt），逐段自动核验；可编辑区多余空行回收，降低孤立签章页风险。
- **两个必须通过的关卡**：结构+排版属性自动校验 → 每页截图+孤页自动预检 → Agent逐页看图。源文稿太长时要重新写得简洁，而不是缩字。
- **运行环境**：`pip install -r requirements.txt`，截图转换（DOCX→PDF）依次探测 soffice（LibreOffice）→ Word COM → WPS COM，亦可 `--pdf` 直通已转 PDF。仅能运行Python却不能渲染时，严禁报“视觉验收通过”。

## v1.3 新增使用要求

AI 写作前先读 `assets/reference-samples/README.md` 与范本A/C，再按课题阅读B或D；**参考样本绝不可替代官方空白模板，也不可当作当前课题的技术事实**。`issues_paragraphs` 不再接受连续大段内容，优先通过 `issue_pairs` 给出2～4组问题/整改，生成器会生成“存在问题：（1）（2）… 整改措施：（1）（2）…”并检查问题数量与措施数量一致，编号一条一段。

`python -m unittest discover -s tests -v` 的测试现在包含“样本匿名化与结构、问题整改分点配对、漏号/未分点应失败”。
