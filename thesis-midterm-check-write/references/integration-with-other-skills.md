# 与技术文档 / 任务书 / 开题报告 Skill 集成边界

`project-technical-doc` 产生带来源的技术理解，可能输出技术 MD 与用户可视化 HTML。中期 Skill 只读其技术事实及真实阶段资料，不修改源码/技术文档、不输出 HTML，不对项目进行系统开发。

`thesis-taskbook-write` 负责未来应完成的任务、周计划和参考文献，官方模板也不同。中期 Skill 复用相同 `project-assets` 的技术事实、计划、真实文献，但要核实“当前已完成多少”，可以贡献可选 `progress.json`；**不能直接把任务书中的未来要求写成已完成**。

`proposal-write`（开题报告）负责背景、方案、预期成果等另一份文书，复用相同稳定 `REF-ID/FACT-ID`，但有自己官方 DOCX 和独立格式门禁。三个文书只在项目资产层交流，不共享 Word 填充定位脚本或文书正文。

在 Codex / Claude Code 中可由主 Agent 先路由任务：用户说“中期检查记录表”→调用本 Skill；“任务书”→任务书 Skill；“开题报告”→开题 Skill；用户同时要多个文书则分开运行，严禁直接复用上一份模板的字段坐标。一个项目只有一个 `PROJECT_ROOT`、一个稳定 `project_id`，每个 Skill 有独立的运行区和成品目录。
