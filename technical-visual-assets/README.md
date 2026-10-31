# technical-visual-assets v0.3.0

本 Skill 是 `thesis-doc-suite` 的公共图片资料层，**不是 Word 插图器**。它基于 `project-technical-doc` 的技术 Markdown + 同项目 FACT，建立四类素材：系统框架图、功能架构图、真实关键流程图、完整核心模块实物图。拒绝电阻等意义不明的局部器件图。

## 最小依赖

- Python 3.10+ 标准库，已有插件及 `project-technical-doc` 绘图脚本。
- **没有任何自动 pip/npm/apt 安装操作**。`search_candidates.py` 的可选 DDGS 只有预先安装时可用；否则尝试 Commons API 或让 Claude Code 使用已经存在的网页浏览工具。
- 图形渲染只使用已安装的 Mermaid CLI/Graphviz；不存在就保留源码与 WARN，不安装。
- 不自动下载图片；图片下载需用户明确许可，并显式 `--allow-image-download`。

## 主要命令

`visual_assets.py`: `scan-md`, `scope-module`, `render`, `add-external`, `review`, `list`, `coverage`, `verify`, `workdir`, `cleanup`。

`search_candidates.py`: 只搜候选 URL，无写入、无下载、无安装。

`download_selected_image.py`: 明确授权后才下载一张真正图片到本轮运行区，验证实际图片格式。

完整运行规则见 [`SKILL.md`](SKILL.md)，使用前需存在正式技术 MD 和 `project-assets/facts.json`。

## 新增：用户五张正反例（v0.3.0）

见 [`references/image-selection-examples.md`](references/image-selection-examples.md)，内含用户上传的原始截图 5 张（`assets/image-selection-examples/`），前 3 张反例、后 2 张正例。

判断依据是**图片展示对象是否为当前项目所需的完整功能模块/完整执行器**，而不是图片是否干净、是否透明背景。裸传感器 IC、孤立小配件、芯片内部框图不能充当模块/电机整体照片；完整步进电机、完整传感器小板符合期望的主体层级，但**型号与版权仍需另行核验**。

审批网络图片需 `--subject-level` 明示主体层级；不引入新第三方依赖，也不会自动下载额外文件。
