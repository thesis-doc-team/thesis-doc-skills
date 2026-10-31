---
name: technical-visual-assets
version: 1.1.0
disable-model-invocation: true
description: 毕业设计公共视觉素材 Skill；只依据 project-technical-doc 正式 Markdown 及同项目 FACT-xxx，主动整理系统总体框架、功能架构、核心流程与完整硬件模块实物图。优先复用 Mermaid 和原图，从可证实 ASCII 关系生成缺少的图表；模块照片按完整主体/准确型号/来源许可逐张核验，官网、Bing、百度、CSDN 等仅作候选线索；按 VIS 稳定 ID 管理图片。禁止擅自安装软件、下载无关文件、虚构技术事实或修改业务 Word 文档。
---

# technical-visual-assets v1.1.0 — 真实技术视觉资产公共 Skill

## 0. 唯一任务与直接执行原则

**本 Skill 独立完成：从已写好的技术文档认知项目 → 主动补齐有事实依据的技术图 → 检索准确完整的实物图片 → 查验与登记 → 输出四类图片清单及缺口。**

用户已有技术 MD 时，**直接启动全链路**，不要反复要求重写技术文档、逐阶段追问或只给开发建议。已有条件能完成的立即完成；不可完成的节点准确报告缺口，不造假。

- 技术内容唯一上游：`<PROJECT_ROOT>/deliverables/technical-document/` 下 `project-technical-doc` 的**正式最终 Markdown**，以及同项目 `<PROJECT_ROOT>/project-assets/facts.json` 的 `FACT-xxx`。`implemented / declared / proposed / unverified` 状态必须如实保留。
- 用户输入只能选择项目根目录与技术 MD、批准本轮行为，不允许来自网上图片的内容反向补造项目事实；网络网页只证明候选图片/产品信息，**不能证明本项目使用了该型号板卡或实测成功**。
- 本 Skill 不创建六类业务 Word 文书、不修改官方模板、不修改 `project-technical-doc` 的正式 MD/HTML、不替业务 Skill 执行 DOCX 插图。各业务 Skill 后续根据官方模板自行选择是否插图。
- 一个项目一个资产包：共享事实 `project-assets/`；本 Skill 的图片长期资产为 `project-assets/visual-assets/`；中间文件只在 `.skill-tmp/technical-visual-assets/<run-id>/`；保留历史、不覆盖。
- **最小引入绝对规则**：不得执行 `pip install`、`npm install`、`npx` 拉包、浏览器/驱动/模型安装、`git clone` 任意网络仓库，不得自动下载 PDF、文档、脚本、压缩包、软件或无关图片。可调用已存在的 Python 标准库和既有 Claude Code 网络工具；DDGS 仅当本机已安装才尝试。不安装也应能做信息分析和普通图形绘制。

**首轮默认：允许网络检索候选元数据，不授权下载图像文件。** 网络图像只有用户针对本轮明确要求“下载/保存图片”才可受控下载、审核；单纯执行 Skill、希望“找图”不等于允许下载。

## 1. 必要输入与核验门槛

- `<PROJECT_ROOT>` 是用户明确指定的项目根目录，已初始化 `project-assets/project.json`。必须校验 `schema_version = 1`、`project_id` 与 `facts.json` 的项目归属一致。
- `<TECH_MD>` 是上述目录下**已生成并确定版本**的技术 MD；不能读取别的项目、网上通用模板或 AI 编造的伪技术文档替代。
- `facts.json` 中确有与图对应的 `FACT-xxx`。未入库的技术推断不可替代事实。若项目已有 MD 但部分 FACT 缺失：先保留图形候选与待核验关系，需上游补齐 FACT 后才可批准；不得擅自将推断写成已实现。
- 逐项记录文档路径、SHA-256、章节/行号、`FACT ID` 与事实状态。上游修改后相应图片必须重新复核，不得静默沿用旧的 `approved`。

## 2. 必须覆盖的 4 类技术图（不是“找几张图片就算完事”）

