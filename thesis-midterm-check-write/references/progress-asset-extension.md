# 可选扩展 `progress.json` v1：中期状态与计划分离

**兼容性：** 与 taskbook v1.1 的 `project.json / facts.json / references.json / schedule.json / activity.jsonl` 不冲突，只在相同 `<PROJECT_ROOT>/project-assets/` 增加一个文件。旧任务书脚本可继续读取原有文件而无需调整自己的输出。

结构：

```json
{
  "schema_version": 1,
  "project_id": "实际项目稳定 ID",
  "items": [
    {
      "id": "PROG-001",
      "as_of": "YYYY-MM-DD",
      "category": "completed",
      "status": "draft",
      "description": "有来源的具体进展，不是成绩模板",
      "source": "证据文件路径 + 章节 / 用户确认的时间点",
      "related_fact_ids": ["FACT-001"],
      "notes": "draft 为待用户核实；确认前不冒充实际验收"
    }
  ]
}
```

`category`：`completed/in_progress/pending/risk/next_step`；`status`：`draft/confirmed`。初次创建采用 draft，**只有真实用户确认/源文件中明确载明且可追溯的事实**才写 confirmed。`schedule.json` 是计划、`facts.json` 是相对长期技术事实、`progress.json` 是某个日期的真实阶段状态；不要互相偷换。稳定 ID 不反复重新生成；更正已有 ID 须显式 `--replace --reason` 并写 activity 日志。不要把所有中期段落拆成一大堆无用的冗余记录。

`project_assets.py merge --kind progress` 支持增补、冲突保护、审计；老项目没有 `progress.json` 时首次 merge 自动创建，不影响旧资产。这个扩展**不表示必须在每次运行时追加状态**；若本轮缺少可核实进展，可以只做待核实文稿，不入库假事实。
