# Skill 职责边界与关系规则（跨 Skill 契约）

> 本文是六个业务 Skill 的职责边界、互操作关系与扩展规范。各 Skill 的详细执行规则以其 SKILL.md 为准；本文只约束"谁负责什么、谁能复用什么、谁不能越界"。

## 1. 六个业务 Skill 的独立职责

| Skill | 唯一主交付 | 职责要点 | 明确不做 |
|---|---|---|---|
| `project-technical-doc` | `<项目名>-技术文档.md` + `<项目名>_用户展示.html` | 只读理解真实项目资料/源码，提炼带证据的技术事实（FACT-xxx 主要产出者），MD→HTML 单向派生 | 不编写任何毕业设计表格文书 |
| `thesis-taskbook-write` | `<课题简称>-毕业设计任务书-vN.docx` | 官方任务书模板原位填充；任务化改写；≥10 篇核验文献；周计划拟定 | 不生成开题报告/论文/HTML |
| `opening-report-writer` | `<课题简称>-毕业设计开题报告-vN.docx` | 七项内容论证；真上标引文；进度计划与共享周计划一致 | 不把未完成研究写成已完成；不生成其他文书 |
| `literature-review-write` | `<课题简称>-文献综述-vN.docx` | 按研究问题组织文献比较与评述；真实引文与证据 | 不做技术介绍堆砌；不生成其他文书 |
| `thesis-guidance-record-write` | `<课题简称>-指导记录-vN.docx` | ≥8 次指导主题拟稿；问题→整改编号严格配对；评价/签名栏留空 | 不虚构指导会议/教师意见/日期/签名 |
| `thesis-midterm-check-write` | `<课题简称>-中期检查记录表-vN.docx` | 三栏各≥200字；问题与整改分条编号一一对应；教师意见拟稿 | 不凭空编造已完成成果；不生成其他文书 |

**通用边界**：任何业务 Skill 都**禁止跨越边界生成其他业务文书**；用户一句话混用文书名称时，以本轮指定的官方模板与明确交付类型为准，冲突时说明而不是偷换模板。

## 2. 复用关系（共享资产，而非固定顺序）

- `project-technical-doc` 是项目技术事实（FACT-xxx）的主要提炼者；其他 Skill 按稳定 ID 复用其事实与状态限定。
- `thesis-taskbook-write` 与 `opening-report-writer` 共用技术事实与周计划（schedule.json）。
- `literature-review-write` 与 `opening-report-writer` 共享参考文献（REF-xxx）。
- `thesis-midterm-check-write` 与 `thesis-guidance-record-write` 读取项目计划与实际进展（progress.json）。

**只有确实必要的输入才设为硬性前置条件**（如 Word 文书需要官方模板与技术资料）。缺非必要资料时允许**降级执行**并在执行汇报中明确说明影响（例如：缺已核验文献时可先交标注"待补文献"的草稿，不得伪造）。这些关系**不意味着固定执行顺序**；除"技术资料是多数文书的事实输入"外，各 Skill 可独立调用、独立验收、独立失败。

## 3. 数据归属

| 资产 | 主要贡献者 | 其他 Skill 的权利 |
|---|---|---|
| facts.json（FACT-xxx） | project-technical-doc | 读取、引用稳定 ID；有证据时可补充缺失条目 |
| references.json（REF-xxx） | 各文书 Skill（按需增补） | 全体复用；增补先核验再入库 |
| schedule.json | thesis-taskbook-write（拟定基线） | 读取复用；有依据可 `--replace --reason` 更新 |
| progress.json（PROG-xxx） | thesis-midterm-check-write（扩展） | thesis-guidance-record-write 读取；有证据可补充 |
| project.json metadata | 用户确认后写入 | 读取个人信息填充封面，不从范本继承 |

所有变更遵守 `core/contracts/shared-project-assets-contract.md` 第 3 节（先读后写、不静默覆盖、审计留痕）。

## 4. 添加第七个 Skill（扩展规范）

1. 在 `skills/<new-skill-name>/` 新建独立目录，`SKILL.md` frontmatter 的 `name` 必须与目录名一致，`description` 写清触发场景与边界；文档生成类 Skill 建议加 `disable-model-invocation: true`（仅显式调用）。
2. 只复用所需公共能力：项目资产协议（`core/asset-management/project_assets.py` 或自备协议兼容副本）、模板保护（`core/template-protection/template_guard.py`）、写作规范（`core/quality-check/shared-writing-rules.md`）。**不要复制其他 Skill 的执行规则**。
3. 在 `core/contracts/skill-catalog.json` 注册元数据（README 与网站据此同步）。
4. 新模板：提供官方原件只读副本 + `assets/template-lock.json`（SHA-256 与结构审计）+ 填充/验证脚本，绝不修改官方原件。
5. 自带 `tests/` 最小回归（模板哈希、结构保护、资产协议兼容），并保持其他 Skill 零改动。
6. 更新 README、docs/skill-catalog.md 与 site/ 的功能目录（三者内容源自 skill-catalog.json，禁止三套说法）。
