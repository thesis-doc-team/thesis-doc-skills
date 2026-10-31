# thesis-taskbook-write｜毕业设计任务书编写 + 项目资产共管

这是一个给 Claude Code / Codex 等可操作本地文件的可安装 Skill，当前版本 **V1.2**。它只根据真实技术资料编写学校官方 Word **任务书**；不写开题报告。**V1.1 新增项目级共享资产和执行后清理中间文件**，以便今后其他 Skill 共享同一项目的参考文献、技术事实和周计划。

## 两种目录，各自职责不同

```text
A. Skill 安装目录（固定规则和工具，不存项目事实）
.claude/skills/thesis-taskbook-write/
├── SKILL.md
├── assets/official-taskbook-template.docx      官方只读副本
├── references/                               写作/模板/共享资产/清理规则
├── scripts/                                  填充/验证/项目资产管理
├── templates/                                输入结构说明、汇报模板
└── tests/

B. 每个实际项目的根目录（跨不同 Skill 共享）
<ProjectRoot>/
├── project-assets/
│   ├── project.json                         项目身份、人工确认的个人信息
│   ├── references.json                      同项目统一论文库（稳定 REF-ID）
│   ├── schedule.json                        同项目统一周计划（draft/confirmed）
│   ├── progress.json                        可选：中期检查等文书的真实进展
│   ├── facts.json                           同项目有来源的技术事实
│   └── activity.jsonl                       可追溯变更、文书使用关系
├── deliverables/taskbook/                   任务书最终 Word 与必要最终报告
└── .skill-tmp/thesis-taskbook-write/<run-id>/    临时内容，执行结束清理
```

**共享资产不放在 Skill 文件夹，也不会因 Skill 升级覆盖。** 一个项目对应一套 `project-assets/`，不得混用不同项目的文献和周计划。

## 重要原则

1. **官方 DOCX 是不可改变的框架**。原位置填充，不重建 9×4 表格，不更改页面、合并、固定文字、附注、签名与正文规定格式；正文自然分页，不为控页缩减关键内容。
2. **先读资产再生成**。已有 `references.json` 中真实核验且相关的论文直接复用；新检索到的有来源论文增入同一库。`REF-ID` 是跨文书稳定 ID，文中 `[1]` 是每份文件自己的编号。
3. **共用周计划**。先读取 `schedule.json` 基线；新计划初始 `draft`，用户/官方确认后才能 `confirmed`。发生实际变更明确说明原因，不暗中覆盖。
4. **任务书、开题报告各自独立**。其他 Skill 可以用同一项目资产目录，但仍由自身负责正文和官方模板；当前 Skill **只出任务书**。
5. **中间文件执行完删除**。仅删除本轮带所有权标记的 `.skill-tmp/thesis-taskbook-write/<run-id>`，即使失败也按安全规则清理。原始技术资料、官方模板、共享资产、最终 Word 和必要汇报永久保留。
6. **真实性**。论文至少 10 条，实际来源优先知网/万方/维普/出版方；CSDN 可作明确标注的技术补充，不能假冒论文。未经真实检索不能设 `verified=true`；不能把兼容渲染误报为 WPS 实测。

## 安装

将 `thesis-taskbook-write/` 文件夹复制到：

- Claude Code：`<项目根目录>/.claude/skills/thesis-taskbook-write/`
- Codex：`<项目根目录>/.agents/skills/thesis-taskbook-write/`

安装依赖：

```bash
python -m pip install -r requirements.txt
```

## 推荐执行命令（节选）

具体全流程见 `SKILL.md` 第 4 节，接口与输入示例分别见 `references/shared-project-assets-contract.md` 与 `templates/shared-asset-input-examples.md`。

```bash
# 只第一次初始化；存在则不覆盖
python scripts/project_assets.py init --root "$PROJECT_ROOT" --project-id "$PROJECT_ID" --name "$PROJECT_NAME"

# 优先查看有哪些论文、周计划、项目事实可以直接复用
python scripts/project_assets.py status --root "$PROJECT_ROOT"

# 建立一个本轮临时目录，保存命令打印的路径和 run-id
python scripts/project_assets.py workdir --root "$PROJECT_ROOT"

# 检索、核验并新增项目资产后，组装本次任务书特有内容
python scripts/project_assets.py compose --root "$PROJECT_ROOT" \
  --draft "$WORKDIR/taskbook-draft.json" --out "$WORKDIR/taskbook-input.json"

# 执行 Word 原位填充与结构审计，最终 DOCX 不存临时目录
python scripts/fill_taskbook.py --template assets/official-taskbook-template.docx \
  --data "$WORKDIR/taskbook-input.json" --out "$FINAL_DOCX"
python scripts/validate_taskbook.py --template assets/official-taskbook-template.docx \
  --file "$FINAL_DOCX" --data "$WORKDIR/taskbook-input.json" \
  --report "$WORKDIR/structure-report.json"

# 生成执行汇报后，将真正选中的 REF-ID 登记到共用日志，再安全清理中间文件
python scripts/project_assets.py cleanup --root "$PROJECT_ROOT" --run-id "$RUN_ID"
```

清理只接受本次运行目录，不能清空项目目录或他人资料。如用户明确要求保留诊断产物，应另行归档为交付文件。

## 参考材料

- `references/shared-project-assets-contract.md`：所有 Skill 都可采用的项目共管协议
- `references/intermediate-cleanup-policy.md`：成功/失败清理约定及安全边界
- `references/citation-policy.md`：论文与技术资料真实检索、核验、复用原则
- `references/template-boundary-and-layout.md`：官方模板不可变结构和 WPS 对齐
- `references/integration-with-project-technical-doc.md`：如何与技术文档 Skill 协作
- `references/quality-gates.md`：最终审查清单
- `templates/execution-report.md`：执行后的如实汇报
- `templates/shared-asset-input-examples.md`：供 Agent 使用的**纯示意** JSON，绝非可提交论文
- `templates/cross-skill-integration-snippet.md`：后续开题报告等其他 Skill 可复制的共同维护规则片段

官方模板副本 SHA-256：`49e0983db300ca1729d7d298b3f849dfce3d8d189c4b3cc4c8c2ce87b5085590`。最终验收仍由用户决定。

## V1.2 — 匿名范本与模板锁

本版本相对于 V1.1 **新增四份去标识化 DOCX** 到 `assets/reference-samples/`。建议先读 `assets/reference-samples/README.md`，然后选择风格最近的 1–2 份；如果环境无法直接解析 Word，可读 `references/anonymized-sample-text.md` 和 `references/sample-style-audit.json`。**范本只有表达参考意义，没有当前项目事实和可引用论文。**

新模板写入前会通过 `assets/template-lock.json` 验证官方空白模板的 SHA-256；若用户更换官方空白模板，不得强灌，须重新分析映射并更新锁。对历史 `-vN.docx` 不执行覆盖。生成后调用 `scripts/render_visual.py` 截取全部页面逐张检查，临时 PDF/PNG 仍放在本轮 `.skill-tmp/`，交付后清理；**不再硬性限制生成页数**。

```bash
python scripts/inspect_reference_styles.py assets/reference-samples/sample-*.docx --report /tmp/reference-style-audit.json
python scripts/render_visual.py --file "$FINAL_DOCX" --outdir "$WORKDIR/render"
# 全部 page-*.png 必须实际逐页审阅；质量结论记录在执行汇报，截图不作为长期项目资产
```

**页面检查提醒**：官方空白原件中末条附注可能独立出现于第三页；应与官方原件同引擎渲染结果比对，不为了追求特定页数更改原模板或压缩核心正文。
