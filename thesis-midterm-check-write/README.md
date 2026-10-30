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
- `assets/official-midterm-template.docx`：本次上传的**学校官方空白模板原样副本**。`assets/template-lock.json`：SHA256 固定版锁。
- `scripts/project_assets.py`：与任务书 v1.1 兼容的项目资产库 init/status/merge/compose/workdir/cleanup/record-use，并支持可选 `progress.json`。
- `scripts/inspect_template.py`：只读检查模板结构及空白位置；`scripts/fill_midterm.py`：只写允许的空白文字；`scripts/validate_midterm.py`：严格结构和字数审计。
- `references/`：范本文体逆向、项目资产协议、参考来源政策、技术状态、官方模板保护及清理与质量门禁。
- `templates/`：草稿字段 JSON Schema、项目引用/进展输入示例、执行汇报结构。
- `tests/`：离线回归测试，仅使用模拟内容，不混入真实项目资产。

## 本工具的真实性限制

程序可以核验字数、表格结构、原固定格式、资产 ID 和文件存在，但**不能仅凭技术文档证明作品在特定中期日期实测成功**，也不会自行验证知网论文真实性。AI 必须先读取相关技术材料并严谨判断，再撰写有内容的文字。指导教师意见始终是拟稿，需要教师自行审核并签字。

## 更新学校官方模板

不要直接覆盖内置原版并继续使用旧脚本。先将新的 DOCX 和新版审计结果交给 Agent 检查，重新建立模板定位/锁定信息并测试；若没有可编辑 DOCX 不能声称“原版保真填充”。

## 验收

`python -m unittest discover -s tests -v` 应离线通过；生成真实文档后运行 `validate_midterm.py` 并逐页渲染检查。不在 WPS 中实际打开，不可称“已在 WPS 验收”。最终是否采用由用户决定。

### 关于页数

学校官方 DOCX 内存在大量空段。为了严格遵守“不改官方结构”，脚本不会删除这些占位段落；正文填入后 Word 可能自然增加一页。对出现的孤页落款，应优先精简重复措辞并复核字数；若模板结构冻结与固定页数无法同时实现，必须如实汇报并交由用户决定，而非偷偷修改学校模板。
