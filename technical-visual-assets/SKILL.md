---
name: technical-visual-assets
version: 1.4.3
disable-model-invocation: true
description: 根据用户指定的唯一正式技术 Markdown，提取/创建系统架构图、功能树、核心流程图和真实数据表；强制正交（横平竖直）连线、Visio 式黑白工程图、A4 版心与实际 Word/WPS 分页验收，并为每张正式技术图生成中英文图题元数据与原生 VSDX（Visio 打开状态如实标注）。按 MD 明确记载的实体硬件生成用户实物图上传清单、审核本地上传照片。保留 Mermaid/SVG/可编辑 draw.io 与项目 VIS/FACT/RES 资产，完全取消联网搜图及自动安装。
---

# 技术视觉与表格资产｜v1.4.0（正交连线 · 中英文图题 · A4/Word · 完全离线）

## 0. 不可突破的约束

1. **唯一项目技术事实源 = 本轮用户指定的正式技术 Markdown `<TECH_MD>`**。必须位于 `<PROJECT_ROOT>/deliverables/technical-document/` 或用户明确指定的同项目路径。FACT-xxx 只作为同份 MD 的派生追溯，不是独立事实源；冲突则报告，不反向改写 MD。示例截图、模型常识、聊天历史、用户照片都不能补充或编造项目技术事实。
2. **彻底不联网搜图。** 不允许 WebSearch/WebFetch、Bing/百度/DDGS/Openverse/Commons、浏览器搜图、图片爬虫、图片 API、HTTP 下载图片。相关脚本和命令已移除。**实物模块图片只能由用户自己上传**；不存在“自动搜索候选”阶段，也不允许自动补齐不存在的实物照片。
3. **只做素材能力，不越界修改 Word 文书**。本 Skill 不改技术 MD、HTML、源码、官方 DOCX 模板、其他写作 Skill；输出是候选图、表格源、A4 设计约束与审核资产。最终 DOCX 插入由对应文书 Skill 完成，并执行排版校验。
4. **正交连线是硬门槛。** 所有常规连接线只能是水平线、垂直线或由二者组成的 90° 折线；不得默认输出任意角度斜线。箭头尖端自身的几何斜边不属于连接路径。只有图形语义明确要求特殊斜线时才允许例外，且必须写明原因。**不能只在样式名里写“正交”，必须检查实际 SVG/ draw.io 路径。**
5. **A4 页面适配是硬门槛。** 图表/表格不能仅因“能生成”就成为可插 Word 的正式素材。必须依据当前官方 DOCX 的实际纸张、页边距和所在节计算版心；过宽/过高时重新排布或拆图/拆表，绝不直接缩成看不清的小图。只有在 Word/WPS 真正渲染并检查后，才能宣称“Word 版面验收通过”。
6. **每张正式技术图必须有中英文图题元数据。** 如果目标文书要求按章节编号，使用 `figure_number`（如 `4-1`）；如果只是生成独立素材，可用项目内稳定序号，由后续排版方重排。中文题名和英文题名必须描述实际内容；图题放在图下，由 Word 原生段落渲染，**不得画进 SVG/PNG 像素**。模板只允许单行时可合并中英文，但不得改变官方模板结构。
7. 不臆造连线、模块状态、系统测试、实验曲线和表格数据。**测试计划 ≠ 测试结果**。本项目未使用、备用、待实现的设备，不能标成已实装照片。
8. 不自动安装任何包或字体，不调用外部下载，不运行学生上传的源码。不覆盖项目历史 `-vN` 文书版本，不写入插件安装目录。
9. **必须生成原生 `.vsdx` 文件**：`scripts/vsdx_writer.py` 从同一正交 spec 生成 Visio 2013+ Open Packaging 格式的节点、连线、文字和图题。生成后必须做包结构/XML/关系校验；若本机没有 Visio，状态必须标 `vsdx_verification=pending-visio-open`，不得写成“Visio 已打开合格”。只有真实 Visio/WPS 打开并保存验证后，才能标 `VISIO_OPEN_VERIFIED`。不得用改后缀的假 VSDX。

## 1. 核心输入与工作顺序

必需：`<PROJECT_ROOT>`、已正式确认的 `<TECH_MD>`、稳定 `project_id`。

