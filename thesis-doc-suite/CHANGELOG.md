# Changelog

本文件记录 Thesis Doc Suite（`thesis-doc-suite`）插件的版本变化。插件语义化版本与各 Skill 自身版本独立（见 `core/contracts/skill-catalog.json`）。

## 未发布（0.1.0 之后的指令修订）

- **project-technical-doc：SVG 渲染内容断言 + 图区全局显示（防"渲染损坏却全绿"事故复发，变异验证过防）**：真实交付曾出现 5 张 Mermaid 图黑块/文字消失/纵向图压扁而自动检查全绿（根因① `prefix_svg_ids` 只改 `url(#…)` 不改 `<style>` 选择器 → 前缀化后样式全部失配回默认黑；根因② 净化误删承载 htmlLabels 的 `<foreignObject>` → 节点文字全灭；根因③ `.vector-diagram svg{max-height:685px}` 压扁纵向图 + `overflow:auto` 藏进内层滚动条）。本次为三类根因加**互相独立的防御层**：`validate_html.py` 新增逐图渲染内容断言（`<style>`/`url(#…)` 引用闭合命中本图 id、Mermaid 源标签 100% 存活于 SVG 文本、估算最小字号 <9px 报 WARN、foreignObject 残留 WARN，**断言失败=FAIL 不得降级**）+ 模板 CSS lint（未作用域 `svg/path/rect/foreignObject/div/span/p` 元素选择器禁入；图区禁 `max-height`/`overflow`/`min-width`，流程图必须全局显示无滚动条），默认落盘 `<html>.audit.json` 证据（record-use 登记凭证，无证据不得登记）；`render_html.py` 的 `prefix_svg_ids` 补 `<style>` 文本同步（词边界安全）；`layout.html` 移除图区滚动/压缩规则；`diagram_svg.py` 引擎预检诚实化（`mmdc_version`、系统浏览器探测、`PUPPETEER_EXECUTABLE_PATH` 自动默认，杜绝"装了引擎却零 SVG"假绿）；`screenshot_audit.py` 新增 `renderprobe`（高度比/容器滚动条/黑块填充/标签对比，`diagram_probe.js`）、`pixelprobe`（像素色彩多样性，黑块图≈单色）、`coverage`（1440/768/390 × 首页/含图章节/交互态 9 格覆盖矩阵，缺格/字节重复即不通过）；`publish.py` 报告逐图证据化（`mmdc_version`/`text_count`/`label_hit_rate`/`style_closure`/`estimated_min_font_px`/`pixel_probe`）。新增 `tests/test_svg_pipeline.py`（19 项：CSS lint、前缀闭合、三类破坏样本必 FAIL、mmdc 完整管线金丝雀 A/B、渲染/像素探针、覆盖矩阵、publish 证据 e2e）；**变异验证**：逐一临时还原三类根因缺陷，分别被 4/2/5 项测试当场拦下、还原后基线全绿。run_all 扩为 24 项。原目录同步。
- **technical-visual-assets 升级 v1.1.0（上游发布包整合，Windows/中文环境修复版）**：按上游 v1.1.0 发布包完整替换 Skill 文件（根目录原 Skill 与插件副本同步、树内一致）——新增 `plan_visuals.py`（只推荐有实据的 Markdown 插图占位）、`draft-from-ascii`（可证实 ASCII 关系生成可编辑 Mermaid，歧义自动拒绝）、`svg_fallback.py`（无引擎时标准库画简易流程图，拒绝 subgraph/sequenceDiagram 等并给真实理由）、`preview` 渲染自检（合法 XML/根元素/真实宽高尺寸，杜绝 `width="100%"` 撑满导致截图大片空白）；render 自动探测系统 Chrome/Edge、`diagram_svg.py` 缺失时经 `TVA_DIAGRAM_SVG` 或已知目录定位；`scope-module` 模块层级 3→2（`D1` 占位描述拒绝）；示例图重命名规避 Windows MAX_PATH（`positive-02-complete-breakout-boards.png`，内容不变）。**集成侧修复**（沿 v0.3.0 同类修复先例）：上游血统 5 处 `subprocess.run(text=True)` 缺 `encoding`，zh-CN GBK 解码 UTF-8 输出崩溃（实测 5 项测试报错）→ 补 `encoding='utf-8', errors='replace'`；`test_v1_new_capabilities.py` 的 `register_skill.py` 查找由 `parents[4]` 改为向上探测（原写法在原目录镜像布局解析到盘根报不存在）。`tools/register_skill.py` + `catalog-entry.json` 入库仓库根（幂等注册，只改 skill-catalog.json），目录注册 0.3.0→1.1.0（category support→shared），docs/skill-catalog.md 与站点卡片版本同步。上游自测 17 项本机双环境（默认 / PYTHONIOENCODING=utf-8）实测全绿。**提示**：上游 INTEGRATION.md 声明五张示例图的公开二次发布许可未核验，如需公开撤图可删 `assets/image-selection-examples/*.png`、保留 `references/image-selection-examples.md` 文字判别规范（当前按用户指示随库保留）。
- **project-technical-doc：MD 图示强制 + HTML/截图验证阶段防误判加固（真实交付复盘逆向）**：① **MD 图示硬门禁（强制）**——技术 MD 必须自带 Mermaid 图（全文 ≥1 幅、「系统总体架构」「关键流程」章各 ≥1 幅），`check_markdown.py` 缺图直接 ERROR 阻断 HTML 阶段，保证派生 HTML 一定有图可转 SVG（HTML 0 图 = FAIL）；② 图形引擎预检前置——新增 `diagram_svg.py engine` 子命令并在 `publish.py` 发布前预检，缺 Mermaid CLI/Graphviz 时**立即**告知用户 + 安装命令 + "装好后重跑生成新版本补图"，不再等交付才发现图未转（报告新增 `svg_engines` 字段）；③ 截图伪象防护硬规则——量测先于定性（FAIL 判定前必须有 scrollWidth vs 视口宽量测数据，512px 最小布局视口的截图裁切伪象不得判成溢出 FAIL）、截图字节级查重（相同哈希=拍摄失败重拍）、窄视口/章节截图用 iframe（`--screenshot` 锚点无效、长图有高度上限）、探针脚本四条写法红线（不等事件/不用转义 heredoc/只测一次/抓 Console）；④ 新增 `scripts/screenshot_audit.py`（dupcheck/probe/harness 三命令，仅标准库）+ `scripts/viewport_probe.js` + `references/browser-verification-notes.md` 实施细则，`quality-gates.md` 清单与 `core/quality-check/shared-writing-rules.md` 截图验证红线同步。新增回归 `tests/test_screenshot_audit.py`（13 项，含 MD 图示门禁用例与真实浏览器端到端量测），run_all 扩为 22 项。原目录同步（并带回迁移期 GBK 编码修复）。
- **新增支持 Skill：technical-visual-assets v0.3.0（公共图片资料层）**：新引入并完成插件化整合——四类真实可追溯视觉资产（系统框架图/功能架构图/关键流程图/核心模块实物图，`VIS-` + 内容 SHA-256[:12] 稳定 ID），入库 `project-assets/visual-assets/` 子层；拒绝裸芯片/局部元件/芯片内部框图冒充模块实物图，外部检索 ≠ 自动下载（需用户许可 + `--allow-image-download`），不自动安装任何 pip/npm 包。整合内容：`skill-catalog.json` 注册（10 个 Skill）、help/README/docs/skill-catalog.md/site 同步、`shared-project-assets-contract.md` 增补 visual-assets/ 子层契约、`skill-boundaries.md` 增补职责边界行、`tests/run_all.py` 扩为 21 项。**只做素材与登记，不在文书中插图。**
- **修复（technical-visual-assets 自带缺陷）**：① 3 处 `subprocess.run(text=True)` 缺 `encoding`，zh-CN GBK 控制台解码 UTF-8 输出抛 `UnicodeDecodeError` → 补 `encoding='utf-8', errors='replace'`；② `visual_assets.py` 落盘 `.mmd` 源码未固定换行符，Windows 下 `\n`→CRLF 使落盘字节哈希与源码哈希不一致，`verify` 误报"Mermaid 源码哈希变化" → `write_text(..., newline='\n')`。两处均为只读使用层面的缺陷修复，不改协议行为。
- **分批写入与一次终检（硬性规则）**：根据实际使用反馈（一次写太多容易出问题）修订全部 6 个业务 Skill——禁止一次性整篇生成长内容，必须分节/分批起草并落盘（技术文档逐章、开题七项逐项、综述逐节、指导记录逐次、中期/任务书逐栏），全部落盘后做**一次且仅一次**端到端终检，终检只做定点修订。同源规则已写入 `core/quality-check/shared-writing-rules.md` 第 7 节。Skill 能力版本不变。

