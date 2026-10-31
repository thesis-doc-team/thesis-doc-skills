# 项目级共享资产协议 v1（跨 Skill 的统一契约）

> **此协议独立于任务书体裁**。任务书、开题报告、技术说明书、论文和答辩材料可以遵守同一套资产路径与读取约定，但各自仍负责自己的正文、模板、验证和交付。本 Skill 仅实施任务书工作流，不替其他 Skill 生成文书。

## 1. 唯一持久化根目录

每个**真实项目**一个独立的 `<PROJECT_ROOT>/project-assets/`。它不是某个 Skill 的安装目录，也不是中间生成目录；**同一项目、多个 Skill 共同维护**。不要把不同毕业设计项目的论文和周计划合并。

```text
<ProjectRoot>/
├── project-assets/                  # 共同维护：跨 Skill 的长期资产，不属于中间文件
│   ├── project.json                 # 项目标识、人工提供的学校/人员元信息
│   ├── facts.json                   # 项目技术事实、来源、实施状态
│   ├── references.json              # 共享参考文献库、稳定编号、核验状态
│   ├── schedule.json                # 一份项目级周计划基线及确认状态
│   ├── progress.json                 # 可选：中期检查记录的真实进展
│   └── activity.jsonl               # 增补/变更/被文书使用的审计记录
├── deliverables/                    # 持久化最终产物（示例，可按用户指定位置）
│   ├── taskbook/毕业设计任务书.docx
│   └── proposal/开题报告.docx        # 由后续独立 Skill 负责，本 Skill 不生成
└── .skill-tmp/                      # 本 Skill 的临时产物，最终应清理
    └── thesis-taskbook-write/
        └── <run-id>/                # 仅本次执行创建、带所有权标记的工作空间
```

**绝不能把 `project-assets/` 放在 `.claude/skills/` 或 `.agents/skills/` 内**：Skill 升级会导致资料丢失，而且另一编辑器未必使用同一安装目录。禁止向 Skill 的 `assets/` 内保存项目论文或项目事实。

## 2. 文件语义、稳定 ID 与来源

### `project.json`

固定 `schema_version=1`、`project_id`（唯一、持久，不应在同项目中随意修改）、`name`、`metadata`、时间戳。`metadata` 仅存用户明确确认或当前项目真实材料直接提供的稳定字段。未知导师、学院、日期不得从其他项目范本复制。不要记录密码或密钥。

### `references.json`（共享参考文献）

`items[]` 中每条文献有**项目内稳定**的 `id`，例如 `REF-001`（不是正文 `[1]`）。至少：

```json
{
  "id": "REF-001",
  "citation": "作者. 论文标题[J]. 期刊, 2025, 1(2): 1-9.",
  "source_url": "https://example.org/仅表示字段结构-禁止当作真实文献",
  "source_type": "journal",
  "verified": false,
  "checked_at": null,
  "tags": ["与本项目有关的技术主题"],
  "project_relevance": "本项目哪些任务需要此文献",
  "notes": "示意结构；不得作为真实引用"
}
```

以上是**字段示意**，不是待引用的学术论文；真实写入时应以实际来源重新填写。`verified=true` 只能在确实打开且核对来源记录后设置，同时记录 `checked_at`；链接、作者和出版详情不得靠 AI 记忆捏造。

- 一个项目只维护**一份**参考文献事实库，允许保存超过 10 篇；任务书/开题报告各自通过 ID **选择其中适用的子集**。
- 文献 ID 永久稳定，正文 `[1]`、`[2]` … 按**本份文书实际入选顺序**生成，绝不将 `[1]` 当作长期 ID。
- 新 Skill 优先读取现有已核验、相关的条目；**不需要每次从零检索/重新抄写**。若来源变化、文献元数据有缺漏、研究方向不匹配或学校另有要求，则补充核验；未核验条目不得被伪装成已核验。
- 不修改共享条目的内容来迎合某一份文书的排版；仅在导出到文书时按对应学校格式处理。
- 同一文献跨数据库不可计为两篇；按稳定 ID、规范化标题、DOI（若真实存在）等去重。

### `schedule.json`（共享周计划）

`plan` 记录 `id`、`status`（`draft` 或 `confirmed`）、`total_weeks`、可选 `start_date/end_date` 和 `stages[]`（阶段含稳定 ID、`from_week`、`to_week`、`task`）。

- 基线周次必须连续覆盖 `1..N`，且不重叠；不同文书可调整**措辞详略**，但不能暗中更改基线日期、周次或顺序。
- 初次提议用 `draft`，**仅用户或正式安排明确确认后**标 `confirmed`；AI 不能把“自己编出来的计划”声明成用户已确认。
- 遇到学校新时间安排、开题报告要求细化阶段或真实进度改变：先检查是否只是文书表达差异；如果是**项目级基线变更**，明确变更理由并更新共享计划，告知影响的下游材料。
- 不同 Skill 若认为周计划互相冲突，不能自动以新覆盖旧；保留当前基线，记录冲突并依据用户决定修改。

### `facts.json`（项目事实）

每条保存 `id`、`statement`、`source`（文件及章节、行号或证据地址）、`status`（`implemented` / `declared` / `unverified` / `proposed`）。任务书和开题报告可以引用相同事实，但“现已实现”和“计划设计”是**文体**不同，不能修改事实本身的状态。

