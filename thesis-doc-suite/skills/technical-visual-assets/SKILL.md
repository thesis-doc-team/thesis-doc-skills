---
name: technical-visual-assets
version: 0.3.0
disable-model-invocation: true
description: 只基于 project-technical-doc 的正式技术 Markdown 与同项目 FACT-xxx，建立系统框架图、功能架构图、关键流程图、核心模块完整实物图四类真实可追溯的视觉资产；按准确型号在线搜索官网、CSDN、百度等原始来源并核验，按用户提供的五张正反例识别完整功能对象与裸芯片、局部组件、芯片内部框图的区别，不使用局部元件或意义不明图片；禁止自动安装软件包和下载无关文件，不改业务 Word 文档。
---

# technical-visual-assets | 技术图示与模块实物图公共 Skill

## 0. 执行范围与红线（必须先读）

本 Skill 只负责**识别技术图需求 → 复用原技术图 → 查找完整模块照片 → 验证 → 分类 → 持久资产登记 → 覆盖检查**。不写任务书/开题报告/文献综述/中期检查/指导记录正文，不修改官方模板，不执行 DOCX 插图，不修改 6 个业务 Skill。其他 Skill 负责最终“适当位置放适当图片”。

**选图前的必读资料**：`references/image-selection-examples.md`（用户真实提供的前 3 张反例、后 2 张正例；包含图片本体与判断依据）。涉及模块/电机/传感器实物图时，必须实际查看五张案例，而不是仅阅读文件名或自动相信搜索标题。

**不可突破的要求：**

1. **技术事实只来自上游**：`<PROJECT_ROOT>/deliverables/technical-document/` 中由 `project-technical-doc` 生成的最终技术 MD，和同项目 `project-assets/facts.json` 的 `FACT-xxx`。技术事实中的型号、模块组成、功能、接口、流程、已实现状态只能来自它们。网络页面、CSDN、百度、器件厂商资料**只能核对外部图片及其所描绘的设备**，不能将网上找到的新模块反向添加为“本项目使用/实现的模块”。缺少技术 MD 时 BLOCK；同项目事实冲突时 BLOCK 相关素材。
2. **四类必检**：①系统框架/总体架构图 `system-framework`；②功能架构/功能模块关系图 `functional-architecture`；③具有真实步骤/分支/数据关系的关键流程图 `flowchart`；④每个**已确认核心硬件模块**的整体实物图 `module-photo`。四类**分别检查，不得互相冒充**。仅允许真实项目支持的图；缺失须标记 MISSING / 待补证据，不得“凑图”。纯软件项目的硬件照片可单独报告 N/A，但禁止伪造硬件。
3. **图片主体要完整且对象层级正确**：模块实物图必须清晰显示**整个对应功能模块/开发板/传感器模组/整机单元（例如完整步进电机）**，且能核对准确型号/版本/厂家和主体是否真实。**单张电阻、电容、裸芯片封装、芯片引脚局部、PCB 某角、无关配件、芯片内部功能框图、教程装饰图、广告、截断/模糊图、只有背景的照片，不能充当模块实物图**。完整电机虽然是单一器件，但作为独立执行器整体是合格的实物图层级；整块传感器小板是合格的传感器模组层级。透明/白底不是拒绝理由。例如技术 MD 只说明使用 STM32F407 主控芯片，不得直接用另一型号 STM32 开发板照片来冒充项目的开发板；未确认实际板型时可找准确芯片的**官方完整产品封装图**并标注“芯片产品图（非项目实拍）”，但是否足以满足模块实物图需按真实模块定义审核。
4. **严格最小引入**：只使用当前 Claude Code **已经可用**的 WebSearch/WebFetch/浏览器能力和本插件既有渲染程序、Python 标准库。**绝对不执行 `pip install`、`npm install`、`npx` 自动拉包、`apt install`、`brew install`、下载模型权重、爬虫框架或插件安装**。DDGS 仅当用户环境**已安装**时可选调用；没有就用现有搜索能力或标准库 Commons API；完全不可用如实 WARN，不得自动补环境。
5. **外部检索 ≠ 自动下载**：先搜索并检查原始来源/许可；`search_candidates.py` 只返回候选 URL，不下载文件。只有当前用户明确允许“保存该图”时，才允许下载**选中的图片文件**到当前项目受控运行区，并在调用 `download_selected_image.py` 时显式提供 `--allow-image-download`。不得下载其他文档、PDF、压缩包、脚本、未知文件或整个网页资产包；不得绕过验证码、登录、版权和访问限制。
6. **授权与事实分开核验**：图片在网上真实存在不等于技术型号正确，也不代表允许复用或公开论文转载。未经确认的保留候选，不得标记 `approved`。禁止假装看过图片、查过原网址或获得授权。
7. **只写项目资产**：一个项目 = `project-assets/` 数据 + `deliverables/` 成品 + `.skill-tmp/` 运行；不修改上游技术 MD、原始图片、六个业务 Skill、官方模板，也不保存到插件安装目录。保留资产版本与审计。

