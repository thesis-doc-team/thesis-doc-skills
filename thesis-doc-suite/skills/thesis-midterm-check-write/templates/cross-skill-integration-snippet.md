# 跨 Skill 可复制的资产层补充片段

> 这是协议片段，给已安装的任务书 / 开题报告 / 技术文档 Skill 查阅，不要求它们引入中期检查的 Word 填充脚本。

```markdown
## 共享项目资产

- 每个真实项目唯一 `<PROJECT_ROOT>` 与稳定 `project_id`；共同使用 `<PROJECT_ROOT>/project-assets/` 的 `project.json`, `facts.json`, `references.json`, `schedule.json`, `activity.jsonl`。
- 文献使用稳定 `REF-xxx`，核验来源可包含知网、万方、维普、出版商/学协会、CSDN（网页补充不可冒充正式论文）；不同文书的 `[1]...[N]` 是独立排版序号。
- 周计划 `schedule.json` 是项目级基线，不是中期完成证明；`draft` 不等于 `confirmed`。变更必须有真实理由及审计记录。
- 可选中期进展扩展文件 `progress.json`，通过 `PROG-xxx`、日期、`draft/confirmed` 与来源区分阶段实际进展，旧 Skill 不认识此文件时可安全忽略，绝不可删除或覆盖。
- 每份文书各自使用官方模板，各自输出到 `deliverables/{taskbook|proposal|midterm}/`，各自所有权运行区 `.skill-tmp/<skill-name>/<run-id>/`，成功/失败结束时只清理本轮中间文件。
- 不能把另一份文书的正文当作可自动复用的真实进展；只能复用经过校验的事实、文献和计划。
```

建议：已有任务书 Skill 的 schema_version=1 不变，默认不要修改它的填充脚本；若它想读取中期进展，可以**只读**参考 `progress.json` 的 `as_of/status/source`，不能以“计划”自动反推“已完成”。
