# JSON 输入结构范例（均为**假设结构演示**，不要作为真实项目进展使用）

`midterm-draft.json` 写在 `<PROJECT_ROOT>/.skill-tmp/thesis-midterm-check-write/<run-id>/` 中，仅含当次文书稿件和相关共享资产 ID：

```json
{
  "project_id": "真实项目稳定ID",
  "title": "本轮用户真实毕业设计题目",
  "student_name": "",
  "class_name": "",
  "teacher_opinion_is_draft": true,
  "progress_paragraphs": ["依据真实资料撰写、总计不少于200字的阶段工作内容……", "下一步完成什么、哪些还需验证……"],
  "issues_paragraphs": ["需要核实的问题、实际已出现的故障与潜在风险分开写……", "针对问题制定可执行且可检验的整改措施……"],
  "teacher_opinion_paragraphs": ["指导教师审阅前的意见拟稿，总计不少于200字……"],
  "asset_fact_ids": ["FACT-001"],
  "asset_reference_ids": [],
  "asset_progress_ids": [],
  "evidence_notes": ["记录当前实际证据/尚待用户确认的事实"]
}
```

**这里所有文字都是字段说明而非实写内容，不能拿来生成交付 DOCX。** 实际题目/姓名/检查日期未有可靠依据时不得从前一个同学范本复制；`inspection_date` 未知时直接省略字段。

新增实际进展快照时，输入 `progress-import.json`：

```json
{
  "project_id": "真实项目稳定ID",
  "items": [
    {
      "id": "PROG-001",
      "as_of": "实际证据对应的YYYY-MM-DD",
      "category": "in_progress",
      "status": "draft",
      "description": "来自真实资料的阶段进展记录",
      "source": "证据所在文件及小节"
    }
  ]
}
```

实际运行后：
```bash
python scripts/project_assets.py merge --root "$PROJECT_ROOT" --kind progress --input "$WORKDIR/progress-import.json"
python scripts/project_assets.py compose --root "$PROJECT_ROOT" --draft "$WORKDIR/midterm-draft.json" --out "$WORKDIR/midterm-input.json"
```

已存在 ID 的更正要 `--replace --reason`；不可直接删除旧资产或默默覆盖。