## 1. 输入与前置检查

必须有：
- 当前项目绝对路径 `<PROJECT_ROOT>`、同项目有效 `project_id`。
- `project-technical-doc` 完成的正式技术 MD 的明确文件路径（若有 v1/v2，按用户/项目确认版本选择，不凭修改时间猜）。
- `<PROJECT_ROOT>/project-assets/project.json` 和 `facts.json`。

可选：联网工具、已安装 DDGS、原有 Mermaid CLI/Graphviz、上游 MD 引用的本地图像。**这些是可选能力，不允许因此擅自安装依赖。**

入场检查：
1. 运行公共 `core/asset-management/project_assets.py status` 或读取同一项目资产；确认 `schema_version=1` 和一致的 `project_id`。
2. 读取最终技术 MD 的章节、`FACT-xxx`、Mermaid 与已有图片引用；保存 MD SHA-256、行号与章节。
3. 仅从这些资料整理**受证据约束的视觉需求表**：图类别、图要说明什么、相关模块、准确型号、FACT ID、事实状态和来源定位。
4. 严格区分**整机/系统**、**功能模块**、**模块整板**、**单个器件/PCB 元件**的层次，不能把物理器件列表当作功能架构图，也不能把一张器件照片当成系统框架图。

`implemented` 有实现证据；`declared` 是资料声明；`proposed` 是方案；`unverified` 不可作为已审核正式图的事实依据。任一外部网页不得提升这些状态。

## 2. 四类视觉资产的判断标准与五张实图对照

| 类型 | 必须说明的内容 | 合格形式 | 一律不合格的替代品 |
|---|---|---|---|
| 系统框架图 | 项目主要层次、真实子系统、接口和数据/控制边界 | 结构框图、系统拓扑、已核验的 Mermaid/SVG | 单个开发板产品照、无来源的通用物联网架构图 |
| 功能架构图 | 功能分组、从属关系与各功能职责 | 功能树、功能模块关系图、按真实需求绘制的框图 | 硬件 BOM 列表、随意连接的功能卡片、系统框架图直接改名 |
| 关键流程图 | 起点→实际步骤/分支→结果，符合执行/交互/数据先后顺序 | 可编辑 Mermaid + 正确渲染的 SVG；已有合格图优先 | 缺失真实分支的套话流程、无语义箭头和装饰图 |
| 模块实物图 | 核心实体模块的完整外观；型号/版本/供应商是否匹配 | 原厂产品整图、项目自有完整实拍（如确实存在） | 单个电阻/电容、局部引脚、同系列但不同型号、教程图、不清楚的缩略图 |