要做正式 A4 空间适配时，必需：用户/学校提供的**原始官方 DOCX 模板**（只读）或明确的纸张/页边距设置。A4 门禁只需要读取模板的纸张与页边距，**不要求绑定章节，也不由本 Skill 把图插入 Word**；章节归属、图号重排由写作 Skill 或用户自行处理。模板可以经写作 Skill 在同项目中按真实路径只读引用，不能猜测页边距。

执行流程：

1. `md_pipeline.py scan`：只读扫描正式 MD，提取 Mermaid、ASCII 功能树、Markdown 表格、本地图片引用与证据行号。
2. `md_pipeline.py sync`：按六类归档到 `project-assets/resource-catalog/`，并自动建立**MD 中明确出现的硬件/完整模组的用户照片上传清单**。两次执行须幂等。
3. **技术图：**复用 MD 已有 Mermaid，按明确树关系生成缺失功能图；文本有足够证据时，Agent 才可以编写新的 Mermaid 或显式布局 JSON。每个节点和箭头都要能回指 MD 的章节/行号；无法确认的连接必须留在待确认，不能画错。保存可编辑源码。
4. **正交 Visio 式绘图：**参考 `references/visio-style-a4-guide.md`、`references/orthogonal-routing-rules.md` 和内置 7 张 Word 参考截图。使用 `scripts/visio_diagram.py` 从源自有据节点/箭头的 JSON 生成 `.svg` + `.drawio` + `.vsdx`；连接器由 `orthogonal_router.py` 自动布线或校验，不允许默认斜线。需要位图时用 `scripts/export_png.py` 在本机 Chrome/Edge 导出 300 dpi PNG。无原生 Visio 环境时不伪称 `.vsdx` 已生成。
5. **图题：**为每张正式图填写 `figure_number`、`caption_zh`、`caption_en` 和 `source_refs`；渲染器写出 `.figure.json` 元数据，不把图题画进图片。规则见 `references/english-caption-spec.md`。
6. **质量门禁：**运行 `scripts/figure_qc.py`，检查正交、节点重叠、连线穿节点、文字溢出、分支标签、A4 版心、中英文图题、SVG/drawio/VSDX 完整性和 RES 关联。程序通过不等于视觉验收通过；技术逻辑与英文语义仍需人工复核。
7. **用户实物照片：**使用 `md_pipeline.py module-list --save` 让用户看到“缺什么模块照片、名字、MD 行号、状态”。用户在**当前项目的** `user-uploads/` 中提交 PNG/JPG/WEBP；由 `md_pipeline.py upload-photo` 导入候选 VIS，再按原 VIS 审核检查完整主体、准确型号、来源/权利声明与同项目 FACT。未上传即 MISSING；用户照片与实际模块是否一致由人复核。
8. **数据表格：**直接保留 MD 中的真实行列和单元格。使用 `scripts/table_layout.py` 测算目标 A4 版心；下游必须生成**Word 原生可编辑表格**，**所有新生成的学术数据表必须是严格三线表**：仅表顶线、表头下线、表底线；不允许任何竖线或其他内部横线。固定官方表单框架不改动；若模板对新生成数据表要求与三线表冲突则 BLOCK 并交由用户处理。不将文字数据表转成大图片。
9. **A4 质量门禁：**使用 `scripts/a4_layout.py profile` 读取官方模板 A4 纸型/节/页边距/内容宽度；使用 `fit-figure` 测试图形物理尺寸和缩放后文字大小；下游写作 Skill 插入后运行 `audit --docx`、`figure_qc.py --docx` 并逐页查看 Word/WPS 或实际渲染截图。
10. 审核入库、引用登记、汇报。如果未提供正式模板，允许生成技术候选，但必须标注 `pending-template-and-word-visual-review`，**不得写“可直接插入 Word 且已合格”**。

## 2. 六类素材及规则