| 类型 | 需要展示的真实内容 | 优先成图路径 | 禁止的替代品 |
|---|---|---|---|
| `system-framework` 系统总体框架 | 系统边界、硬件/软件/通信主要子系统、**有证据的**连接和数据边界 | 复用 MD → ASCII 严格关系转换 → 人工核对后绘制 Mermaid | 一张芯片内部资源框图、单独主控板照片 |
| `functional-architecture` 功能架构 | 项目功能树/功能域、子功能与层级关系 | 复用功能树 → ASCII 转换 → 按事实新建功能图 | 把硬件型号清单改名为功能架构 |
| `flowchart` 核心流程 | 真正的启动/采集/决策/通信/异常处理等步骤、分支与顺序 | 复用技术 MD 的 Mermaid；按明确节点和箭头补图 | 空泛“开始→处理→结束”装饰图 |
| `module-photo` 模块整体实物图 | 每一个**真正核心**硬件功能单元的整体外观，准确型号/板型/版本与真实层级匹配 | 官方/分销商/公开资料原图线索 → 逐图目视核验 | 裸传感器 IC、板上电阻、局部零件、芯片内部框图、错型号板卡 |

四类单独审核。**一图一主类别**：不能把系统框图同时记为功能图或流程图凑覆盖率；同一图可在多个文书中引用，但不能刷类别完成度。纯软件项目没有核心硬件的情况标记 `N/A` 并写依据，不能强造模块照片。

### 2.1 用户五张正反例是硬性判例

开始筛选实物照前，**必须阅读** `references/image-selection-examples.md` 并实际查看 `assets/image-selection-examples/` 内五张用户图片：

- **反例 1**：只有 SH4X 裸芯片封装，即使名称相符，也不是“完整 SHT40 功能模块实物照”。
- **反例 2**：孤立小部件（无法证明其为目标完整功能单元），不合格。
- **反例 3**：MCU 内部存储/接口资源框图，不是项目级系统架构、功能架构或板卡实物照。准确芯片的内部原理说明任务可另用，但不计入本四类。
- **正例 4**：完整步进电机（外壳、输出轴、主体清晰可见），主体层级合格；但仍必须核对具体型号。
- **正例 5**：完整的传感器 PCB 小板/模组（整板、接脚、元件关系可见），主体层级合格；图中若出现多个板型必须选对真实版本。

合格强调**有意义的完整功能对象**，而不是“拍到了关键词”。单件电机可以是完整执行器；单颗传感器芯片若只是板上的元件，就不能冒充功能模块。透明底/白底可接受，不能因样式拒绝；模糊、截断、广告、水印、非主体配件不合格。

### 2.2 模块识别层级

先创建审阅表：`技术MD原名 | 系统角色 | 完整目标层级（设备/模组/整板/仅芯片）| FACT ID | 型号证据 | 图片必须展示的范围`。

- 确认完整模块/板卡型号时，优先找同型号完整实物图。
- 若只确认“STM32F103 芯片”而未确认开发板或核心板，**不能挑一块 STM32F103C8T6 小板说项目用了它**。可保留“同类开发板示意/仅供参考”，但不能批准为该项目的 `module-photo`。
- 若只确认 SHT40 裸芯片，不要为了凑图强找某品牌 SHT40 breakout 小板冒充项目模块。此时正确结果是“板型待确认，缺真实整体照片”。
- 代表性照片与实际设备照片必须分开标记：`exact-project-module / reference-only / model-unknown`。**reference-only 永不计入正式模块照覆盖率**。
- 例如 SIM900A 与“4G DTU”同时出现在 MD，应先反馈上游核对二者是否为不同模块；不得根据网络信息直接篡改上游事实。

## 3. 主动执行的完整流程

### A. 先识别，不直接搜图

1. 运行 `scripts/plan_visuals.py` 或等价只读分析：识别技术 MD 章节、Mermaid、ASCII 树/箭头的证据行号和可用 `FACT-xxx`。
2. `visual_assets.py scan-md` 提取已存在 Mermaid 和本地图片到候选库。**图仅是候选，不能凭名字批准。**
3. 依据事实识别**核心**硬件功能单元，按需用 `scope-module` 登记查图目标；元器件清单中的电阻/电容/局部附件不是模块查图清单。
4. 运行 `coverage` 初检，列出 `system-framework / functional-architecture / flowchart / module-photo` 的真实缺口。

### B. 优先补全本地技术图，无需联网或安装

