# 执行结束清理中间文件：保留规则与安全删除规则

## 三类文件必须严格分开

| 类别 | 位置 | 执行结束处理 |
|---|---|---|
| **原始输入**：用户技术 MD、源码、官方 Word 模板、参考范本 | 用户原本存放的目录及 Skill 自带模板副本 | **永远不删、不覆盖** |
| **项目共享资产**：`project-assets/{project,facts,references,schedule}.json`、`activity.jsonl` | 本项目根目录固定位置 | **长期保留、维护、可在多个 Skill 复用** |
| **最终交付**：通过检查的任务书 DOCX、执行报告（若生成） | 用户指定路径，或 `deliverables/taskbook/` | **长期保留**，除非用户明确要求删除 |
| **中间文件**：结构扫描 JSON、候选文献 JSON、任务书数据 JSON、渲染 PNG/PDF、临时 DOCX、调试记录 | `.skill-tmp/thesis-taskbook-write/<run-id>/` | **先完成结果归档、再自动删除** |

## 规范工作流

1. 在项目根目录创建一次运行专属目录：
   ```bash
   python scripts/project_assets.py workdir --root /项目根目录
   ```
   输出路径形如 `/项目根目录/.skill-tmp/thesis-taskbook-write/20261030T080000Z-a1b2c3`，其内有本 Skill 所有权标记。
2. 所有中间 JSON、渲染图片、临时输入和调试 DOCX **只放到这一目录**。绝不能把临时结果留在 Skill 安装目录、`project-assets/` 或用户原资料旁。
3. 输出最终 Word 到 `deliverables/taskbook/`（或用户要求的位置），写入/校验共享资产，记录实际采用的引用 ID，形成最终简短执行报告；失败时输出必要的**失败原因摘要**而不是遗留大批测试文档。
4. 成功或失败终止时都应清理本轮目录：
   ```bash
   python scripts/project_assets.py cleanup --root /项目根目录 --run-id 本次ID
   ```
5. 仅在用户**明确要求保留调试材料**时，可将必要诊断内容作为明确命名的交付物另存，而不是默认留临时目录。

## 安全限制（不可降级）

- 清理命令只接受**单个本 Skill 标记过的 `run-id`**；不会提供对项目根目录、`project-assets/`、`deliverables/`、`.skill-tmp` 全目录的递归删除选项。
- 禁止 `rm -rf <PROJECT_ROOT>`、`rm -rf output` 等泛删除；禁止通配符清理不属于当前执行的目录。
- 遇到不存在的标记、目录符号链接、运行 ID 不合法、目标超出固定目录：**拒绝删除**。
- 运行失败时不要以“保留中间文件”作为默认行为；先把用户需要的错误概要写入执行报告，之后清理。若清理失败，执行报告明确列出残留位置与原因，不假装已删除。
- 更改共享资产失败时，不能因为清理中间文件而删除或回滚用户已有的共享记录。共享更改必须单独有检查和审计记录。