| 类别 | code | 数据从何而来 | A4 / 人工门槛 |
|---|---|---|---|
| 系统框架图 | `system-framework` | MD 中系统层次、组件及真实通信关系 | 分区层级清楚；大型框架优先分区/拆图，不超版心；连线正交 |
| 功能架构图 | `functional-architecture` | MD 功能树、明确父子关系 | 方框/层级，禁止借硬件清单充当功能划分；连线正交 |
| 核心流程图 | `flowchart` | MD 实际步骤、判断、分支、异常路径 | 流向清晰，长流程分段，菱形分支标“是/否”；连线正交 |
| 模块实物图 | `module-photo` | **用户上传照片**；所需模块名称只能从 MD 提取 | 完整设备/整板/整模组；不使用网络照片、不用裸元件代替 |
| 测试结果图 | `test-result` | MD 中有可追溯的真实测量或测试截图/数据 | 不从计划或设想生造实验曲线；图例/坐标适合 A4 |
| 数据表格 | `data-table` | MD 中真实 Markdown 表格 | 原生 Word **严格三线表**；宽度≤版心；不得有竖线/内层横线；内容完整 |

每一素材仅一个主分类，保留 `RES-xxx` 稳定标识、MD SHA256、章节/行号、图形源哈希、实际审阅状态、A4 模板版本和 VIS 关联。正式技术图还要保留 `figure_number`、`caption_zh`、`caption_en`、`caption_position=below`、`source_refs`、`routing_status` 和 `caption_review_status`。MD 变更须重新审核受影响资产，不能静默替换已交付成品。

## 3. 正交连线与布局规范（v1.4.0 新增）

完整规则见 `references/orthogonal-routing-rules.md`。执行时必须遵守：

### 3.1 连线

1. 常规连接路径只能由水平/垂直线段组成，**不得默认使用任意角度斜线**。
2. 优先上→下；需要横向展开时左→右。
3. 连线从上、下、左、右四个合理锚点进出矩形/菱形/起止节点，不从图形中心穿入。
4. 判断节点分支方向稳定：目标主要在下方的分支走底边；目标在侧方/上方的分支走左/右边。同一判断节点的“是/否”标签必须成对出现，靠近对应线段。
5. 连线必须避开其他节点、节点文字和图题；不可避免的交叉要尽量少，并在 QC 报告中计数。
6. 回环/重试支线从外侧绕行，不允许穿过中间节点。
7. 汇合点必须符合实际业务逻辑；不能为了布局方便把两条不同语义的支线强行合并。
8. 相邻节点统一间距，同级节点尽量对齐，判断分支左右尽量对称。
9. **不得因为自动布局方便而改变 MD 的技术流程语义**；如果路由失败，应先扩大间距、移动节点或拆图，而不是接受斜线/穿节点。

### 3.2 节点与文字

1. 白底、黑/深灰边框、无渐变/阴影；普通操作矩形、判断菱形、起止圆角矩形、分区虚线框。
2. 文字在节点内水平/垂直居中；不得超出边框，不得因自动缩小低于 9pt。
3. 长文本优先换行或加宽节点；中文不得乱码/方框。
4. 分支标签必须有白色底衬，且不得压在任何节点上。
5. 复杂流程优先拆成多个逻辑完整子图；不允许简单缩小整图来适配 A4。

### 3.3 分组框（subgraph）与 `<br/>` 标签

1. 复杂架构/时序图的分组框必须：**虚线边框 + 浅色底 + 清晰分组标签**；不得用无标签实线大框冒充分组。
2. 分组框之间不得互相压盖；嵌套必须有明确语义。分组标签不得压节点或其他分组标签；节点不得骑在分组边界上（跨边界需人工确认）。
3. 新增 `scripts/subgraph_layout.py`：把 `<br/>`/`<br>`/HTML 标签归一化为真实换行；按节点 `group`/`group_id`（或几何包含）识别成员；重算分组框为“成员网格 + 内边距 + 标签高度”；分组框纵向堆叠/并排，保证不重叠；组内节点重新网格化；之后交给正交路由器重路由。节点和连线不得被删除，拆图只作为可读性最后手段。
4. 使用 `visio_diagram.py --auto-layout` 或 spec 中 `layout: "subgraph"` 启用；`figure_qc.py` 会检查分组框重叠、分组标签重叠、节点跨边界、`<br/>` 残留、分组框是否虚线/有底色/有标签、连线是否穿过无关分组框。
5. 分组框样式为虚线 + `#F7F8FC` 浅底（可覆盖）；标签带白色底衬，避免连线压字。draw.io 同步使用虚线/浅底。

### 3.3 路由实现约束

