# Technical Visual Assets v1.0.0

`thesis-doc-suite` 的公共技术视觉素材 Skill。输入已发布的 `project-technical-doc` Markdown 和同项目 `FACT-xxx`，一次性检查并尽量完善**系统总体框架、功能架构、关键流程图、完整核心模块实物照片**，按项目保存 `VIS-...` 资产及核验记录。六个文书 Skill 的 Word 插图由它们自己负责。

## 不装包、不乱下载

**Python 3.10+ 标准库即能运行基本识别、候选登记、ASCII 转图、简单 SVG 渲染、资产审核。** Mermaid CLI、Graphviz、DDGS 只是可选的已有能力：不会自动安装、下载模型、安装浏览器或爬虫。Openverse / Wikimedia Commons 元数据查询只消耗网络 API，图片文件默认不下载。对百度/CSDN 等网站仅用 Claude Code 已有浏览/搜索工具，不绕过反爬。只有用户本轮明确允许保存具体图片时，才能显式调用选中单张图的安全下载命令。

## 使用前准备

1. 原项目已经通过 `/thesis-doc-suite:init-project` 初始化。
2. 已有 `<PROJECT_ROOT>/deliverables/technical-document/` 中的一份正式 Markdown 技术文档。
3. `<PROJECT_ROOT>/project-assets/facts.json` 已有对应事实及可信来源。没有支持图片内容的 FACT 就只保留候选，不可批准。
4. 本 Skill **必须**复制到 `thesis-doc-suite/skills/technical-visual-assets/`，并在现有 `core/contracts/skill-catalog.json` 注册；从该插件目录启动 Claude Code。

## 一键测试命令示例（Claude Code 中调用）

```text
/thesis-doc-suite:technical-visual-assets

项目根目录：E:\thesis-work\my-project
正式技术MD：E:\thesis-work\my-project\deliverables\technical-document\项目-技术文档.md

根据当前 MD 和 FACT 一次性完整执行：
先复用六张已有 Mermaid，识别并将可证实的 ASCII 系统框架、功能树主动绘制为候选图；
再对核心硬件逐项检索完整模块实物图，严格遵守五张正反例，验证准确型号、原始来源和版权。
本轮仅允许网络检索，不允许下载图片，不安装任何软件包。
交付四类图资产/缺口表，列出实际脚本、结果和未通过原因。
```

## 主要工具

| 脚本 | 作用 | 是否联网/修改文件 |
|---|---|---|
| `scripts/plan_visuals.py` | 只读定位 Mermaid、ASCII 区块与 FACT | 不联网，默认不修改 |
| `scripts/visual_assets.py` | 扫描、ASCII 转候选、渲染、审核、登记、覆盖与清理 | 本地管理，不联网 |
| `scripts/svg_fallback.py` | 简单流程图/架构图零依赖 SVG 渲染 | 不联网，仅受支持图语法 |
| `scripts/search_candidates.py` | DDGS（若已安装）/Openverse/Commons 公开图片线索检索 | 请求元数据；不下载图片 |
| `scripts/download_selected_image.py` | 用户已授权的选定单张图片受控下载 | 仅 HTTPS 图片，需要显式许可 |

完整业务规则在 [SKILL.md](SKILL.md)，选图标准在 [image-selection-examples.md](references/image-selection-examples.md)，资产格式在 [asset-contract.md](references/asset-contract.md)。

**特别声明：** 本地测试不代表真实图片、型号、版权或外部网页访问已经通过人工核验。五张用户截图只用于本地选图对照，公开分发到 GitHub 前要核对图片再分发权限；也可删除样例 PNG，保留文字判例。
