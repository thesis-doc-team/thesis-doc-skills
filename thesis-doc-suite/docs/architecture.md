# 架构说明（Architecture）

本文面向想理解或扩展插件的读者。使用者可先看 [README.md](../README.md)；资产协议细节见 [asset-management.md](asset-management.md)。

---

## 1. 总体结构：一个插件 + 七个业务 Skill + 三个支持 Skill + 公共基础设施 + 管理型 Skill

```
thesis-doc-suite/
├── .claude-plugin/
│   └── plugin.json                 # 插件清单（name=thesis-doc-suite，唯一必需字段是 name）
├── skills/                         # 13 个 Skill，各自独立
│   ├── project-technical-doc/      # 业务 Skill：自包含 SKILL.md + scripts/ + references/ + templates/ + assets/
│   ├── thesis-taskbook-write/
│   ├── opening-report-writer/
│   ├── literature-review-write/
│   ├── thesis-guidance-record-write/
│   ├── thesis-midterm-check-write/
│   ├── project-solution-write/
│   ├── technical-visual-assets/    # 支持 Skill：公共图片资料层（VIS 视觉资产，不生成文书）
│   ├── docx-format-audit/          # 支持 Skill：DOCX 格式全景只读解析
│   ├── pptx-format-audit/          # 支持 Skill：PPTX 格式全景只读解析
│   ├── init-project/               # 管理型 Skill：初始化项目资产包
│   ├── check-project/              # 管理型 Skill：前置条件与资产检查
│   └── help/                       # 管理型 Skill：使用导航
├── core/                           # 公共基础设施（跨 Skill 契约与参考实现）
│   ├── asset-management/           # project_assets.py 规范参考实现 + schema 说明
│   ├── contracts/                  # 共享资产协议、Skill 边界与关系、skill-catalog.json 共享元数据
│   ├── reference-management/       # 参考文献核验与引用规范（canonical）
│   ├── template-protection/        # 通用模板哈希/结构保护工具
│   └── quality-check/              # 共享写作与质量规则（教师意见拟稿、分页门禁、截图验证）
├── scripts/                        # 插件级脚本：check_env / verify_plugin / package_plugin
├── docs/                           # 使用文档（本目录）
├── site/                           # 离线 HTML 介绍网站
├── examples/                       # 脱敏合成示例项目
└── tests/                          # 插件级测试（一致性、隔离、模板锁、清理）
```

设计原则：**适度工程**——只用文件系统与轻量 JSON/JSONL 配置，不引入数据库、服务端或框架；稳定性、可理解性、低维护成本优先。

## 2. 业务 Skill 的独立性

- 每个业务 Skill 一个目录、一个 `SKILL.md` 入口，能单独执行；一个 Skill 出问题不影响其他 Skill。
- **不合并**为单个大 SKILL.md；执行规则按需加载（渐进式披露）：常驻上下文的只有 `name` + `description`，正文触发后才加载，`references/` 里的细则按需读取。
- 六个业务 Skill、支持 Skill `technical-visual-assets` 与 `init-project` 均设 `disable-model-invocation: true`——可能写入正式文件/修改资产的能力只响应**用户显式调用**，普通聊天不会意外创建文档。
- 边界规则（`core/contracts/skill-boundaries.md`）：业务 Skill 不得跨越边界生成其他业务文书；`project-technical-doc` 是技术事实（FACT-xxx）的主要提炼者；任务书/开题报告共享事实与计划；文献综述与开题报告共享文献；中期检查/指导记录读取计划与进展；`technical-visual-assets` 只读技术 MD 与 FACT 登记 VIS 视觉资产（素材层，不在文书里插图）。**这些复用关系不构成固定执行顺序**——只有真实必要的输入才是硬性前置，缺非必要资料时降级执行并声明影响。

## 3. 公共资产契约（core/contracts/）

一个项目 = 一个资产包（数据 + 成品 + 运行区），`<PROJECT_ROOT>/` 下：

```
project-assets/    数据层：project.json / facts.json / references.json / schedule.json / progress.json(可选) / activity.jsonl + visual-assets/(可选，VIS 视觉资产子层)
deliverables/      成品层：technical-document/ taskbook/ opening-report/ literature-review/ guidance/ midterm/（-vN 永不覆盖）
.skill-tmp/        运行层：<skill-name>/<run-id>/（带所有权标记，结束清理）
```

- **schema_version=1**：稳定 `project_id`；稳定 ID 体系 `FACT-xxx` / `REF-xxx` / `PROG-xxx` / 计划 stage ID；跨文书关联只通过稳定 ID，正文 `[1]` 之类只是各文书内部临时序号。
- **唯一可信数据源**：项目事实、文献、计划各只有 `project-assets/` 一份，禁止 Skill 各自维护副本；先读后写、显式更新（`--replace --reason`）、审计留痕（`activity.jsonl`）。
- 完整字段与冲突规则见 [asset-management.md](asset-management.md)。

## 4. project_assets.py 的"协议兼容副本"机制

`project_assets.py` 是资产协议的命令行实现（仅标准库），提供 `init / status / merge / workdir / cleanup / record-use`，以及各 Skill 专用的 `compose` 装配命令。

```
core/asset-management/project_assets.py     ← 规范参考实现（shared operations，无 compose）
skills/<each>/scripts/project_assets.py     ← 协议兼容副本：同一算法 + 本 Skill 所有权常量 + 本 Skill 专用 compose
```

为什么保留每 Skill 一份副本而不是互相 import：

