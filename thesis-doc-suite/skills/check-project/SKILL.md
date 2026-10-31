---
name: check-project
version: 0.1.0
argument-hint: "[项目根目录] [目标Skill名称]"
description: 检查运行环境（Python/依赖/渲染器）、插件完整性（清单/技能/模板哈希）与项目资产状态（初始化/技术事实/参考文献/周计划），按 PASS / WARN / BLOCK 三类输出结论与修复建议。当用户说"检查环境""能不能生成""前置条件""为什么执行不了"或在生成文书前想确认资料齐备时使用。
---

# check-project｜前置条件与资产检查

## 目标

在执行任何文书 Skill 之前（或排查执行失败原因时），给出**环境、插件、项目数据**三方面的 PASS / WARN / BLOCK 结论：

- **PASS**：满足条件。
- **WARN**：可以继续，但可能降低内容完整度或质量（例如文献不足，执行时需补检索）。
- **BLOCK**：关键条件不足，不能可靠执行当前操作（例如官方模板缺失/哈希不符、插件结构损坏）。

**判级原则**：不要把所有缺少的信息都判为 BLOCK；只有确实影响目标 Skill 可靠执行的条件才阻止操作。个人信息缺失、可选资料缺失一般只是 WARN（对应 Skill 支持留白/降级执行）。

## 执行步骤

1. **收集参数**：`<PROJECT_ROOT>`（用户当前项目根目录，可省略——省略则只查环境与插件）；目标 Skill 名称（可选，提供后按该 Skill 的真实门槛判级）。
2. **运行检查脚本**：

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/check_env.py" \
     --root "<PROJECT_ROOT>" --skill "<目标Skill名称>" --json "<可选报告.json>"
   ```

   脚本输出逐条 `PASS/WARN/BLOCK: [区域] 说明` 与 `SUMMARY`。区域含义：`python/deps`（运行环境）、`render`（LibreOffice 渲染）、`plugin/template`（插件结构与模板哈希）、`project/assets`（项目数据）、`skill`（目标 Skill 门槛）。
3. **补充脚本无法覆盖的信息**（对话中确认后按同样三类汇报）：
   - Claude Code 与插件是否已加载：若本 Skill 正在运行，即证明插件已加载（PASS）；否则提示用 `claude --plugin-dir <插件目录>` 或 `/plugin` 安装。
   - 技术资料是否已就位：询问/查看 `<PROJECT_ROOT>` 或用户指定处是否有源码/技术 MD/DOCX/PDF；完全缺失对文书 Skill 是 BLOCK（没有事实来源），有部分资料是 WARN。
   - 用户是否已提供官方模板：本插件内置五个官方模板只读副本；用户提供新版模板时须重新审计适配（WARN 提示）。
4. **汇总输出**：按 `环境 → 插件与模板 → 项目数据 → 目标 Skill 门槛` 顺序汇报三类结论；对每个 WARN/BLOCK 给出**具体处理动作**（例如"pip install python-docx"、"先运行 /thesis-doc-suite:init-project"、"补检索至 ≥10 篇已核验文献"）。
5. **可交互补全建议**：对缺资料的项给出补全入口（如建议先运行 `/thesis-doc-suite:init-project`、提示放入技术资料的建议位置），但尽量减少用户反复手动输入。

## 与业务 Skill 的关系

本 Skill **只检查、不修改**任何资产与文书（写 `--json` 报告文件除外，且仅在用户指定路径时写）。业务 Skill 内部的强制门禁（模板锁定、事实门禁、截图验证）不因本检查 PASS 而豁免。