## 0.1.0 — 2026-10-30

首次插件化发布：把 6 个独立的毕业设计文书 Skill 整合为一个可安装的 Claude Code 插件「Thesis Doc Suite Taru」，并建立统一的项目资产与质量基础设施。

### 迁移（原有能力保留）

| Skill | 命令 | Skill 版本 | 迁移状态 |
|---|---|---|---|
| `project-technical-doc` | `/thesis-doc-suite:project-technical-doc` | 5.2.0 | 完整迁移 |
| `thesis-taskbook-write` | `/thesis-doc-suite:thesis-taskbook-write` | 1.2.2 | 完整迁移 |
| `opening-report-writer` | `/thesis-doc-suite:opening-report-writer` | 4.1.0 | 完整迁移 |
| `literature-review-write` | `/thesis-doc-suite:literature-review-write` | 3.2.1 | 完整迁移 |
| `thesis-guidance-record-write` | `/thesis-doc-suite:thesis-guidance-record-write` | 1.2.0 | 完整迁移 |
| `thesis-midterm-check-write` | `/thesis-doc-suite:thesis-midterm-check-write` | 1.3.2 | 完整迁移 |

迁移方式为**复制迁移**：原始 Skill 目录未做任何修改（git 状态可证），迁移副本位于 `skills/`，原工程保留作回退依据。详见 `docs/migration-report.md`。

