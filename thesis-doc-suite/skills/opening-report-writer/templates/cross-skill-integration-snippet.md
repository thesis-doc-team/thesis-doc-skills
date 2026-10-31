# 主 Agent 路由文书 Skill 的参考片段

目标是让不同 Skill 只在**事实/文献/周计划资产层**共享信息，不能混用模板与脚本。

- 技术说明：`project-technical-doc` 负责当前项目的可追溯技术 MD/可视化 HTML，开题 Skill 只读最终 MD。
- 任务书：`thesis-taskbook-write` 负责官方任务书，维护项目周计划与真实参考文献；开题 Skill 复用同一个 `project-assets/references.json` 和 `schedule.json`，但不调用任务书填充脚本。
- 开题报告：`opening-report-writer` 只使用 `assets/official-opening-report-template.docx`；只写 `deliverables/opening-report/`。
- 中期记录：`thesis-midterm-check-write` 针对中期表的进度与整改，可能维护额外 `progress.json`；开题报告不能倒写未来已完成成绩。

项目统一 `PROJECT_ROOT`、稳定 `project_id`、`FACT-xxx/REF-xxx/周计划ID`，每份文书有独立运行区、模板锁和版本检查。用户同时要求多个文书时应分开执行并分别报告。