1. **独立性**：任何 Skill 目录可以单独拷走/单独执行，不依赖跨目录 Python 导入（Windows 路径、空格、中文环境下的脆弱点）。
2. **所有权隔离**：每份副本的 `WORK_BASE`（`.skill-tmp/<skill-name>/`）与所有权标记常量归属本 Skill，`workdir/cleanup` 天然只操作自己的运行区。
3. **compose 不同**：任务书、中期检查、指导记录的输入装配逻辑（字段校验、资产 ID 复用规则）各不相同，属于各 Skill 的职责，不上收。

一致性保障：`tests/test_asset_consistency.py` 对全部副本执行**行为契约测试**（同一协议场景：初始化、拒绝覆盖、拒绝串项目、所有权清理、记录使用），确保各副本与 core 规范实现行为一致。修改协议时先改 core 副本与契约文档，再同步各 Skill 副本并跑测试。

## 5. 模板保护（core/template-protection/）

Word 文书的物理格式真源是**官方空白模板原件**，保护链条：

```
assets/official-*-template.docx   官方模板只读副本（永不当输出覆盖）
assets/template-lock.json         SHA-256 + 结构审计（节、表格、行列、合并、可填区坐标）
scripts/inspect_template.py       只读扫描结构
scripts/fill_*.py                 仅写允许填写区域（限定坐标/占位段）
scripts/validate_*.py             成品与原件逐项比对（节属性、tblPr/tblGrid/trPr/tcPr、固定文字、签名栏）
core/template-protection/template_guard.py   通用哈希/锁校验（check-project、tests 使用）
```

硬规则：不改原件、不重建表格、不动固定栏目/字体/行距/页边距；填充后哈希与结构不符即 FAIL；新学校模板须重新审计重建坐标，禁止"强灌"。

## 6. 质量门禁（core/quality-check/）

跨文书共享的写作与验收规则（各 SKILL.md 内嵌同源条款）：

- **教师意见拟稿统一规范**：五要素逻辑链一段成文；一律"供指导教师审定的拟稿"，不代签、不写日期、不写等级。
- **实质性分页门禁**：页数是内容自然排布的结果，不为凑/压页数增删事实；孤页（末页只剩签名/空白）是硬性 FAIL，只调整可填正文措辞修复。
- **截图验证分析（三步硬门禁）**：截图（逐页渲染）→ 逐张分析（缺一张即未完成）→ 留痕汇报（工具/张数/逐页结论/返工次数）。未逐张分析不得宣称视觉验收通过。
- **事实状态词汇**：`implemented / declared / unverified / proposed`（VERIFIED/DECLARED/DESIGN/EXAMPLE/UNKNOWN 证据分类的入库映射），文书体裁不改变事实状态。

## 7. 管理型 Skill 与插件级脚本

| 组件 | 作用 | 实现 |
|---|---|---|
| `skills/init-project` | 创建资产包骨架 | 引导调用 `core/asset-management/project_assets.py init` |
| `skills/check-project` | PASS/WARN/BLOCK 前置检查 | 引导调用 `scripts/check_env.py` |
| `skills/help` | 命令导航 | 静态导航 + skill-catalog.json |
| `scripts/check_env.py` | 环境（Python/依赖/渲染器/权限）+ 项目数据（资产/模板/文献/计划）检查 | 标准库 |
| `scripts/verify_plugin.py` | 插件清单、目录结构、SKILL.md frontmatter、内部引用路径、模板哈希 | 标准库 |
| `scripts/package_plugin.py` | 打包分发 ZIP（排除缓存/临时/个人数据） | 标准库 |

管理型 Skill 不修改任何业务 Skill 的职责，只做初始化、检查与导航。

## 8. 共享元数据与文档同步（skill-catalog.json）

`core/contracts/skill-catalog.json` 是 13 个 Skill 的**结构化事实源**（名称、命令、版本、输入、输出、前置条件、交付目录）。README、`docs/skill-catalog.md` 与 `site/` 网站的内容都以它为准；`tests/test_doc_consistency.py` 校验文档/网站中的命令与 Skill 名称与目录一致，避免"三套说法不一致"。

## 9. 扩展点

| 扩展 | 做法 | 影响面 |
|---|---|---|
| 新增 Skill（如论文正文、答辩 PPT） | `skills/<new>/` + SKILL.md（name 与目录一致）+ 注册 skill-catalog.json | 不动现有 Skill |
| 新学校官方模板 | 对应 Skill 的 assets/ 换新模板 + 重新审计 template-lock.json + 重建填充坐标 | 单 Skill 内 |
| 新检查规则 | 对应 Skill 的 validate/check 脚本或 core/quality-check 规则文档 | 按需 |
| 资产 schema 演进 | 递增 `schema_version`，旧字段只增不改；提供迁移说明；兼容读取旧版 | core 契约 + 各副本同步 |

详见 [README.md 第 16 节](../README.md#16-如何添加新的-skill)。

## 10. 运行时路径约定

- 插件内部引用一律用**相对路径**（相对各 Skill 目录）或 `${CLAUDE_PLUGIN_ROOT}`，不硬编码用户电脑目录；Windows 路径的空格/中文/反斜杠由调用方加引号处理。
- 项目数据只写 `<PROJECT_ROOT>`（用户指定），**永不写入插件安装目录**。
- 公共规则通过 Skill 正文、core/ 文档与 scripts/ 实际接入（不依赖插件根 CLAUDE.md 自动加载）。
