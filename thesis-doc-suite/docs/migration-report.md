# 迁移报告（Phase A 审计 + 实施记录）

- 日期：2026-10-30
- 范围：`E:\Code\thesis-doc-skills` 下 6 个独立 Skill → `thesis-doc-suite/` 插件
- 原则：**复制迁移**。原始 Skill 目录零修改（`git status` 仅显示新增 `thesis-doc-suite/`，可随时回退比对）。

---

## 1. 迁移原则合规声明

| 约束 | 执行情况 |
|---|---|
| 规则1 不从零重写 | 6 个 Skill 全部以原件为基础复制迁移，仅做增量修改（见 §4） |
| 规则2 不修改原始目录 | 原始 6 个目录未做任何改动；全部修改发生在 `thesis-doc-suite/skills/` 副本中 |
| 规则3 不降低质量 | 19 项测试全绿（含各 Skill 原有回归套件）；修复项只增不减 |
| 规则4 不伪造内容 | 示例/测试数据全部合成并标注（2099 年、example.invalid）；报告区分 PASS/WARN/FAIL/未测试 |
| 规则5 无资产重复源 | 共享元数据单一来源 `core/contracts/skill-catalog.json`；各 Skill 保留"协议兼容副本"并由行为测试锁定等价性 |
| 规则10 不丢能力 | `diff -rq` 逐文件比对原件与副本，差异文件全部在 §4 逐项列明，无删除文件 |

## 2. Phase A 盘点结果

### 2.1 能力清单（迁移后版本）

| Skill | 版本 | 产出 | 官方模板 |
|---|---|---|---|
| `project-technical-doc` | 5.2.0 | 技术文档 MD + 离线展示 HTML | 不需要 |
| `thesis-taskbook-write` | 1.2.2 | 毕业设计任务书 DOCX（原位填写） | 需要（内置只读副本） |
| `opening-report-writer` | 4.1.0 | 开题报告 DOCX（七项内容） | 需要 |
| `literature-review-write` | 3.2.1 | 文献综述 DOCX | 需要 |
| `thesis-guidance-record-write` | 1.2.0 | 指导记录 DOCX（≥8 次） | 需要 |
| `thesis-midterm-check-write` | 1.3.2 | 中期检查记录表 DOCX | 需要 |

### 2.2 共享资产契约存在 4 种变体（原件 md5 比对）

| 变体 | md5（原件） | 覆盖 Skill |
|---|---|---|
| A | `e75f01a3…`（`shared-project-assets-contract.md`） | literature-review-write、opening-report-writer、project-technical-doc |
| B | `73791a72…`（`shared-assets-contract.md`，命名亦不同） | thesis-guidance-record-write |
| C | `2fd8b2d3…` | thesis-midterm-check-write |
| D | `559f4417…` | thesis-taskbook-write |

另有 opening-report-writer 独有的 `integration-contract.md`、`report-json-contract.md`（文档格式契约，随 Skill 保留）。

处置：新建统一协议 `core/contracts/shared-project-assets-contract.md`（schema_version=1）整合四变体的公共规则（FACT-xxx/REF-xxx/PLAN/PROG-xxx、`--replace --reason`、activity.jsonl 审计、项目隔离）；各 Skill 原有契约文档**保留在自己目录内**作为上下文，不产生双源冲突——统一协议只在插件级管理场景引用，Skill 执行仍遵循自身契约（两者规则一致处由行为测试断言）。

### 2.3 `project_assets.py` 实现分析

6 个 Skill 各自携带一份 `scripts/project_assets.py`（stdlib-only，含文件锁、原子写、run-id 校验、符号链接防护）。逐份与规范参考实现（`core/asset-management/project_assets.py`）比对，差异集中在：

1. 属主常量 `WORK_BASE`/`MARKER`（各 Skill 拥有自己的 `.skill-tmp/<skill>/` 与 `.owned-by-<skill>` 标记）；
2. 支持的 `KINDS` 集合（如 literature-review 不含 `progress`）；
3. `progress` 记录的校验规则（仅部分 Skill 实现）；
4. Skill 专属 `compose`（汇总产出内容不同）。