`scripts/orthogonal_router.py` 是唯一默认路由器：它为每条边选锚点、在节点障碍格上做正交 A*、惩罚交叉/反向重叠/过多转折，并拒绝穿节点路径。`visio_diagram.py` 在写文件前调用它；显式 `points` 只有在**本身正交且不穿节点、不产生交叉**时才保留，否则自动重排。`figure_qc.py` 会再次扫描实际 SVG 的 `<polyline>` 和 draw.io 的 `orthogonalEdgeStyle`，不能只凭样式名放行。

## 4. 中英文图题规范（v1.4.0 新增）

完整规则见 `references/english-caption-spec.md`。

1. 每张正式图必须提供：
   - `figure_number`：按目标文书要求提供；可用章节号（如 `4-1`、`3-2`）或项目内稳定序号，不强制绑定章节；不得写死“图 1”。
   - `caption_zh`：中文描述性题名，如“阈值判断与告警流程图”。
   - `caption_en`：英文描述性题名，如“Threshold Judgment and Alarm Processing Flowchart”。
   - `source_refs`：章节/行号/证据，至少一项。
2. 图号、中文题、英文题必须语义一致；禁止只用 `Flowchart`、`System Diagram`、`Diagram` 等含糊标题。
3. 图题放在图片下方、居中；字号、字体、段前段后优先服从官方模板。
4. **图题不画进 SVG/PNG 像素**。SVG 可在 `<title>`/`<desc>` 和 `data-caption-*` 属性中保存元数据，但视觉文字由 Word/HTML 原生段落负责。
5. Word 中优先使用原生图题段落；中文与英文可分两段（中文在上、英文在下），模板只允许单行时可合并。图题与图片必须同页，不得跨页分离。
6. 图题元数据写入 `.figure.json` 并绑定到 RES；`md_pipeline.py attach-layout --figure-meta` 会把图号/中英文题/routing 状态写入资源目录。
7. 英文题名语义必须人工核对；`figure_qc.py` 的关键词一致性只是预警，不是语义证明。

## 5. A4 / Word 集成

1. 纸张 A4 = 210×297mm，但可用尺寸由 DOCX `sectPr/pgSz/pgMar` 决定；例如左右各 25mm 时正文宽仅 **160mm**。不得将固定 190mm 宽的图塞进去。
2. 通过 `a4_layout.py profile` 读取真实模板；`fit-figure` 检查缩放后文字是否仍 ≥9pt。纵向图还要预留图题、上下文和段落间距。
3. 图片优先嵌入型（inline），不要环绕浮动覆盖文字；不得拉伸变形；不得与页眉/页脚重叠。
4. 图与图题必须同页；图题不得孤立在上一页或下一页。
5. 插入后运行 `a4_layout.py audit --docx` 和 `figure_qc.py --docx`，再在 Word/WPS 中逐页实际渲染，检查出界、文字重叠、表格横向溢出、图题孤页、图表跨页截断。
6. 静态 XML 尺寸检查不等于 Word 最终渲染；没有实际页面截图/目检，不得宣称视觉验收通过。
7. 不能为了放下一张图破坏学校官方模板；裁剪、边距改写、横竖版切换都要取得模板许可。

## 6. 数据表格（三线表硬门禁保持）

1. 直接保留 MD 真实行列和单元格，不篡改数据。
2. 下游生成 **Word 原生可编辑表格**；所有新生成的学术数据表必须是严格三线表：表顶一条线、表头下一条线、表底一条线；无竖线、无数据行间横线、无表格截图。
3. 表头跨页重复；表格宽度在版心内；文字建议 ≥9pt，不允许缩成不可读小字。
4. **所有表头和数据单元格必须水平居中且垂直居中**；`three_line_table.py apply` 会自动设置，`audit` 把未居中列为 BLOCK。
5. 表格过宽时按语义拆成关联子表并重复关键列，不删数据。
6. 官方固定表单不改；模板要求与三线表冲突时 BLOCK 并请用户确认边界。
7. 每张新生成数据表在正式 Word 成品上运行 `three_line_table.py audit --docx ... --indices ...` 并保存 PASS 报告；没有 Python-docx/Word 运行环境时标记 PENDING，不得虚报通过。

## 7. 技术真实性与数据来源

