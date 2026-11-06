# 项目介绍 HTML 内容映射（Markdown → 结构化数据 → HTML）

## 一、唯一内容来源

HTML 只读取《项目介绍与功能说明.md》，**不得读取《工程实施方案.md》**。页面中的项目名、功能、流程、场景、系统组成和验收场景必须能在介绍 Markdown 中找到对应内容；允许标题简化、分组、摘要和排版调整，不允许改变原意或补充未确认的功能、指标、实测结果。

生成链路：

```text
介绍 Markdown
  → 轻量 Markdown 解析（标题/段落/列表/表格/引用/代码块）
  → 章节提取（项目概述/场景/功能/系统/流程/验收）
  → PROJECT_DATA 结构化数据
  → templates/project-introduction.html
  → 单文件 HTML
```

## 二、章节识别与映射

| HTML 区块 | Markdown 来源 | 提取规则 | 缺失时 |
|---|---|---|---|
| 项目标题 | 一级标题 `# ...｜项目介绍与功能说明` | 取 `｜` 前的项目全称；按“的”拆成 lead/accent/tail | 缺失则生成失败 |
| 版本/状态 | 开头引用块的 `版本：`、`文档状态：` | 取原文；状态不写入正文断言 |  audience 显示“项目介绍 · 可视化展示” |
| 项目简介 | `## 项目概述/项目简介/项目定位` 首段 | 截取 160 字以内，保留原意 | 用通用说明占位（不编造功能） |
| 项目特点 | 功能小节前 4 项 | 标题 + 简述截取 | 无功能时用场景前 4 项 |
| 功能卡片 | `## 功能说明/功能介绍/核心功能/功能模块` 下的 `###` 小节 | 标题去编号；描述取首段，若首段以冒号结尾/过短则补公式、清单或表头列；截取 170 字 | 隐藏功能区，并给出 WARN |
| 使用流程 | `## 使用与交互/使用流程/交互流程` 的 `5.1 首次使用` 有序列表 | 标题取分句前短语，描述取完整条目；无列表时依次回退到无序列表、表格、mermaid 节点标签 | 隐藏流程区 |
| 应用场景 | `## 应用场景/系统目标` 的 `2.1 典型场景` 列表 | 标题取分句前短语，描述取完整条目；无列表时回退表格 | 隐藏场景区 |
| 系统组成 | `## 系统组成/组成概览` 表格第一列 | 去表头、去重、最多 10 项；无表格时回退列表/段落拆分 | 隐藏组成区 |
| 验收场景 | `## 功能展示/验收场景` 表格 | 按表头匹配 `编号/场景/操作/预期/状态`；每行一条；无表格时隐藏 | 隐藏场景示意区 |

## 三、动态数量

- 功能：3 / 6 / 10+ 个都按同一卡片组件渲染；桌面 3 列、平板 2 列、手机 1 列，禁止固定卡片数量。
- 流程：≤5 步使用带箭头的等分网格；>5 步改为 3 列网格（手机 1 列），避免箭头指向空位。
- 场景：1 个时占满一行；2–4 个两列；更多自动换行。
- 系统组成：chip 自动换行；超过 10 项截断并保留前 10 项（原文仍在 Markdown）。
- 验收场景：全部渲染为切换按钮；数量多时自动换行，屏幕只显示当前选中项。

## 四、结构化数据（PROJECT_DATA）

```json
{
  "schema_version": 1,
  "project": {"title": "", "short_title": "", "category": "", "version": "", "status": "", "source": ""},
  "overview": {"intro": ""},
  "tags": ["", ""],
  "summary": [{"symbol": "▦", "value": "", "note": ""}],
  "features": [{"id": "F01", "title": "", "description": "", "icon": "scale", "tone": "blue"}],
  "featuresIntro": "",
  "workflow": [{"title": "", "description": ""}],
  "workflowIntro": "",
  "scenarios": [{"title": "", "description": "", "symbol": "▦", "tone": "mint"}],
  "scenariosIntro": "",
  "system": {"items": [""], "intro": ""},
  "showcase": {"kind": "slots|metrics", "title": "", "badge": "概念展示", "bottom": "", "tiles": [], "callouts": []},
  "demo": {"title": "", "intro": "", "note": "验收场景 · 预期结果 · 未实测", "items": []},
  "page_title": "",
  "page_description": "",
  "header_note": "",
  "footer_note": ""
}
```

数据同时嵌入 `<script type="application/json" id="project-data">`，供场景切换脚本读取；静态 HTML 已由 Python 渲染，因此禁用 JavaScript 时主要内容仍可阅读。

## 五、分类、标题与视觉映射

- **类别 eyebrow**：按标题/功能/系统关键词推断，如 `EMBEDDED · SMART STORAGE`、`EMBEDDED · ENVIRONMENT`、`SMART INTERACTION · UI`、`ROBOTICS · CONTROL`、`SOFTWARE · SYSTEM`、`PROJECT · SOLUTION`。类别只是展示标签，不改变功能描述。
- **标题拆分**：全称按最后一个“的”拆成 lead 与 accent；若 accent 以“系统”结尾，把“系统”放回 tail。长标题允许换行，禁止 `nowrap`。
- **品牌名**：取 accent 的前 6 个中文字符（含英文时最多 10 字符），用于页头；不改变项目全称。
- **图标**：按功能标题关键词从固定集合选择；标题优先，描述只作兜底，避免“无线通信”的描述里出现“重量”而被误判为称重。
- **概念面板**：默认 `metrics`（功能 tile）；仓储/库存/货架类项目且功能 ≥3 时用 `slots`（纸箱形 tile）。两种模式共用同一卡片、色调和进度条样式，不把“4 个货位”写死。
- **场景示意**：只使用验收表；屏幕大号字显示场景编号（如 S01），状态徽章显示“预期，待实测”，正文显示操作与预期结果；固定提示“未实测”。

## 六、失败处理

- 找不到一级标题：生成失败（退出码 2），不得猜项目名。
- 功能/流程/场景/系统/验收任一缺失：隐藏对应区块，生成结果标记 WARN，并在执行汇报中列出缺失项。
- 模板占位符未全部替换：生成失败，避免输出半成品。
- 输出先写临时文件再原子替换；不得覆盖同名历史版本（版本号由调用方递增）。
- 只要求重新生成 HTML 时，复用当前项目已确认的介绍 MD；介绍 MD 改动后重新生成 HTML 并重新校验。

## 七、命令

```bash
python scripts/generate_intro_html.py \
  --intro "deliverables/project-introduction/<项目简称>-项目介绍与功能说明-vN.md" \
  --out "deliverables/project-introduction/<项目简称>-项目介绍与功能说明-vN.html" \
  --data-out "<WORKDIR>/project-data.json"

python scripts/validate_intro_html.py \
  --intro "<INTRO_MD>" --html "<INTRO_HTML>" --report "<WORKDIR>/html-qa.json"
```