**用户五张图片的判例**（必须打开 `references/image-selection-examples.md` 中的图片对照）：反例①裸传感器芯片封装、反例②孤立小部件特写、反例③ MCU 内部资源框图——这三张**不能**代替当前项目的完整模块实物图/系统或功能架构；正例④整台步进电机外观、正例⑤整块传感器 PCB 模组——两张符合用户期望的**整体主体层级**。但正例也必须匹配当前项目实际型号及复用许可，不能直接放入任意项目。第三张在准确芯片型号且文档需要“芯片内部功能框图”时可能有别的合法用途，不得将其一概判为无用。

关键规则：
- **一图一主目的**，不得同一张图同时记为系统框架、功能架构、流程图来满足覆盖率。图可在多个文档中复用，但不得跨类别刷数。
- 系统框架/功能架构/流程图原则上先复用最终技术 MD 中的 Mermaid 或已引用本地图；确需新图时只用真实 FACT+MD 内容绘制、生成可编辑 `.mmd`，经审核和渲染后入库。不能联网找一张与项目不一致的通用技术图冒充自研架构。
- “模块”是能独立承担功能的系统组成，如通信模组、驱动板、传感器模组、主控板、工业终端，而不是任意元器件。若项目实际上就是单个电子元件的设计研究，应按真实项目情况标注产品整体图，不得强行套“模组”说法。
- 硬件很多时，只为**技术 MD/FACT 已确认且与正文有关的核心模块**登记查图任务；无需给每个电阻或每个引脚找图，不为数量制造工作。
- 若无法确认精确模块/板型，不以近似型号冒充；标记 `MISSING` 并说明缺少型号或实物证据。

## 3. 工作流（固定）

### 阶段 A：真实识别与需求覆盖

1. 从已确认技术 MD 抽取系统边界、功能层次、主要业务流程及物理模块清单；每个结论关联 FACT-xxx。
2. 现有图优先：`scan-md` 发现 Mermaid 和 MD 本地图片引用；此操作只登记**候选**，自动提示类别仅供参考，不能免人工检查。
3. 为每一个需要实物图的**核心模块**调用 `scope-module`，写入名称、FACT IDs、准确型号与为何属于核心模块；不允许范围泛化到电阻等小元件。
4. 输出“四类素材需求与缺口”：系统框架、功能架构、关键流程、每个核心模块完整实物照。先检查当前索引是否已有合格资产；不满足才开始补全。

### 阶段 B：复用与绘制图表（不安装绘图包）

1. 逐图查看原 Markdown 中 Mermaid 的章节、节点、箭头和语义是否正确，与事实状态一致。
2. 借用已经存在的 `skills/project-technical-doc/scripts/diagram_svg.py` 渲染，优先使用**已经安装**的 `mmdc`，否则若 Graphviz `dot` 已存在则走其受限回退；**不允许安装**。不支持的 Mermaid 语法保存 `.mmd` 并 WARN；不生成假 SVG。
3. 若 MD 缺少四类中的某种结构图、但已具备足够真实事实，允许本 Skill 根据真实 MD + FACT **新增独立技术示意图候选**（不回写 MD）。必须带准确节点、关系、图注、源事实映射，不允许补虚构节点；先产生 `.mmd` 再按现有渲染器真实渲染。新增图的人工确认和版本持久化规则必须与原图一致。
4. 系统框架图和功能架构图须分别审查表达层次是否正确，不能仅修改标题后重复使用一张图。

### 阶段 C：网络模块实物图查找（先核准检索对象层级，仅真实模块）

每个核心模块单独检索。先从技术 MD 和 FACT 提取**真实完整型号/板型/厂家**，再生成准确中英文查询。

**搜图前必须建立正确的“目标对象”认知**：先写出本项目需要的是「整套功能模组/PCB 整板」「完整独立执行器（电机等）」「完整控制板/通信模块」还是「芯片/零件本体」。**不要看到型号关键词就把搜索结果第一张芯片封装图当成传感器模块**。若 MD 只确认芯片型号而未确认板型，不能自动确定一块网售 breakout board 就是实际模块；标注缺证据。

