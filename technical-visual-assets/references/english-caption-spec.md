# 中英文图题规范（technical-visual-assets v1.4.1）

> **编号不是章节绑定**：如果目标文书要求按章节编号，用 `4-1` 这类格式；如果只生成独立素材，可用项目内稳定序号。本 Skill 只保存图题元数据，不负责把图插入 Word；插入后的最终编号由排版方决定。

## 1. 为什么必须有英文图题

正式毕业设计/学术报告的图题通常采用“图 X-Y 中文题名 + Fig. X-Y English Title”。英文题名不是装饰，而是图内容的可检索描述。禁止用 `Flowchart`、`System Diagram`、`Diagram` 这类无法区分具体图的泛称。

## 2. 编号规则

1. 图号按正式 Word 文档的章节编号，例如：
   - 第 4 章第 1 图：`4-1`
   - 第 7 章第 5 图：`7-5`
2. 不使用全局连续编号（除非学校模板明确要求）。
3. 图号与表号独立；图题不得与表题混用。
4. `figure_number` 只存 `4-1`，不存“图 4-1”；完整题名由元数据/Word 段落生成。
5. 同一项目内图号不得重复；插入 Word 后若章节调整，必须重新生成编号，不能保留旧号。

## 3. 题名写法

### 3.1 中文题名

- 描述实际内容，2–60 字。
- 常用结构：`对象 + 动作/属性 + 图类`，例如“阈值判断与告警流程图”“系统总体分层架构图”“数据采集与处理流程图”。
- 禁止只写“流程图”“系统图”“示意图”。
- 与正文术语一致；不得引入 MD 中没有的模块名。

### 3.2 英文题名

- 首字母大写；实词首字母大写（Title Case）或按学校模板。
- 至少 3 个单词，且至少一个具体技术对象；不能只有泛称。
- 常用结构：`[Domain Object] [Action/Attribute] Flowchart / Architecture / Diagram`。
- 示例：

| 中文 | 推荐英文 | 不推荐 |
|---|---|---|
| 阈值判断与告警流程图 | Threshold Judgment and Alarm Processing Flowchart | Alarm Flowchart |
| 系统总体分层架构图 | Overall System Layered Architecture | System Diagram |
| 运行时数据流图 | Runtime Data Flow Diagram | Data Diagram |
| 系统上电启动流程图 | System Power-on Initialization Flowchart | Startup Flowchart |
| 主循环调度流程图 | Main Loop Scheduling Flowchart | Loop Flowchart |
| JSON 封装与 4G 上传流程图 | JSON Packaging and 4G Upload Flowchart | Upload Flowchart |
| SIM900A 短信发送流程图 | SIM900A SMS Sending Flowchart | SMS Diagram |
| 数据采集与处理流程图 | Data Acquisition and Processing Flowchart | Data Flowchart |
| 页面切换交互流程图 | Page Switching Interaction Flowchart | Page Flowchart |
| 系统功能架构图 | System Functional Architecture Diagram | Function Diagram |

## 4. 元数据 schema

`visio_diagram.py` 生成 `*.figure.json`：

```json
{
  "schema": "tva-figure-meta/1.0",
  "figure_number": "7-3",
  "caption_zh": "阈值判断与告警流程图",
  "caption_en": "Threshold Judgment and Alarm Processing Flowchart",
  "caption_zh_full": "图 7-3 阈值判断与告警流程图",
  "caption_en_full": "Fig. 7-3 Threshold Judgment and Alarm Processing Flowchart",
  "caption_position": "below",
  "semantic_check": "heuristic-match",
  "semantic_review_required": true,
  "routing": "orthogonal",
  "crossings": 0,
  "geometry_mm": [155.0, 176.0],
  "font_pt": 9.5,
  "svg": "...figure-06.svg",
  "editable_drawio": "...figure-06.drawio",
  "native_visio_vsdx": false,
  "review_status": "pending-semantic-and-Word-page-review"
}
```

`md_pipeline.py attach-layout --figure-meta` 会把图号/中英文题/路由状态写入 `resource-catalog/index.json` 的同一 RES 条目，供 Word/HTML/素材库复用。

## 5. Word 中的呈现

1. 图题放在图片下方、居中。
2. 默认两段：
   - `图 7-3 阈值判断与告警流程图`
   - `Fig. 7-3 Threshold Judgment and Alarm Processing Flowchart`
3. 学校模板只允许单行时，可合并为：
   - `图 7-3 阈值判断与告警流程图  Fig. 7-3 Threshold Judgment and Alarm Processing Flowchart`
4. 字体、字号、行距、段前段后优先服从官方模板；模板未规定时，中文宋体、英文 Times New Roman，10.5pt 左右。
5. **图题不得画进 SVG/PNG 像素**；Word 使用原生图题段落，便于重新编号、检索和格式统一。
6. 图片与图题必须同页；不得图题孤页、图题被页脚遮挡。
7. 图题与正文之间保持模板规定的间距；不得用空行硬撑。

## 6. 自动检查与人工复核

`figure_qc.py` 会检查：

- `figure_number` 是否符合 `章节-序号`。
- 中文/英文题是否为空、过短、过长或命中泛称黑名单。
- 英文题是否至少 3 个词、首字母大写、含具体技术词。
- 中英文题是否命中同一技术关键词（**预警，不是语义证明**）。
- SVG `<title>`/`<desc>` 与 `data-caption-*` 是否存在。
- `--docx` 模式下每张图下方是否有中文题和 `Fig. X-Y` 英文题、是否居中、图号是否一致。

**必须人工确认**：英文题是否真的描述了图的内容、术语是否符合专业习惯、中文题是否与正文一致、图题是否与图片同页。

## 7. 常见错误

| 错误 | 后果 | 修正 |
|---|---|---|
| 英文只写 `Flowchart` | 无法区分图，答辩时被追问 | 加技术对象和动作 |
| 图号写死 `图 1` | 与章节编号不符 | 用 `figure_number` 按章节生成 |
| 图题画进 PNG | 无法重编号、字体不一致 | 用 Word 原生段落 |
| 中英文题号不一致 | 排版/引用错乱 | 同一 `figure_number` 生成 |
| 图题与图片跨页 | 图题孤页 | 设置“与下段同页”/调整图高 |
| 英文题与中文题语义不符 | 学术不严谨 | 人工逐图核对 |