### `progress.json`（可选的中期进展扩展，与 midterm-check v1.3 兼容）

`progress.json` 是中期检查等后续文书维护的项目**实际进展**，不等同于任务书 `schedule.json` 的**拟定周计划**。旧项目可没有此文件；若已有则本 Skill 不得删除或覆盖。最小约定：`schema_version=1`、`project_id`、`items[]`；单条 `PROG-xxx` 含 `as_of`、`category`（`completed/in_progress/pending/risk/next_step`）、`status`（`draft/confirmed`）、`description` 与 `source`。源文档或用户未证实的进展不能标为 `confirmed`。

本 Skill 的 `project_assets.py` 支持按相同 ID 读取、显式 `merge --kind progress` 和审计记录，但**任务书的 `compose` 不读取 progress 生成进度表**：编写任务书时按用户确认或拟定的 `schedule.json`，不把中期已完成事实冒充早期计划。其他文书的 `compose` 仍归各自 Skill 所有，禁止交叉调用。

### `activity.jsonl`（维护记录）

记录新增、更正、使用来源文献等事件的时间、调用方、稳定 ID 与原因；不是另一个技术报告，也不应保存全文论文。用户可检查谁修改了什么，避免悄悄覆盖。当前脚本用独占锁 + 文件原子替换写资产，支持从其他 Skill 调用同一脚本或按本协议自行实现。

## 3. 跨 Skill 执行的固定顺序

1. **识别项目根目录与 project_id**；先读已有 `project-assets/`。若目录不存在才初始化；若 project_id 不一致立即停止合并，防止串项目。
2. **先读后写**：查看当前文献、周计划与项目事实；仅补充缺失的、经证据支持的条目。不要重新创作已存在且仍适用的资产。
3. **只通过稳定 ID 关联**。已存在条目如果需要改变，必须给出变更原因并使用显式覆盖动作；不能让后生成的文书覆盖先前共享事实。
4. **完成每份文书的独立生成与质量验收**；不得因为资产库存在内容就跳过本轮文书的相关性检查、引用检查或模板检查。
5. **使用记录**：记录本份文书实际采用的参考文献 ID、成品路径和文件校验值，便于之后回查。
6. **清理中间文件**：临时 JSON、渲染图、模板审计缓存、测试文书、调试日志等仅存于本轮自己的运行目录，完成成功/失败报告后都清理。共享资产、真实输入和最终成品不删。

## 4. 修改资产的严格边界

- **允许新增**：从本轮技术文档抽取证据事实，找到真实参考文献，形成新增共享记录或提出新周计划。
- **更新已有记录**：需要显式变更理由（例如 DOI 更正、时间安排被教师调整、原事实被源码否定）；书面报告受影响的文书。
- **禁止默默覆盖**：其他 Skill 已审定的计划、已验证的文献、用户本次提供的原始资料和官方模板。
- **禁止“为了复用而生造”**：共享目录是事实与可复用计划的存储，不是杜撰论文与虚假论证的许可证。
- **不强制全项目只存在一份最终文档**；交付文书可以按用户指定名称保留版本，区别于每轮无意义的临时文件。

## 5. 命令契约（其他 Skill 也可调用）

下面的路径仅示意 `python scripts/project_assets.py` 位于安装好的 `thesis-taskbook-write` Skill 下；在其他 Skill 调用时传入这个脚本的**实际绝对路径**，或按协议实现兼容客户端：

```bash
# 初始化一次：在项目根目录建 project-assets/（已存在时不覆盖）
python scripts/project_assets.py init --root /项目根目录 \
  --project-id PROJECT-001 --name "当前毕业设计项目"

# 了解有哪些可复用资产
python scripts/project_assets.py status --root /项目根目录

# 新增参考文献或技术事实（使用真实项目数据；每条须有稳定 ID）
python scripts/project_assets.py merge --root /项目根目录 \
  --kind references --input /本次运行目录/verified-references.json

# 初次写入共同进度计划（更新时增加 --replace --reason "真实变更理由"）
python scripts/project_assets.py merge --root /项目根目录 \
  --kind schedule --input /本次运行目录/schedule-proposal.json

# 从已有资产组合本份任务书的 JSON，草稿只写任务书独有内容和所选文献 ID
python scripts/project_assets.py compose --root /项目根目录 \
  --draft /本次运行目录/taskbook-draft.json \
  --out /本次运行目录/taskbook-input.json

# 完成用户可见成品后登记实际使用关系
python scripts/project_assets.py record-use --root /项目根目录 \
  --file /项目根目录/deliverables/taskbook/毕业设计任务书.docx \
  --doc-type taskbook --ref-ids REF-001,REF-002
```

`merge` 的输入为 `{ "project_id":"PROJECT-001", "items":[...] }`；周计划为 `{ "project_id":"PROJECT-001", "plan":{...} }`。`project.json` 的 `metadata` 可通过 `--kind project` 更新。所有项目 ID 必须一致。脚本**只校验字段和冲突，不会连接知网自动验证文献**，`verified` 的可信度仍依赖实际检索证据。

其他 Skill 的接口原则：**读取同一个 `project-assets/`、按相同 ID 读写、各自选择和排版、各自做真实性门禁、都不删除共享资产**。
