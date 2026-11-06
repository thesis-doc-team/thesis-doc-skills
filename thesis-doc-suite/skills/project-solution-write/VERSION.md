# VERSION

- Skill 名称：`project-solution-write`
- 当前版本：`v1.3.1`
- 生成日期：`2026-11-06`
- 输出：独立的《项目介绍与功能说明》Markdown 及其单文件 HTML、 《工程实施方案》UTF-8 Markdown（或用户明确仅要其中部分）
- 结构参考：用户提供的 `thesis-midterm-check-write-v1.3` 的组织格式，不复用学校 Word 规范或毕业文书业务内容。

## v1.3.1

- 新增与六件套一致的“分批写入与一次终检”机制：介绍/实施 MD 各建议至少 4 批，逐批写入 `$WORKDIR/batches/...` 后由 `scripts/compose_markdown.py` 一次组装；禁止一次性整篇生成；组装后一次终检，终检问题只修受影响批次。
- 新增 `references/batch-writing.md`、`scripts/compose_markdown.py`、`tests/test_compose_markdown.py`；SKILL §8、quality-gates G6、README、执行汇报模板同步；汇报需注明批次数与一次终检结论。
- 组装器检查单一 H1、二级章节、批次数量与常见章节缺失提示；不改写内容、不补写事实。
- 回归：新增 8 项分批组装测试，原 52 项保持通过，合计 **60 项全绿**；双树同步、manifest 重生成（48 文件）。

## v1.3.0

- 新增项目介绍 HTML 可视化能力：以《项目介绍与功能说明.md》为唯一内容源，生成单文件、离线可打开、响应式的介绍页；新增 `templates/project-introduction.html`、`scripts/generate_intro_html.py`、`scripts/validate_intro_html.py`、`tests/test_html_generation.py`。
- 逆向提炼用户提供的 HTML 视觉：固定配色/卡片/暗色场景面板/1000-750-500 断点；功能/流程/场景数量动态适配；示例仓储业务数据不进入通用模板。
- 新增 `references/html-visualization-rules.md`、`html-content-mapping.md`、`html-quality-check.md`；SKILL 增加 4.5 节与三份成品一致性门禁；quality-gates 增加 G7。
- 介绍 HTML 只读介绍 MD，不读实施方案；禁止 GPIO/引脚/接线/协议帧/代码/密钥/部署命令/收费与后续建议；场景示意固定标注“未实测”。
- 回归：新增 15 项 HTML 测试（三类项目、3/6/10 功能、缺失章节、长文本、XSS、离线性、校验器拒绝违规），与原 36 项及题目—项目资产一致性检查 1 项合计 **52 项全绿**；双树同步、manifest 重生成。
- 说明：这是文档可视化能力，不开发用户项目的前端系统。

## v1.2.2

- 新增写正文前的**设计冻结**检查点：`references/design-freeze-and-consistency.md` + `templates/design-freeze.md`，冻结术语/默认值、页面/交互映射、数据结构与配置布局、协议字段与空值语义、状态枚举与优先级、资源/接口、失败分支、测试追溯；冻结表是两份草稿的唯一跨文档来源，冻结后改动须先登记、再一次性同步所有受影响章节并复检。
- SKILL §7/§8 与 `references/quality-gates.md` G2/G6 增加对应门禁；新增回归测试，防止冻结防线被移除。
- 背景：一次静态 PASS 的方案在人工复核中因页面数、字段宽度、状态优先级、Flash 链接区、DMA 完成、按键死区等跨章节不一致产生连锁返工；本补丁只加写前冻结与复核顺序，不改原有选型、边界与资产逻辑。

## v1.2.1

- 新增首次启动**项目题目+功能清单的强制主动询问门禁**，可仅说“使用这个 Skill”；仅缺一项则只问缺项，已确认信息不重问。
- 即使用户要求“直接生成”，也不得凭空编造项目题目或核心功能；设计侧重未指定时才允许默认均衡。
- 新增 `templates/initial-intake-message.md` 聊天话术、`scripts/check_input.py` 结构化初检；补充标准执行流程、G0 质量门禁与回归测试。
- 原有 V1.2.0 的成本/性能/功能/均衡选型探索、严格双文档内容边界、资产管理、质量检查逻辑保持不变。
- 集成侧（thesis-doc-suite）：与六件套共享资产契约对齐——canonical init（project.json + 空 facts/references/schedule + init 审计事件）、`workdir`/`cleanup`（`.owned-by-project-solution-write` 标记运行区）、`record-use`（activity.jsonl 登记）、`write-asset`（requirements/decisions 持 `.asset-write.lock` 原子写）；禁章清单并入“变相章节”族；与 `project-technical-doc` 的分工写入 SKILL。

## v1.2.0

- **以用户已升级的 v1.1.0 全目录为母版**，保留全部双文档边界与原有参考模块；不是重新生成旧版。
- 强化“用户偏好→真实技术路线差异→决定取舍→实施参数→验收指标”的决策追踪；允许同解但必须解释，不捏造不同方案。
- 新增 `references/priority-driven-exploration.md` 和 `templates/priority-choice.md`，明确一次选择、候选探索、硬门槛、反事实比较、跨领域示例。
- 内部候选矩阵增补决策影响、舍弃代价及 REQ/DEC 到验收的追踪；输入 JSON 可选 `secondary_priority` 和 `priority_reason`。
- 文档 QA 增加空泛候选、缺少取舍代价和缺少落地影响的风险警告；次优先级冲突为错误，新增回归测试。
- 继续严格只输出两份 Markdown 项目文档；不做开发、商业交付说明或建议章节。

## v1.1.0

- 新增设计目标四选项：成本优先、性能优先、功能优先、均衡方案；已有选择不重复问，用户明确要求直接执行时均衡拟定。
- 新增先过滤硬约束、再探索 2～3 条候选路线、按目标权衡、确定最终实施基线的流程。
- 明确成本包含一次性与持续/维护费用，性能需有可观测指标，功能优先不得擅自加功能。
- 新增 `references/optimization-and-tradeoff.md`、`templates/optimization-matrix.md`，扩展输入 schema 和项目决策资产约定。
- 在原双文档边界内呈现选型结果；不产生第三份正式文件，不混入“收费”“交付说明”“改进建议”。
- 扩展静态 QA 对明确优化选择的检查，以及相应回归用例。

## v1.0.0

- 建立项目方案专用双文档生成、需求澄清/自主推理、技术资料事实分层、独立项目资产、格式边界与校验脚本。
