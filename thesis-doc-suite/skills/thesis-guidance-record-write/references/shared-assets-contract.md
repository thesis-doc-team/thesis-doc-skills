# 与用户现有毕设文书 Skill 的共享资产协议

本 Skill 复用上传的`thesis-midterm-check-write v1.3`的项目级协议，与任务书/开题/技术文档等 Skill 指向**同一个`PROJECT_ROOT`**。`schema_version=1`，稳定项目ID、REF/FACT/PROG编号不另起号；文献库和周计划绝不重复创建。脚本`project_assets.py`是其兼容副本，修改了本Skill专用运行区与指导记录`compose`数据结构；共用操作`init/status/merge/workdir/cleanup/record-use`的原有意义不变。

| 文件 | 所有 Skill 公共规则 | 本 Skill 的职责 |
|---|---|---|
| `project.json` | 真实项目身份与可能的人员元数据 | 读取或填入已经确认的封面字段，不借用范本人名 |
| `facts.json` | 稳定 FACT-ID、来源和状态 | 技术内容选题、措辞与风险的依据 |
| `references.json` | 稳定 REF-ID、核验状态/URL | 已核验相关论文优先复用；本表不加独立引用栏 |
| `schedule.json` | 唯一周计划，`draft/confirmed` | 只作选题顺序参考，不虚构导师实际会面 |
| `progress.json` | 可选真实阶段快照 | 只有证据支持时补 PROG-ID；不可拿拟稿当真进度 |
| `activity.jsonl` | 所有变更与成品版本审计 | 仅视觉+结构检查结束后登记`doc_type=guidance` |

如发现旧资产与新证据冲突，先停下自动回写，说明差异；更新须显式`--replace --reason`，写入变更日志。不同 Skill 不得互删运行区，`.skill-tmp`的所有权标识必须校验。

如果项目使用`schema_version>1`，本脚本禁止覆盖/降级，应先审查迁移后再执行。


## 题目唯一（强制）

`project.json` 的 `name` 是项目正式题目，同一项目的全部文书题目必须与之一致。`compose`（或对应校验入口）按 NFKC＋去空白归一化强校验，不一致即报错并指出两处题目。确需变更题目时，先更新 `project.json` 并留下审计记录，再重新生成全部文书——不得各文书各写一个题目，也不得靠换名、加空格绕过。
