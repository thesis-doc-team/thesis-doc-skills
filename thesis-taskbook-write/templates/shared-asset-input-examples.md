# 共享资产输入结构参考（仅字段示意，全部内容不得作为真实项目资料）

**提示：以下数据全部是占位示意，不是已核实的论文、周计划或项目信息。不能直接用于提交的任务书。**

## 项目级周计划：`schedule-proposal.json`

```json
{
  "project_id": "PROJECT-001",
  "plan": {
    "id": "PLAN-001",
    "status": "draft",
    "total_weeks": 4,
    "stages": [
      {"id":"STAGE-001", "from_week":1, "to_week":2, "task":"示意阶段：文献调研"},
      {"id":"STAGE-002", "from_week":3, "to_week":4, "task":"示意阶段：技术设计"}
    ]
  }
}
```

`total_weeks`、起止日期、分段应当来自**当次项目/官方要求**。本例的 4 周不是任何学校的真实毕业时间。

## 新增文献：`verified-references.json`

```json
{
  "project_id": "PROJECT-001",
  "items": [{
    "id": "REF-001",
    "citation": "示例作者. 示例论文名[J]. 示例期刊, 2025.",
    "source_url": "https://example.org/not-a-real-reference",
    "source_type": "journal",
    "verified": false,
    "checked_at": null,
    "tags": ["示意主题"],
    "project_relevance": "说明与项目的关联"
  }]
}
```

此条文献未核验，`compose` **不会选入**。

## 技术事实：`facts-proposal.json`

```json
{
  "project_id":"PROJECT-001",
  "items":[{
    "id":"FACT-001",
    "statement":"示例描述，不构成任何事实",
    "source":"技术文档的具体文件名及章节/行号（需真实填写）",
    "status":"unverified"
  }]
}
```

## 本次任务书特有草稿：`taskbook-draft.json`

```json
{
  "project_id":"PROJECT-001",
  "title":"用户提供或根据项目事实拟定的题目",
  "thesis_content":["根据项目技术文档重写的毕业设计任务内容"],
  "issuer_opinion":"此处应当根据当次项目拟定至少五十字的任务下达人意见，并明确需要指导教师复核后确认，不能冒充已经审批的真实意见。",
  "selected_reference_ids":["REF-001", "REF-002"]
}
```

在真实生成时 `selected_reference_ids` 应当列出**至少 10 条真实核验过、适合本项目的文献**，否则构建工具会拒绝生成正式输入。它决定该份任务书的 `[1]...[N]` 局部引用顺序；下一份开题报告可以选取不同子集与局部顺序，而不修改共享文献库的稳定 ID。