1. 检查已存在 Mermaid 是否能对应真实架构、功能、流程。与 MD/FACT 不一致的不能批准。
2. 如果系统框架/功能架构只存在 ASCII（如 `├──` 功能树或有明确箭头的文本链），**不要直接报告必须重跑上游**：依据行号运行 `draft-from-ascii` 生成候选 Mermaid。先核对根节点、父子关系和方向；无充分证据的连线不得添加。
3. 如果 ASCII 混合、没有明确箭头、关系歧义或无法可靠转换：依据已证实的段落+FACT 写一个可编辑 `.mmd` 草稿，使用 `add-diagram` 登记；只有节点/连线都能对应事实时才可审查通过。没有证据就报告缺口。
4. `render` 优先复用项目已存在的 Mermaid 渲染器及本机 `mmdc/dot`；**如果没有这些程序，内置 `svg_fallback.py` 使用 Python 标准库渲染简单 DAG 流程图**。复杂语法、环路、长标签或布局不可靠则 WARN，绝不伪称渲染成功。
5. 必须保存 `.mmd` 原始源代码与可显示 `.svg`。对每张图进行实际目视检查：是否完整、文字是否被遮挡、箭头是否清楚、节点是否与事实对应。批准前写明 `visual-evidence` 和 FACT。**仅程序生成 SVG 不表示技术审核完成**。
6. 系统框架与功能架构**必须分开判断**，不能给一张图换个标题当两张。

### C. 多渠道联网搜核心模块实物图（不下载）

1. 仅从 MD 和 FACT 生成查询词：真实名称、厂家、准确型号、目标层级（whole module/complete board/full stepper motor）以及“整板/实物/完整模块”。**不把来源网页发现的新型号添加到上游技术事实**。
2. 按证据优先级使用：**原厂产品/型号页面 → 正规元器件分销商页面 → 公开图片平台 → 百度/CSDN/Bing 等搜索线索**。百度/CSDN 的搜索缩略图需要回到原网页核验，不能仅靠标题批准。
3. 如果 Claude Code 已具备 WebSearch/WebFetch/浏览器，使用现有能力；遇网络策略拦截，不得绕过验证码/登录/反爬。`search_candidates.py --provider auto` 先使用当前 Python 已安装的 DDGS；否则/之后尝试**Python 标准库** Openverse、Wikimedia Commons 图片元数据 API。两个公共渠道覆盖精确硬件型号可能有限；结果为 0 就如实报告。
4. 每个候选记录：`title / precise_model / target_object_level / source_page_url / original_image_url / publisher / author / license_evidence / actual_viewed / fact_ids / decision`。若仅搜到搜索摘要，标为线索，**不可声称已经看到图片**。
5. **主体检查**：是否展示完整电机/整板/完整模组，还是裸芯片、局部元件、芯片内部框图？**型号检查**：厂商、完整型号、版本/板型、外观是否一致？**说明价值**：是不是读者能看懂的真实整体部件？不满足任何一个则淘汰作正式 `module-photo`。
6. 图片版权与型号分开审查；网络上有图不等于允许公开转载。无可核对许可则保持 `candidate`，不得标记 `approved`。第三方的 CC 元数据也必须回到原页面核对，并按许可署名。
7. **有效探索，而非机械重试**：一种引擎失效后使用另一种已有渠道；不要把 Bing 无关噪声或百度反爬结果当作成功。对仅有芯片型号但无板型的模块，报告缺少的事实字段，允许保留“reference-only”线索但不计覆盖。

### D. 保存、审核与共享（仅已授权图片）