对照用户五张实例：
- **反例 1**：只拍裸传感器芯片封装，没有整个传感器模块/PCB/接口，淘汰作为模块实物图。
- **反例 2**：只拍一个小型孤立配件，无法证明是目标完整模块，淘汰。
- **反例 3**：展示 MCU/芯片内部功能模块，不是项目整体系统框架、功能架构，也不是模块产品外观，不能用来满足四类覆盖；对准确芯片的专门内部框图任务可另行考虑。
- **正例 1**：完整步进电机，输出轴、壳体、连接接口等主体清楚，是合理的完整执行器照片形态。
- **正例 2**：整块传感器模组/小板（图片中有多个完整板卡）；能看见整体 PCB、引脚/焊盘和模块构造，是合理的整模组照片形态。实际应用仍须确认具体板卡版本，不能混用图中不同变体。

执行 `scope-module` 前，把每个对象写成「原文名称｜完整目标层级｜核心功能｜已确认型号｜证据 FACT｜期望图片完整范围」，没有证据的对象不得查图充数。

检索顺序：
1. 厂家官网的型号产品页、规格书关联媒体图（优先“整板/整模组”官方产品图）。
2. 公开可验证的专业分销商产品页及官方授权媒体。
3. CSDN、百度图片、Bing 等第三方搜索用于**发现线索**，须点击溯源到图片原始页面，不能以百度缩略图或 CSDN 的不明转载作为授权证据。
4. 可用开放许可图片资源如 Wikimedia Commons，但仍需核对准确型号、作者和单文件许可。

**可用工具顺序**：Claude Code 当前已有的 WebSearch/WebFetch/浏览器 → `scripts/search_candidates.py`（已安装 DDGS 时可使用；否则仅 Python 标准库 Wikimedia Commons API）→ 网络不可用时 WARN。不得擅自装 DDGS/Playwright/Crawl4AI 或调用 `npx` 拉取 MCP。

对每个候选逐个核对：
- `subject_is_whole_module`：完整设备、完整电机、整板、整模组是否可见？仅裸芯片、孤立零件、板上电阻、局部电路或芯片内部框图，**淘汰作为模块实物图**。
- `exact_model_match`：厂商/完整型号/板卡修订版可证实吗？系列相似图或型号不符，**淘汰**。
- `image_is_explanatory`：清楚展示模块本体且能说明对应技术内容吗？只有外包装、配套线材或无关场景，**淘汰**。
- `source_is_real`：实际访问原网页和原图了吗？只看到搜索摘要，**候选未核实**。
- `rights_are_known`：有可定位许可证、授权声明或权利人许可吗？不明确则 `unverified`，不得当作可公开发表的插图。

**禁止**“搜到几张就算完成”。当只有无关/局部图，返回 `MISSING` 并继续尝试其他已有检索渠道；没有合格图就诚实报告，而非拼凑一张电阻照片。

### 阶段 D：可控保存与审核登记

1. 搜索阶段只查看链接和必要页面内容，不自动保存任何无关文件。必要时使用 `search_candidates.py` 的只读候选结果；不得以搜索摘要代替逐图查看。
2. 当前任务**明确允许下载/保存图片时**，在核对原图 URL 后先创建 `workdir`，使用已有浏览器下载能力，或使用**需要显式 `--allow-image-download`** 的安全脚本，仅抓一张选中的 PNG/JPG/WEBP 到该运行区；不下载其他格式或依赖。
3. `add-external` 检查真实文件头、项目 MD 中的模块名、原始来源页面 URL 与图片 URL，保存为候选。不得把一张局部电阻图改名为“模块实物图”通过检查。
4. 模型必须**实际查看图片**才能执行 `review --approve`，明确确认四类之一、技术事实 IDs、图形内容说明。对于模块实物图，只有完整主体经核实才传 `--full-module-confirmed --subject-level complete-device|complete-module|complete-board`，同时写明识别依据；这是审核声明，不是程序自动视觉识别的证明。
5. 外部候选必须还要有真实的来源核验日期、核验人、许可及复用依据才能批准。无法获取许可则保留候选。避免把“教学/内部研究可看”错误等同于“公开发表可转载”。
6. 所有临时文件执行后安全清理；正式索引和已批准图片、可编辑 Mermaid、历史版本**绝不删除**。

