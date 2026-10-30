# 与 thesis-taskbook-write-v1.1 的项目资产接口兼容说明

## 一份真相，多份文书

本 Skill **直接复用了任务书 Skill 的共享契约 schema_version=1**，本包 `references/shared-project-assets-contract.md` 是其原始契约副本。可并行安装两个 Skill；均指向真实 `<PROJECT_ROOT>`，读写同一 `project-assets/` 文件组。不能把 `project-assets` 放到任何 Skill 的安装目录。

| 文件 | 任务书 Skill | 文献综述 Skill | 冲突规则 |
|---|---|---|---|
| project.json | 创建并维护基本项 | 读取/必要时增补确认字段 | project_id 不符拒绝 |
| facts.json | 提取任务、模块事实 | 检查文献论述中的项目事实 | 更改已有事实须明确证据和理由 |
| references.json | 引用与核验入库 | 复用同一 REF-ID、新增经查实文献 | 稳定 ID 不变，文内序号独立 |
| schedule.json | 维护周计划基线 | 默认只读，不为综述另造周计划 | 不自动改计划 |
| activity.jsonl | 任务书版本、更新审计 | 综述版本/引用使用审计 | append-only，锁及原子写 |

`project_assets.py` 从任务书 v1.1 的实现移植，保持 `init/status/merge/workdir/cleanup/record-use` 的共享读写逻辑；**仅把运行区命名及所有权标记改为 literature-review-write**，并不暴露针对任务书 JSON 的 `compose` 命令。文献综述使用独立的 `compose_review.py`，其写入的是**本轮临时输入文件**，不是另一份共享文献库。

## 核验的共享条目格式

```json
{
  "project_id": "<真实项目ID>",
  "items": [
    {
      "id": "REF-XXX",
      "citation": "<实际查证的著录字符串>",
      "source_url": "https://<真实论文页面URL>",
      "source_type": "journal",
      "verified": true,
      "checked_at": "<实际核验日期ISO8601>",
      "project_relevance": "<真实论文对当前课题的支持>",
      "tags": ["<技术主题>"]
    }
  ]
}
```

这是**字段说明**，不是可作为真实文献导入的例子。绝对不能把上面的占位项用于正式项目。`--replace --reason` 只用于有证据的更正。不同 Skill 的正文格式不应污染共享著录事实。

## 交付版本与中间文件

正式综述每版写入 `<PROJECT_ROOT>/deliverables/literature-review/`；任务书仍写 `deliverables/taskbook/`。本轮渲染截图、临时数据输入、审计 JSON、调试文档放 `.skill-tmp/literature-review-write/<run-id>/`。清理必须使用本 Skill 自己的 marker，不能删除 `.skill-tmp/thesis-taskbook-write/` 或任意外部目录。