1. 图中每个实际技术模块必须来自技术 MD。
2. 数据方向、连接关系、判断条件必须有对应事实依据；`source_refs` 要写章节和行号。
3. 不允许根据经验自行增加项目没有的硬件或功能。
4. 不允许为了让流程图更美观而修改实际业务逻辑。
5. 流程矛盾或条件不完整时报告，不擅自补全。
6. 不把参考范本中的模块照搬到其他项目。
7. FACT 只作为 MD 的派生索引，不作为独立事实源。
8. 不修改原始技术 MD，除非用户明确授权。
9. 特别检查“是/否”路径、处理顺序、循环、结束条件和异常分支；`figure_qc.py` 只能检查标签和几何，语义必须人工核对。

## 8. 用户上传实物图机制（保持）

1. 从技术 MD 提取需要照片的实体模块，输出 `module-requests.json/.md`；机器清单可能包含“落选方案/后续路线/泛称”误提，必须人工核对并在汇报中说明。
2. 照片放入本项目 `user-uploads/`，使用真实 `MOD-...` ID 执行 `upload-photo`。
3. 上传只生成待审核候选；必须检查完整设备/模组/整板、型号证据、来源/权利声明、同项目 FACT。
4. 不得用网络照片、宣传图、裸元件或局部特写冒充完整模组。
5. 不得安装或启用 DDGS、Openverse、Commons、百度搜图等网络图片搜索程序。
6. 用户照片与实际模块是否一致由用户最终确认。
7. 正式 VIS 审核使用 `visual_assets.py review` 时，必须明确 `--category module-photo`、`--subject-level complete-device|complete-module|complete-board`、`--full-module-confirmed`、`--model-evidence`、`--visual-evidence`、`--rights owned|express-permission`、`--permission-evidence` 及真实同项目 `--fact-ids`。这些是实际审核步骤，不能让模型自动勾选。

## 9. 命令与产物

在 `thesis-doc-suite/skills/technical-visual-assets/` 下执行：

```powershell
$ROOT = "E:\thesis-projects\demo"
$MD = "$ROOT\deliverables\technical-document\技术文档.md"
python scripts/md_pipeline.py scan --root $ROOT --technical-md $MD
python scripts/md_pipeline.py sync --root $ROOT --technical-md $MD
python scripts/md_pipeline.py module-list --root $ROOT --technical-md $MD --save
python scripts/md_pipeline.py report --root $ROOT --technical-md $MD
```

### 9.1 生成正交图（必须带中英文图题）

```powershell
python scripts/visio_diagram.py --spec "$ROOT\project-assets\resource-catalog\diagrams\figure-01.json" `
  --template "E:\official\官方模板.docx" `
  --out-prefix "$ROOT\project-assets\resource-catalog\diagrams\figure-01" `
  --require-caption
# 输出：figure-01.svg + figure-01.drawio + figure-01.figure.json
```

需要位图时：

```powershell
python scripts/export_png.py --svg "$ROOT\...\figure-01.svg" --out "$ROOT\...\figure-01-300dpi.png" --dpi 300
```

### 9.2 质量检查（几何 + 图题 + A4）

```powershell
python scripts/figure_qc.py --spec "$ROOT\...\figure-01.json" `
  --svg "$ROOT\...\figure-01.svg" --drawio "$ROOT\...\figure-01.drawio" `
  --template "E:\official\官方模板.docx" `
  --json "$ROOT\...\figure-01.qc.json"
```

### 9.3 绑定 RES 与图题元数据

```powershell
python scripts/md_pipeline.py attach-layout --root $ROOT --technical-md $MD `
  --id "RES-真实ID" --svg "$ROOT\...\figure-01.svg" --drawio "$ROOT\...\figure-01.drawio" `
  --template "E:\official\官方模板.docx" `
  --figure-meta "$ROOT\...\figure-01.figure.json" `
  --evidence "已逐条核对正式技术MD对应章节的真实节点、连线与箭头方向"
```

### 9.4 A4 与三线表

```powershell
python scripts/a4_layout.py profile --template "E:\official\官方模板.docx"
python scripts/a4_layout.py fit-figure --template "E:\official\官方模板.docx" --width-mm 155 --height-mm 95 --text-pt 9.5
python scripts/a4_layout.py audit --docx "<写作Skill生成的正式成品.docx>"
python scripts/table_layout.py --template "E:\official\官方模板.docx" --table-md "<某个RES表格.md>"
python scripts/three_line_table.py apply --docx "<待检查成品.docx>" --indices 1 --out "<三线表修订副本.docx>"
python scripts/three_line_table.py audit --docx "<三线表修订副本.docx>" --indices 1 --json "<三线表审计.json>"
```

