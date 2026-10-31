# 图像资产协议 v1.0.0（兼容 shared-project-assets-contract.md）

**单一可信来源**：项目事实只来自 project-technical-doc 正式技术 MD 与同项目 FACT-xxx，网络来源仅支持图片来源/型号和使用权核验，不修改 FACT。

保存目录 `<PROJECT_ROOT>/project-assets/visual-assets/`，并与同项目既有 `project-assets/` 共用写锁 `.asset-write.lock`、审计 `activity.jsonl`，不修改 `schema_version=1` 核心资产协议。不能在插件安装目录存入项目数据。

`index.json` 中 `items[]` 的核心字段：
- `id`: `VIS-` + 内容 SHA256 前12位；`origin`: `project-technical-doc`、`derived-from-technical-doc` 或 `external-web`；`kind`: `technical-diagram`、`technical-figure`、`external-module-image`。
- `visual_category`: 仅能在实际核查后选 `system-framework` / `functional-architecture` / `flowchart` / `module-photo`；`category_hint` 是自动推荐，不等于核验。
- `subject_scope`: `full-diagram` / `needs-visual-review` / `whole-module-reviewed` 等，模块实物图必须是完整主体。
- `technical_module`, `fact_ids`, `evidence_locations`：与正式技术 MD/FACT 绑定，含 MD SHA、行号或章节。
- `source_path`, `image_path`, `content_sha256`, `render_sha256`：按项目根相对路径存储，持久版本/内容核验。
- `source_page_url`, `original_image_url`, `copyright_holder`, `license`, `permission_evidence`, `web_verified_at`, `checked_by`：外部来源与许可完整留痕。
- `visual_evidence`, `review_status`, `rights_status`, `review_reason`：内容、许可与批准状态分开记录。

`requirements.json` 中 `core_modules[]` 记录真实需要完整实物图的核心模块：`name`, `fact_ids`, `technical_md`, `technical_md_sha256`, `reason`, `created_at`。**不要登记电阻电容等普通元件来凑覆盖。**

覆盖要求：独立系统框架、功能架构、至少一张真实关键流程图，以及每个登记核心硬件模块的完整实物照。纯软件项目可报告不适用，不能暗中标 PASS。

许可状态：`owned`（确为用户原创）、`public-domain`（已确认）、`cc-by` / `cc-by-sa`（需遵守协议）、`express-permission`（权利人同意）、`internal-only`（仅允许内部使用，不能标记 approved）、`unverified`（未知，不能批准）。**许可真实 ≠ 技术事实真实**；即使 `approved`，下游公开论文仍须复核授权场景。

每个新资产只作为候选登记；`review --approve` 必须记录图像类别、FACT IDs、真实视觉依据、授权/核验。特别是模块实物照必须记录 `--model-evidence`，并标记 `--full-module-confirmed`，不能用无关局部图片冒充。`verify` 检查 hash、来源和批准字段，不等于机器视觉准确性判断。

所有写入是原子索引更新，审计追加。用户技术 MD、官方模板、旧资产、历史成品不得覆盖。运行目录只有有合法所有权标记时才允许安全清理。

## v1.0 稳定附加约束

- `plan_visuals.py` 只输出只读候选信息，不更新事实源、不联网、不登记批准。
- `draft-from-ascii` 保存源 MD 的具体行号范围、ASCII 节点边证据和 `.mmd`，新的 `system-framework / functional-architecture` 也要经过渲染与内容审核。
- `render` 在已有 Mermaid CLI / Graphviz 不可用时，仅对简单有向无环图使用 Python 标准库 SVG 回退。复杂图拒绝误画，保留可编辑源文件。
- `search_candidates.py` 可选已安装 DDGS、Openverse、Commons；均是候选线索不自动下载图片。
- 外部图像是否准确匹配当前完整模块必须由实际看图的人/Agent 判断。程序对 `--subject-level` 和 `--model-evidence` 做的是审核记录门禁，不是 CV 图像识别。
- 如需纠正图的类别与初始提示，需 `--category-override-reason` 明确记录理由；不能换标签让同一图覆盖多类。
- 兼容原 `schema_version=1` 和 `VIS-` 稳定 ID，原有数据不删除不迁移。