- 用户明确同意**本轮保存指定图像**后，方可 `workdir` → `download_selected_image.py --allow-image-download` **单张**下载 PNG/JPEG/WEBP 到受控运行区（脚本不装任何依赖），然后 `add-external` 复制到 `project-assets/visual-assets/images/` 候选库；不下载任何其他网络文件。不要自动批量下载。
- `review` 对每张可用图片分别绑定 `FACT-xxx`、实际观察说明、确切主体层级、原始来源和复用权限。外部图必须提供 `--source-checked-at --checked-by --model-evidence --permission-evidence --subject-level --full-module-confirmed`；缺任何可信依据就保持未批准。
- 一个 `VIS-...` 资产一个真实主类别；批准图形时还须确认渲染文件已生成，批准模块图需确认尺寸/整体主体。审计信息写入 `project-assets/activity.jsonl`；引用来源须保存可回查 URL。
- 执行后 `verify` 和 `coverage`：已有正式图片与“仅候选/型号待核/授权待核/不适用”分开；不要强迫所有类别 PASS。**只有真实且经过审核的资源才能供下游文书使用。**
- 结束时只清理本人创建的 `.skill-tmp/technical-visual-assets/<run-id>`，不能清理用户原文件、其它 Skill 运行目录或任何历史 `VIS` 资产。

## 4. CLI 速查（全部使用现有 Python，不安装新包）

从 `thesis-doc-suite/` 插件根执行；Windows 为例，尖括号表示真实路径占位：

```powershell
# 只读发现 MD 中的图示/ASCII/FACT（不会下载或创建资产）
python skills/technical-visual-assets/scripts/plan_visuals.py --root "<PROJECT_ROOT>" --technical-md "<TECH_MD>"

# 将 MD 已有 Mermaid/本地图登记为候选（不会联网）
python skills/technical-visual-assets/scripts/visual_assets.py scan-md --root "<PROJECT_ROOT>" --technical-md "<TECH_MD>"

# 如果原文第62至82行是事实明确的功能树/箭头段，可以直接生候选（先核对真正行号）
python skills/technical-visual-assets/scripts/visual_assets.py draft-from-ascii --root "<PROJECT_ROOT>" --technical-md "<TECH_MD>" --category functional-architecture --start-line 62 --end-line 82 --title "功能架构图" --fact-ids FACT-001 --reason "对应技术MD及FACT真实关系"

# 对没有可安全自动转换 ASCII 的结构，手写经事实核对的 Mermaid 源稿再登记
python skills/technical-visual-assets/scripts/visual_assets.py add-diagram --root "<PROJECT_ROOT>" --technical-md "<TECH_MD>" --file "<临时源稿.mmd>" --title "系统总体框架图" --category system-framework --fact-ids FACT-001 --reason "节点连线均来自技术MD与FACT"

# 渲染选中的候选图（先看 list 获得真实 VIS-ID）；自动尝试零依赖 SVG 回退
python skills/technical-visual-assets/scripts/visual_assets.py render --root "<PROJECT_ROOT>" --id VIS-真实ID

# 渲染后必做：SVG 自检 + 按真实尺寸出验收预览 PNG（禁止固定画布截图制造空白）
python skills/technical-visual-assets/scripts/visual_assets.py preview --root "<PROJECT_ROOT>" --id VIS-真实ID --run-id "<真实run-id>"

# 登记完整实体模块检索目标，不能登记没有上游事实的板卡
python skills/technical-visual-assets/scripts/visual_assets.py scope-module --root "<PROJECT_ROOT>" --technical-md "<TECH_MD>" --module "<技术MD中的真实模块名>" --fact-ids FACT-001 --reason "核心硬件功能单元"

# 搜索 URL 元数据，默认 DDGS(已安装时) → Openverse → Commons，绝不下载图
python skills/technical-visual-assets/scripts/search_candidates.py --root "<PROJECT_ROOT>" --technical-md "<TECH_MD>" --module "<技术MD中的真实模块名>" --fact-ids FACT-001 --provider auto --limit 6

# 只有本轮用户明确允许保存指定候选图，才可创建临时运行区并显式下载选中单张图
python skills/technical-visual-assets/scripts/visual_assets.py workdir --root "<PROJECT_ROOT>"
python skills/technical-visual-assets/scripts/download_selected_image.py --root "<PROJECT_ROOT>" --run-id "<真实run-id>" --image-url "https://真实选定的图片URL" --allow-image-download
# 对已保存的图，继续使用 visual_assets.py add-external / review 审核登记（见 references/asset-contract.md）

python skills/technical-visual-assets/scripts/visual_assets.py list --root "<PROJECT_ROOT>"
python skills/technical-visual-assets/scripts/visual_assets.py coverage --root "<PROJECT_ROOT>"
python skills/technical-visual-assets/scripts/visual_assets.py verify --root "<PROJECT_ROOT>"
```