其余共享操作（init/merge/workdir/cleanup/record-use/status）逻辑一致。处置：不合并实现（避免改动各 Skill 执行链），保留"协议兼容副本"模式，用 `tests/test_asset_consistency.py` 对 7 份实现（规范 1 + 副本 6）跑同一套行为契约测试锁定等价（56 用例全过）。

## 3. 迁移实施

1. 逐字节复制 6 个 Skill 目录到 `thesis-doc-suite/skills/`（复制后 md5 校验一致）。
2. SKILL.md frontmatter 增加 `version:`（对应上表版本）与 `disable-model-invocation: true`（业务文书 Skill 仅显式 `/thesis-doc-suite:…` 调用，避免误触发生成文书；管理 Skill `check-project` 保留模型自主调用）。
3. 修复迁移副本中的既有缺陷（§4）。
4. 新增插件级基础设施（manifest、core/、管理 Skill、脚本、测试、文档、网站、示例）。

## 4. 副本与原件的全部差异文件（`diff -rq` 实测）

| 文件 | 差异内容 | 性质 |
|---|---|---|
| 各 `SKILL.md`（6 处） | 仅 frontmatter 新增 2 行（`version`、`disable-model-invocation`） | 插件化必需 |
| `*/scripts/render_visual.py`（5 处）、`project-technical-doc/scripts/diagram_svg.py` | `subprocess.run(text=True)` → 补 `encoding="utf-8", errors="replace"` | 修复：zh-CN Windows GBK 控制台解码中断风险 |
| `thesis-guidance-record-write/tests/test_pipeline.py` | `read_text()/write_text()` 显式 `encoding='utf-8'` | 修复：原测试在 zh-CN Windows 3 处 UnicodeDecodeError（原有缺陷） |
| `thesis-taskbook-write/tests/test_shared_assets.py` | symlink 用例在无权限时 `skipTest` | 修复：原测试在非管理员 Windows 报 OSError（原有缺陷） |
| `thesis-midterm-check-write/tests/test_shared_assets.py` | 补 `sys.path.insert(0, str(ROOT))` | 修复：作为脚本运行时 `import tests.test_pipeline` 失败（原有缺陷） |
| `thesis-taskbook-write/tests/test_reference_samples.py`、`project-technical-doc/tests/test_pipeline.py`、`opening-report-writer/tests/test_anonymized_example.py`、`opening-report-writer/tests/test_project_assets.py`、`project-technical-doc/tests/test_project_assets.py` | 同类 `text=True`/编码加固 | 修复/加固 |

以上"修复"仅作用于副本；原件保留原状作回退依据（含其原有失败用例）。

## 5. 兼容性与行为变化（规则10 申报）

| 变化 | 影响 | 说明 |
|---|---|---|
| 调用前缀变为 `/thesis-doc-suite:<skill>` | 旧的直接 Skill 名调用不再适用 | 插件机制使然；9 条命令以 `skill-catalog.json` 为单一来源 |
| 业务 Skill 增加 `disable-model-invocation: true` | 模型不再自主触发文书生成 | 符合"文书生成须用户显式指令"的安全取向，可按需移除该行恢复 |
| 命令/目录结构新增管理 Skill 与 core/ | 无破坏 | 纯新增 |
| 各 Skill 自带 `project_assets.py` 保留 | 无破坏 | 与原件逐字节一致，行为由契约测试锁定 |

无能力删除、无产出格式变更、无质量门禁放宽。

## 6. 待验收 / 待补充

- LibreOffice 渲染、逐页截图链路、WPS 兼容性未在本机实测（见 `docs/test-report.md`）。
- 真实用户数据（学号/导师/日期等）在示例中一律标注"待补充"，实际生成时由用户填写。
- 其他院校官方模板适配需另行提供模板并生成新的 `template-lock.json`。