### 阶段 E：四类覆盖与交付

执行 `coverage` 和 `verify`。**只有**系统框架、功能架构、流程图及每个登记的核心硬件模块都存在对应合格且批准资产时，覆盖状态才为 `PASS`。若某类别没有足够事实、工具或许可，必须如实输出 `INCOMPLETE` 和缺失原因，不能强行补图。

交付：资产索引 `VIS-xxx`、可编辑 `.mmd`/SVG、实物图片（已获合法保存权限的）、每图的 FACT 链接和原始来源/许可、完整性/缺口报告。下游业务 Skill 在模板允许时自行决定插图和图注，本 Skill **不负责插图**。

## 4. 现有 CLI（仅 Python 标准库，不调用安装器）

从插件目录或使用绝对路径调用：

```bash
# 发现已有 Mermaid 与 MD 中的本地图像引用（只登记候选）
python skills/technical-visual-assets/scripts/visual_assets.py scan-md --root "<PROJECT_ROOT>" --technical-md "<PROJECT_ROOT>/deliverables/technical-document/项目-技术文档.md"

# 将实际确认的核心模块登记为“需要整模块实物图”的任务
python skills/technical-visual-assets/scripts/visual_assets.py scope-module --root "<PROJECT_ROOT>" --technical-md "<PROJECT_ROOT>/deliverables/technical-document/项目-技术文档.md" --module "<来自MD的真实模块名称>" --fact-ids FACT-001 --reason "核心主控模块，技术文档第3章"

# 如果现有技术 MD 缺少某一类图，先核实 FACT，自己写可编辑 Mermaid 候选（不修改技术 MD）
python skills/technical-visual-assets/scripts/visual_assets.py add-diagram --root "<PROJECT_ROOT>" --file "<本轮运行区>/new-framework.mmd" --technical-md "<正式技术MD>" --title "系统总体框架图" --category system-framework --fact-ids FACT-001,FACT-002 --reason "节点与关系分别来自技术文档及事实登记"

# 复用已有 Mermaid SVG 渲染器；缺少已安装的引擎只保留源码并报告
python skills/technical-visual-assets/scripts/visual_assets.py render --root "<PROJECT_ROOT>" --id VIS-XXXXXXXXXXXX

# 搜索候选：只查链接，绝不安装包、下载图片
python skills/technical-visual-assets/scripts/search_candidates.py --root "<PROJECT_ROOT>" --technical-md "<正式技术MD>" --module "<准确型号/模块名称>" --fact-ids FACT-001 --provider auto --limit 6

# 明确允许保存候选原图后才可执行下载（不下载 PDF/软件包/脚本）
python skills/technical-visual-assets/scripts/visual_assets.py workdir --root "<PROJECT_ROOT>"
python skills/technical-visual-assets/scripts/download_selected_image.py --root "<PROJECT_ROOT>" --run-id "<上一步run-id>" --image-url "https://真实原图地址" --allow-image-download

# 将已经取得且真正核查的图像加入项目候选库
python skills/technical-visual-assets/scripts/visual_assets.py add-external --root "<PROJECT_ROOT>" --file "<当前运行区中已保存的图片>" --title "<准确图片标题>" --module "<技术MD中的模块原名>" --technical-md "<正式技术MD>" --source-page "https://真实来源页" --image-url "https://真实原图" --author "<实际权利人>" --license "<真实许可证或unknown>"

# 最后逐图审查后批准。图片类型必须分别记录；不要只为了PASS而勾选
python skills/technical-visual-assets/scripts/visual_assets.py review --root "<PROJECT_ROOT>" --id VIS-XXXXXXXXXXXX --fact-ids FACT-001 --category system-framework --rights owned --reason "<真实审核依据>" --visual-evidence "<至少16字，实际所见主体、框和关系的核验记录>" --approve

# 核查四类覆盖与资产一致性
python skills/technical-visual-assets/scripts/visual_assets.py coverage --root "<PROJECT_ROOT>"
python skills/technical-visual-assets/scripts/visual_assets.py verify --root "<PROJECT_ROOT>"
python skills/technical-visual-assets/scripts/visual_assets.py list --root "<PROJECT_ROOT>" --approved-only
```

