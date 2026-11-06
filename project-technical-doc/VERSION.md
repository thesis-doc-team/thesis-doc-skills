# V5.4 — 图表几何/视觉门禁与自动重排（2026-11-06）

- 新增 `scripts/diagram_qc.py`：检查过宽/过高、适配正文宽后最小字号 <9px、节点重叠、文字重叠（CJK 包围盒估算）、连线端点未接节点、marker 失效；宽高比 >10 FAIL、6–10 WARN。
- 新增 `scripts/diagram_svg.py` 自动重排：渲染后 QC；`LR/RL` 过宽自动改 `TD` + 加大间距；`TD` 失败加大间距；仍失败用 Graphviz 重排；最终失败发布 BLOCK。
- 明确**节点数量不是错误**：系统架构 50–80 节点可能正常；禁止为“过密”删节点，信息完整性优先；拆图只作为可读性最后手段。
- `validate_html.py` / `publish.py` 接入 QC：坏图不得 PASS；报告输出 `geometry_qc` 指标。
- 新增 `references/diagram-visual-qc.md` 与 `tests/test_diagram_visual_qc.py`（7 项回归：过宽、偏宽 WARN、断线、文字重叠、节点重叠、60 节点可读、正常图）。
- 全套 61 项 unittest + pipeline 烟雾测试通过。

# V5.3 — 内容分类索引 + 实物模块自动生成（2026-11-06）

- 新增 `scripts/gen_physical_modules.py`：从「模块详解」章自动生成 `physical-modules.json` v1；只收录传感器/执行器/显示/按键/通信模组等实物模块，排除 `uart_comm`/`Warn`/`main`/全小写下划线软件名；抽取 category/source_files/pins/note，并调用契约检查器。
- 新增 `scripts/content_rules.py` 与 `scripts/classify_content.py`：生成 `content-index.json` v1，对每张表、每个 Mermaid 图、每个实物模块分类并归并相似组（数据结构按模块/协议，引脚/参数/流程/架构按类型或章节，模块按物理类别）；输出 category、group_id、group_title、行号、content_sha256，供网站分组/筛选。
- `content-index.json` 覆盖门禁：正文表格数、Mermaid 数、实物模块数与索引必须一致；缺项/多项即 FAIL。
- `publish.py` 发布前强制校验 `physical-modules.json` 与 `content-index.json`；两者缺失或不合法均拒绝进入 HTML 阶段。
- 新增测试 `tests/test_physical_modules_generator.py`、`tests/test_content_index.py`，并更新 `test_pipeline.py` / `test_svg_pipeline.py`；全套 53 项 unittest + pipeline 烟雾测试通过。
- 网站展示仍由用户/下游处理；本 Skill 只提供分类 JSON，不改 HTML 分组 UI。

# V5.2 — 篇幅/页数仅是参考（2026-10-30）

- 补充同源**实质性分页门禁**原则：范本/模板篇幅仅是参考，实际长度由项目材料支撑程度决定；不为凑足或压缩篇幅增删事实、稀释或堆砌文字。

# V5.1 — 截图验证分析环节（2026-10-30）

- E5 与 HTML 门禁统一**截图验证分析**（Screenshot Verification Analysis）：1440/768/390 三宽度截图 → 逐张分析 → 留痕汇报固定三步与红线；浏览器不可用如实记录“未执行截图验证分析”，不能谎称通过。执行汇报模板同步固定字段。

# V5 — 项目级共享资产接入（2026-10-30）

- 新增 1.5 节：**项目资产包（bundle）布局与版本意识**——一个项目一个包（`project-assets/` + `deliverables/` + `.skill-tmp/`），默认交付路径切到 `<PROJECT_ROOT>/deliverables/technical-document/`；重生成产出 `-v2`、`-v3`…不覆盖历史版本，每版单独 record-use 留痕。

- 接入**项目级共享资产协议 v1**（`references/shared-project-assets-contract.md`）：与 thesis-taskbook-write、opening-report-writer 共用 `<PROJECT_ROOT>/project-assets/` 一个数据资产库，本 Skill 定位为 **FACT-xxx 项目事实的主要提炼者**。
- 新增第 1 章“项目级共享资产”：先读后写、稳定 ID、证据分类→status 固定映射（VERIFIED→implemented、DECLARED/EXAMPLE→declared、DESIGN/PLANNED→proposed、UNKNOWN→unverified）、record-use 强制登记、安全清理红线，烙印进 SKILL.md 并贯穿阶段 A/B 与交付环节。
- 新增 `scripts/project_assets.py`（协议兼容副本，所有权常量归属本 Skill：`.skill-tmp/project-technical-doc/<run-id>/`）；过程临时文件改入该运行目录，交付前 cleanup。
- 新增回归测试 `tests/test_project_assets.py`。
- 其余机制（MD+HTML 双产物、事实门禁、禁问题/改进章节、离线单页 HTML）与 V4 一致。

# V4 — MD + HTML 双产物

- 基于 V3：保留项目源码/技术资料理解流程、通用技术文档范本、事实证据门禁与禁止独立问题/改进章节的内容边界。
- 增加：从**同次生成的 MD**构建单文件离线 HTML 展示网站，集成用户提供网页的固定布局、导航、搜索、阅读进度、章节卡、表格、Mermaid SVG、移动端与打印样式。
- 增加：可配置首页功能卡、真实流程、参数速览；缺乏来源时降级为章节速览。
- 增加：`publish.py` 一键检查 MD、生成 SVG/HTML 并对照 MD 验证，自动生成 JSON 报告。
- 原则：不把网页范例中具体项目的技术事实带入 Skill，不独立重写 HTML 技术正文，不新增改进/展望类章节。