**不要直接照抄示例行号或 FACT-001**：命令只是格式参考，必须替换成当前项目真实行号和真实关联 FACT。`--rights owned` 等审批声明必须有真实著作权事实，不得默认使用。

## 5. 已有项目资产契约与系统边界

```text
<PROJECT_ROOT>/
├── project-assets/
│   ├── project.json / facts.json / references.json / schedule.json / activity.jsonl
│   └── visual-assets/
│       ├── index.json                  # 稳定 VIS-ID、哈希、FACT、版权和来源
│       ├── requirements.json           # 已核实核心模块清单与待找照片范围
│       ├── diagrams/                   # 可编辑 .mmd 与有效 SVG、已引用本地图
│       └── images/                     # 本轮明确授权入库的候选或批准照片
├── deliverables/technical-document/    # 上游正式技术MD/HTML（严格只读）
└── .skill-tmp/technical-visual-assets/<run-id>/ # 可清理过程目录
```

- 兼容原 `core/contracts/shared-project-assets-contract.md` v1，**不修改**原 `project_assets.py` 的 `KINDS`，复用 `.asset-write.lock` 和 `activity.jsonl`。勿把图像写进插件安装目录。
- `VIS-...` 每个内容 SHA 稳定去重；已批准旧资产及历史文件不静默覆盖。源 MD SHA 改变时列为重新审阅事项。
- 所有来源页面和图片 URL 必须真实可回访；原图、候选与最终批准不等价。

## 6. 最终一次性执行汇报格式（必须）

**不要只说“找不到图片”。** 按下列结构提供每一个已经完成、未完成和阻塞的结果：

1. 项目 ID、实际技术 MD 路径/SHA、事实数、被使用的 `FACT-xxx`。
2. 本轮真实使用的网络搜索渠道、每种结果数、失败原因；安装第三方包数（默认 `0`）、下载图片数（默认 `0`）。
3. 系统框架图、功能架构图、核心流程图、模块整体实物图四类**逐类** PASS/PENDING/MISSING/N/A；包括新绘可编辑 `.mmd` 和实际渲染 SVG 的文件位置。
4. 每个核心模块逐项列出：**目标主体/真实型号、FACT、搜索候选 URL、实物图完整性、来源与许可核验、最终 VIS ID 与状态**。
5. 明确区分通过的图片、仅供参考但不代表本项目的图片、未验证型号的图片、无授权的图片；给出不能批准的确切理由。
6. 不触碰上游 MD/Word，不改项目事实，没有用户授权绝不下载外部图片；仅在确有可核验资产时登记。
7. 校验脚本真实运行结果、未完成的环境限制及**用户应该验收的实际图像**。

**严格失败**：缺少当前项目正式技术 MD、跨项目 FACT、伪造来源/授权/测试、未经许可安装软件或下载。**允许 WARN**：网络失效、缺少精确硬件板型、ASCII 语义含糊、图表渲染器不支持复杂语法、未找到可复用授权图片；不得为了提高通过率瞒报。

## 7. 按需读取的本地资源

- `references/image-selection-examples.md`：用户五张真实正反例和完整主体判断办法。
- `assets/image-selection-examples/`：五张用户当次提供的视觉案例，**不代表公开再分发许可**。
- `references/asset-contract.md`：VIS 索引/审核/项目隔离契约和 CLI 详情。
- `references/network-image-research.md`：DDGS、Openverse、Commons、搜索工具降级与原图来源审计。
- `scripts/plan_visuals.py`：只读真实技术需求盘点。
- `scripts/visual_assets.py`：候选、Mermaid/ASCII、渲染、事实审核、索引、去重和覆盖。
- `scripts/svg_fallback.py`：仅为安全、简单的有向无环图提供零依赖 SVG 渲染。
- `scripts/search_candidates.py`：仅检索 URL 元数据；不自动安装任何依赖、不下载图片。
- `scripts/download_selected_image.py`：用户明确许可的单张 HTTPS 图片受控保存；默认拒绝。

项目最终业务验收属于用户；本 Skill 的本地自动测试**不能代替**视觉、技术事实与图片授权的实际人工核验。