外部模块图片的审批还必须提供：`--category module-photo --full-module-confirmed --model-evidence <真实型号核验依据> --source-checked-at <实际日期> --checked-by <实际核验者> --permission-evidence <许可依据> --visual-evidence <观察依据>`，并根据实际许可填写 `--rights`。不得使用示例占位文字充当实际核验结果。

`render` 使用的外部命令若不存在，不要补装；`search_candidates.py` 的 `auto` 在已安装 DDGS 时调用 DDGS，否则使用 Commons API（需要网络）。百度/CSDN/官方网页通过现有的网页搜索/浏览器能力调查。没有工具就报告不可用。运行脚本**不会自行安装任何软件**。

**复核记录范例（示意格式，不得拿示例填真实审计）：** `目标=完整步进电机｜图中=壳体+轴+接线接口整体｜主体层级=complete-device｜型号=待核验｜判断=结构合格但型号未核验，保持候选`。裸传感器 IC、孤立小部件、芯片内部框图分别作为以上三类**反例**处理，不得复用为“模块整体照”。

**视觉边界说明**：本地脚本只能检查图片格式、大小、元数据与审核字段，不能通过简单规则真正识别照片是否拍了整个电机或模块。审批前由具备视觉能力的 Agent 或用户实际检查图像，并写下具体观察依据。`--full-module-confirmed` 等标志是审核记录，绝不是计算机视觉自动判定。

## 5. 资产目录与契约

```text
<PROJECT_ROOT>/
├── project-assets/
│   ├── project.json, facts.json, references.json, schedule.json, activity.jsonl
│   └── visual-assets/
│       ├── index.json                    # 唯一 VIS 索引、批准状态、来源/许可
│       ├── requirements.json             # 核心模块范围，须绑定真实 FACT
│       ├── diagrams/                     # Mermaid/.svg 和 MD 现有本地图副本
│       └── images/                       # 已授权登记的模块实物图副本
├── deliverables/technical-document/      # 只读上游正式 MD、HTML
└── .skill-tmp/technical-visual-assets/<run-id>/  # 受控图片下载临时区
```

`visual-assets/` 是兼容原 `schema_version=1` 的新子资产，不把视觉内容硬塞进现有 `core/asset-management/project_assets.py merge --kind`。共用 `.asset-write.lock` 与 `activity.jsonl`；同内容哈希去重，不能静默覆盖批准后的旧资产。详见 `references/asset-contract.md`。

## 6. 汇报格式与失败条件

每次汇报必须包括：上游 MD 路径与 SHA、`project_id`、本次实际调用的搜索渠道、安装的包数（默认 **0**）、下载的候选图片数、实际核查原网页数、四类覆盖表、核心模块逐一图像匹配结果、批准/待审/缺失、每张图片的 `VIS` ID、图注建议/来源/权限/FACT、存在的不确定项与未执行项目。

**FAIL / BLOCK**：没有技术 MD、项目 ID 错、技术 MD 与 FACT 冲突、疑似跨项目数据、故意伪造来源/版权/实拍、下载未授权的文件、执行未经许可的软件安装。

**WARN / INCOMPLETE**：只有流程图但缺功能架构图、只找到局部电阻照片、网上无法确认精确型号、无明确许可证、已安装图形渲染器不可用、网络工具不可用。遇到缺口不要“拿通用图片填满四类”。

无实际人工/模型视觉检查，不得宣称“实物主体准确”；无实际联网结果，不得宣称“网上已核验”；自动测试成功不代表插图内容正确。最终人工验收归用户。