### 9.5 目录规范

```text
<PROJECT_ROOT>/
├─ deliverables/technical-document/技术文档.md  # 唯一项目技术事实源
├─ user-uploads/                               # 用户自行上传照片的输入区
├─ project-assets/
│  ├─ facts.json                               # 派生兼容事实（非新事实入口）
│  ├─ visual-assets/index.json                 # 正式 VIS 原有资产/人工审核
│  ├─ visual-assets/images/                    # 审核前的用户照片实体
│  └─ resource-catalog/
│     ├─ index.json                            # 六类 RES 资源 + 图题出版元数据
│     ├─ module-requests.json / .md            # 用户需要上传的实物模块清单
│     ├─ diagrams/                             # .mmd / .svg / .drawio / .figure.json
│     └─ tables/                               # 完整 Markdown 表格原始文本
└─ .skill-tmp/technical-visual-assets/<run-id>/ # 自有可清理工作区
```

### 9.6 共享资产与信息管理（与其它 Skill 同一契约）

`project-assets/` 是项目**长期共享数据资产**（跨全部文书 Skill 同读同写），不是本 Skill 的私有目录，也不是中间文件：

- **唯一根目录**：`<PROJECT_ROOT>/project-assets/`；**禁止**把项目资产写进插件安装目录、`references/`、`examples/`。初始化由 `/thesis-doc-suite:init-project` 或 `project_assets.py init`（project-technical-doc 副本）完成，**本 Skill 不自建第二套资产库**；未初始化时命令直接报错并指向 init-project。
- **项目隔离**：读取 `project.json` 校验 `schema_version` 与 `project_id`；与本轮 `--project-id` 不一致立即停止，**禁止串项目**。
- **事实只读**：`facts.json` 只按 `FACT-xxx` 稳定 ID 引用并做 project_id/schema 校验，**本 Skill 不写事实**（事实由 project-technical-doc 维护）；`facts.json` 缺失时按空库处理，不阻断。
- **写锁**：对共享资产的写入一律持有 `project-assets/.asset-write.lock` 排他锁，**禁止绕过、强删或忽略锁冲突**。
- **审计流水**：所有资产变更追加到 `project-assets/activity.jsonl`（`at`/`action`/`actor`/`project_id`），与其它 Skill 同一本账，便于追溯。
- **运行区纪律**：中间文件只写 `.skill-tmp/technical-visual-assets/<run-id>/`（`workdir` 创建，带 `.owned-by-technical-visual-assets` 所有权标记，内容为技能名）；`cleanup` 只删自己带合法标记的单个 run 目录，遇符号链接、路径越界或标记不符一律拒绝，**绝不删除**其他 Skill 的 `.skill-tmp`、共享资产、用户上传原件与历史成品。

```bash
python scripts/visual_assets.py workdir --root "$ROOT" --project-id "$PID"
python scripts/visual_assets.py cleanup --root "$ROOT" --project-id "$PID" --run-id "$RUN_ID"
```

## 10. 自动质量门禁

`scripts/figure_qc.py` 至少检查：

1. 非正交连接线（SVG `<polyline>` 与 spec `points` 双重检查）。
2. 节点之间重叠。
3. 连接线穿过节点内部。
4. 节点文字溢出（复用 `validate` 的字宽/行高计算）。
5. 箭头缺失或来源/目标元数据不一致。
6. 判断分支标签缺失、重复或压到节点上。
7. 技术流程逻辑与 MD 不一致（需要人工语义核对；QC 只检查 `source_refs` 完整性并标记 `semantic_review_required`）。
8. 图片宽高与 A4 版心不匹配。
9. 图题缺失、图号格式错误、中文/英文题过于笼统。
10. VSDX 包缺件、XML/关系损坏、页面无形状；VSDX 校验状态与验证状态不一致。
11. 表头/数据单元格未水平或垂直居中。
12. 英文图题与中文题目的关键词一致性预警（不替代人工语义检查）。
13. 图题与图片分页分离（`--docx` 模式检查图下是否有中英文题；是否同页仍需 Word 渲染）。
14. 图形渲染失败（SVG/drawio/VSDX XML 解析、毫米宽高、根元素）。
15. 绘图源文件缺失或尺寸不一致。
16. 图形资源与原 VIS/RES 索引不一致（`--catalog --id`）。

