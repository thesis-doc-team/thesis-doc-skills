# project-technical-doc — 项目理解 → MD + 用户可视化 HTML

## 这套 Skill 做什么

用户仅需提供本次项目的源码、技术手册、方案说明或现有测试资料。AI Agent 按**同一个工作流**完成：

```text
本次项目资料/源码
    ↓
只读理解项目、整理证据
    ↓
生成 <项目名称>-技术文档.md
    ↓
检查技术事实、章节结构、正文边界
    ↓
生成 physical-modules.json（实物模块清单）
    ↓
生成 content-index.json（表/图/模块分类与相似组）
    ↓
依据刚生成的 MD 生成首页摘要与用户可视化 HTML
    ↓
自动生成流程图 SVG（支持时）、检查 MD 与 HTML 一致性
    ↓
交付 MD + HTML + 执行汇报
```

HTML 只复用用户提供页面的**版式、排版、组件和交互设计**；不带入样例项目的名称、型号、功能、参数或测试结果。默认不生成“已知问题与改进建议”及同类独立章节、网页板块。

## 安装

解压后保留完整 `project-technical-doc/` 目录。Claude Code 常见位置：

```text
<项目目录>/.claude/skills/project-technical-doc/
```

Codex 常见位置：

```text
<项目目录>/.agents/skills/project-technical-doc/
```

确保 Agent 运行 Python。HTML 转换需要：

```bash
python -m pip install -r .claude/skills/project-technical-doc/requirements.txt
```

或按实际安装路径调整。**没有强制 Node、React 或云端服务**。Mermaid SVG 优先使用本地 `mmdc`；安装了 Graphviz `dot` 时，可将常见 `flowchart` 自动转 SVG。两者均不可用时，HTML 保留原始 Mermaid 定义并报告未转成图形。

## 你应该怎样调用

```text
使用 project-technical-doc Skill。只读理解当前我提供的项目源码和技术资料，
先生成标准技术文档 MD，再使用 Skill 内置的通用可视化页面架构，
从最终 MD 自动生成用户阅读的单文件 HTML。

严格保留真实技术事实、章节、表格、流程和实现状态；
不要出现“已知问题与改进建议”及同类评审、优化或未来规划章节。
完成两份产物的自检后，输出执行汇报，由我最终验收。
```

**用户不需要另外提供 HTML 范本**：通用布局已经集成在 `assets/layout.html` 中。

## 自动渲染命令

一般由 Agent 在生成并检查 MD 后自动执行，不需要用户手工操作：

```bash
python scripts/publish.py "output/technical-document/项目名称-技术文档.md" \
  --config "output/technical-document/展示配置.json" \
  --out-dir "output/technical-document"
```

若未提供项目首页 JSON 配置，去掉 `--config` 即可。发布前会校验 MD 同级的 `physical-modules.json` 与 `content-index.json`（均定名、不加版本号；无实物模块也写 `modules: []`），缺失或不合法即拒绝生成 HTML。契约见 SKILL.md「实物模块清单契约」与「内容分类索引契约」。

### 生成两个固定伴随产物

```bash
python scripts/gen_physical_modules.py "output/technical-document/项目名称-技术文档.md"
python scripts/classify_content.py "output/technical-document/项目名称-技术文档.md"
```

- `physical-modules.json`：只列具备实物形态的模块；`code/name/hardware` 必填，`category/source_files/pins/note` 可选；排除软件抽象层、纯逻辑、主程序。
- `content-index.json`：`items` + `groups` + `summary`；表格/流程图/实物模块按 `category` 分类，按 `group_id/group_title` 归并相似项；含 `line_start/line_end`、`content_sha256`，网站可直接分组/筛选。它**不改变原文、不渲染网站**。生成器会自动降级为不编造事实的章节速览/阅读路径，并输出报告 JSON。单独执行 MD→HTML 同样可使用该命令。

## 目录说明

```text
project-technical-doc/
├── SKILL.md                     核心执行规则（包括 MD→HTML 必须顺序）
├── README.md
├── VERSION.md
├── requirements.txt             Markdown/HTML 解析依赖
├── references/
│   ├── 技术文档范本.md            通用技术文档章节范本
│   ├── project-understanding.md  项目理解与源码证据提取
│   ├── style-and-structure.md    MD 写作规范
│   ├── quality-gates.md          技术真实性及一致性门禁
│   ├── shared-project-assets-contract.md 项目级共享资产协议 v1（跨 Skill）
│   └── html-layout-and-content.md HTML 页面布局/映射/交互规范
├── templates/
│   ├── technical-document-skeleton.md
│   ├── evidence-register.md
│   └── execution-report.md
├── assets/
│   └── layout.html               通用科技卡通风、离线网页骨架
├── examples/
│   └── showcase-config.example.json  仅展示 JSON 字段格式，不是项目事实
└── scripts/
    ├── check_markdown.py         MD 结构和内容边界检查
    ├── check_physical_modules.py 实物模块清单校验（physical-modules.json）
    ├── diagram_svg.py            流程图自动转换
    ├── render_html.py            Markdown 内容渲染/模板注入
    ├── validate_html.py          网页结构和 MD 内容一致性检查
    ├── project_assets.py         共享资产读写/运行目录/record-use
    └── publish.py                检查、渲染、验证的发布入口
```

## 交付边界与注意事项

- **MD 是技术内容唯一正式来源**，HTML 是展示派生物；发现技术错误优先修订 MD 并重新生成 HTML。
- 首页少量功能/参数卡需以 MD 为依据；未经证实的功能与实测不可写成完成。
- Mermaid 源码会保留在可展开区域；复杂图仅在有可用的本地渲染器时保证 SVG 转换。
- 自动校验能检查章节、小节、文字段落、代码、表格和锚点；不能代替真实浏览器视觉检查或项目实测。
- 系统不会自动修改项目源代码、原始技术资料或旧成果；默认对 HTML 新建版本文件。
- **一个项目一个资产包** `<PROJECT_ROOT>/`：`project-assets/`（数据，与任务书/开题报告 Skill 共用）+ `deliverables/`（成品）+ `.skill-tmp/`（运行区），按项目分类、整包可迁移；成品带版本号（-v1、-v2…），重生成不覆盖历史版本。本 Skill 将核实的技术事实以 FACT-xxx 写入共享库，后续文书按稳定 ID 复用；交付后 record-use 登记，共享资产永不删除。
- 最终验收由用户进行。