### 新增

- **统一共享资产协议**：`core/contracts/shared-project-assets-contract.md`（schema_version=1），统一 4 种原契约变体；`core/asset-management/project_assets.py` 规范参考实现。
- **公共基础设施**：`core/reference-management/`（文献真实性与 REF-xxx 规范）、`core/quality-check/`（教师意见五要素链、实质性分页门禁、截图验证分析三步）、`core/template-protection/template_guard.py`（模板哈希锁定校验）。
- **3 个管理 Skill**：`init-project`（初始化项目资产包）、`check-project`（PASS/WARN/BLOCK 前置检查）、`help`（使用导航）。
- **插件级脚本**：`scripts/check_env.py`（环境/模板/资产检查）、`scripts/verify_plugin.py`（插件结构与一致性自检）、`scripts/package_plugin.py`（ZIP 打包）。
- **测试体系**：`tests/run_all.py` 汇总 19 项（4 项插件级 + 15 项 Skill 回归），含跨 Skill 资产共享/隔离行为测试与 README/网站/目录一致性测试。
- **文档与网站**：`README.md`、`docs/`（快速开始、使用手册、架构、资产管理、Skill 目录、环境依赖、问题排查）、迁移报告与测试报告、`examples/demo-project/`（合成示例）、`site/`（离线介绍网站）。
- 本地 marketplace 清单（仓库根 `.claude-plugin/marketplace.json`）。

### 修复（仅修复迁移副本，原工程未改动）

- `thesis-guidance-record-write` 测试：`read_text()/write_text()` 缺省编码在 zh-CN Windows 下按 GBK 解码导致 3 处 `UnicodeDecodeError` → 显式 `encoding='utf-8'`。
- `thesis-taskbook-write` 测试：symlink 用例在非管理员 Windows 上 `OSError` → 无法创建符号链接时跳过（`skipTest`）。
- `thesis-midterm-check-write` 测试：`test_shared_assets.py` 以脚本方式运行时 `import tests.test_pipeline` 失败 → 补 `sys.path` 修正。
- 全部 Skill 脚本/测试中的 `subprocess.run(text=True)` 补 `encoding='utf-8', errors='replace'`（16 处），消除 Windows GBK 控制台解码中断风险。

### 已知限制

- LibreOffice 渲染与逐页截图链路未在本机实测（LibreOffice 未安装），相关验收项标注「未测试」，见 `docs/test-report.md`。
- 未实测 WPS 兼容性，文档中不做 WPS 兼容声明。
- 官方模板当前锁定塔里木大学版本；其他院校模板需另行提供并重建 `template-lock.json`。