**通过标准**：`status = PASS_GEOMETRY_NEEDS_SEMANTIC_AND_VISUAL_REVIEW` 只表示程序检查通过；必须在真实 Word/WPS 页面中逐页目检，并人工核对技术逻辑与英文题名语义，才能做最终验收。

## 11. 失败门禁与执行汇报

`BLOCK`：MD 缺失/越项目；图数据无 MD 依据；脚本无法解析关系；上传目标不存在；图片含恶意/未知格式；图片版权或型号证据缺失却要求批准；图超版心/字体小于9pt；出现斜线连接；节点重叠或连线穿节点；判断分支标签缺失；图题缺失/格式错误/过于笼统；VSDX 包结构损坏或页面无形状；表格单元格未水平/垂直居中；表格信息被删减；新生成数据表出现竖线/内部网格线、不是严格三线表或未经过三线表审计；非 A4 却按 A4 硬插；违反官方模板。

`WARN / PENDING`：用户没有上传照片、没有提供模板、复杂图形仍需实际目检、没有 Word/WPS 实际渲染证据、复杂路由存在 1–2 处不可避免交叉、英文图题关键词预警。应保留候选并明确缺口。

每次输出：项目 ID、正式 MD 路径及哈希；6 类资源数及来源行号；建议上传的硬件模块及是否待确认；可编辑 `.mmd`/`.drawio`/`.svg`/`.figure.json` 的真实文件清单；模板 A4 内容宽高与图片/表格适配结果；正交布线 QC 结果（交叉数、自动重排边数）；中英文图题元数据；Word 实际检查是否完成；旧 VIS 的审核状态；处理异常/权限问题；修改文件与真实测试结论。**用户做最终验收。**

## 12. 参考文档与示例

- `references/orthogonal-routing-rules.md`：正交布线、锚点、分支、障碍、QC 规则。
- `references/english-caption-spec.md`：图号、中英文题名、元数据 schema、Word 原生图题。
- `references/a4-figure-layout-spec.md`：A4 版心、图片/图题/表格尺寸与 Word 验收清单。
- `references/vsdx-export-spec.md`：原生 VSDX 包结构、形状/连线/图题映射与 Visio 打开验证状态。
- `references/visio-style-a4-guide.md`：7 张 Word 参考截图逆向规则 + A4 约束 + 正交/图题补充。
- `references/subgraph-layout.md`：分组框虚线/浅底/标签、`<br/>` 归一化、自动子图布局与信息完整性边界。
- `references/asset-contract.md`：RES/VIS/FACT 兼容与 v1.4.0 图题字段。
- `references/image-selection-examples.md` + `assets/image-selection-examples/`：用户实物照片正反例（完整设备/完整模组/完整步进电机 vs 裸芯片/局部特写）。
- `examples/visio-style-example.json`：带中英文图题的规范 spec。
- `examples/orthogonal-flow-example.svg`、`examples/orthogonal-flow-example.drawio`、`examples/orthogonal-flow-example.vsdx`、`examples/orthogonal-flow-example.figure.json`、`examples/orthogonal-flow-example-300dpi.png`：正交示例（含原生 VSDX）。
- `examples/before-diagonal-sms-flow-300dpi.png` 与 `examples/after-orthogonal-sms-flow-300dpi.png`：修改前后对照。**仅作格式判例**，图中 SIM900A/AT 指令等节点不得复制为其他项目的技术事实。
- `examples/A4-正交流程图与英文图题示例.docx` 与 `page-1.png`：真实 Word 渲染样例（非学校官方模板）。
- `examples/A4-图表排版示例.docx`、`examples/A4-三线表强制规范示例.docx`：A4/三线表格式样例。

## 13. 最终验收

用户需最终确认：

1. 图中节点、连线、箭头方向是否与正式技术 MD 完全一致。
2. 所有常规连线是否正交，是否存在穿节点、压文字、不可读的小字。
3. 中英文图题是否语义一致、编号正确、位于图下，并与图片同页。
4. 是否提供学校官方 DOCX 模板或明确页边距设置，以便重新做 A4 空间验收；本 Skill 只生成素材，不负责插入。
5. 正式 Word 成品中的新增数据表是否通过三线表审计。
6. 实物模块照片是否由用户本人上传并完成 VIS 审核。