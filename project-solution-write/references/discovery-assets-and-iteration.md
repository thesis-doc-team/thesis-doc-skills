# 候选项目资产与版本管理

## 资产边界

项目推荐是**独立阶段**，每个候选维护稳定 ID，独立生成 `项目概览.md`、`项目概览.docx`、`项目概览.html` 三个相同内容的文件。初始版本 v1.0；内容变化 v1.1、v1.2；保留历史版本，版本之间不相互覆盖。每批 1～10 个新项目，不凑数。

```text
<WORKSPACE>/
├── discovery/
│   ├── profile.json                      # 已知的专业/技术/偏好/约束
│   ├── catalog.json                      # 项目 ID、状态、最新版本
│   ├── rejected-projects.json            # 用户拒绝过的项目特征
│   ├── history.jsonl                     # 推荐/拒绝/迭代/确认记录
│   └── .discovery-write.lock             # 排他锁，只在写入期间存在
├── projects/
│   └── PROJECT-0001/
│       ├── data/
│       │   ├── project.json              # 当前候选内容，唯一事实源
│       │   └── revisions/v1.0.json       # 不可变旧版快照
│       ├── versions/
│       │   └── v1.0/
│       │       ├── 项目概览.md
│       │       ├── 项目概览.docx
│       │       └── 项目概览.html
│       ├── project-assets/               # confirmed 后复用既有项目契约
│       └── deliverables/                # confirmed 后才正式生成
└── .skill-tmp/project-solution-write/    # 可清理运行区
```

Skill 安装目录只存规则/模板/代码，不保存用户资产。不同候选不可共用 ID；正式方案必须在**原候选项目目录**内开展，不能为改名项目新建身份，不能把其他项目事实串进来。

## 内容唯一事实源

`data/project.json` 与 `data/revisions/vN.json` 含同一套 `title/overview/features`。这三项是候选 MD/DOCX/HTML 的唯一正文来源，文件不得独立手工改出互相矛盾的内容。其他状态、签名、专业、用户偏好只保存在内部元数据，不泄露到外显三份内容。

## 状态机

- `candidate`：新推荐未反馈。
- `rejected`：用户明确“不喜欢/不要这个”。后续默认排除该 ID 及语义高度近似的候选，不删除其版本资产。不能仅因未回复就标拒绝。
- `interested`：用户表示感兴趣但仍想补功能。保持同 ID，持续迭代；**不等于正式确认**。
- `confirmed`：用户明确选定最终题目和核心功能后才设置。正式文档由旧 Skill 的设计冻结、分批生成、质量检查完成。

变更后的状态写入 `catalog.json` 和候选 `data/project.json`，在 `history.jsonl` 留痕；拒绝追加 `rejected-projects.json`。重启或换 Agent 必须首先读持久资产。已拒绝项目再次考虑必须用户明确要求恢复，不能因重新命名悄悄重推。

## 去重规则

对比**既有全部候选（包括 rejected）和当前批次**：标准化题目、应用场景、核心功能组合与实现机制。简单更改“智能/基于 STM32/系统/终端”等词不算新题目。`discovery_registry.py` 对标题和功能进行保守的词面/场景相似度初筛；Agent 还必须判断“同场景同功能不同表述”的语义重复。脚本不能保证理解所有中文同义改写，不得宣传成百分之百语义去重。用户明确恢复拒绝项目时应复用原 ID，不创建新 ID。

## 功能迭代

用户明确提出“增加 RFID 身份验证”则视为本轮功能变更授权；“我觉得功能还应该丰富一点”属于**探索请求**，先由 Agent 给出适量符合原范围的可选功能，待用户选定后再 `revise` 落盘。保留已有功能，除非用户明确删除或替换。更名不改变 ID，修订记录 `change_summary`。同一次迭代三个格式必须基于新快照同步生成，失败不发布不完整三件套。

## 与正式方案无冲突

正式项目已有 `project-assets/project.json/facts.json/references.json/requirements.json/decisions.json` 时直接按旧规则读取。不改变其 schema、不重新初始化。首次从 candidate 进入 confirmed 后，可用旧的 `project_workspace.py init --root projects/PROJECT-0001 --project-id PROJECT-0001 --title ...` 创建正式项目身份；随后由旧流程从已确认功能定义生成“介绍 MD/HTML + 工程实施 MD”。**候选的 DOCX 只是选题介绍；不等于正式实施方案 DOCX。**
