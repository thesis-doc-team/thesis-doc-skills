# 对照 thesis-midterm-check-write-v1.3 的形式迁移说明

**迁移原则**：学习的是 Skill 组织结构、模板保护、参考样本治理、自动检查和项目资产管理，不将中期检查表的栏目、文字状态与限制移植到开题报告中。

| 中期检查 Skill v1.3 的能力 | 本开题 Skill v4.0 的对应做法 | 需要保留的差异 |
|---|---|---|
| `SKILL.md` 0~7章节：边界/资产/官方/逆向/引用/流程/验收/索引 | `SKILL.md` 同序重构并且 README 直接路由 | 本文书是开题报告七项，不是进度/问题整改/教师意见三栏 |
| `assets/template-lock.json` 官方哈希、表格结构锁 | `assets/template-lock.json` + `assets/template.sha256` | 开题模板是正文2行1列表格，教师意见和签字区保留空白 |
| `assets/reference-samples/` SAMPLE A~D + manifest | 当前实收一份 SAMPLE-A 完整脱敏DOCX、清单、哈希及 README | 绝不假称有四个开题参考；历史对照仅以逆向文字规则保留 |
| `references/genre-reverse-engineering.md`+样本风格审计 | 增加同名逆向规则与 `sample-style-audit.json` | 样本的段落缩进异常不能作为新报告目标样式 |
| 共享 project-assets schema v1 + -vN | 继续共用 FACT/REF/schedule；每版DOCX+汇报+文献核验共三项 | 不共享中期 `compose` / Word 坐标 / 实际进展文稿 |
| `fill_midterm.py`+`validate_midterm.py` | 保留 `build_report.py` + 强化 `check_report.py` 缩进和文献检查 | 引文真上标、≥3000汉字、参考文献≥10项是开题专有门禁 |
| `render_visual.py`全页渲染并预警孤页 | 新增本地可运行 `render_visual.py` 与 `check_render.py` 协作 | 不沿用中期默认的3页上限；开题页数自然形成 |
| `intermediate-cleanup-policy.md` | 新增同用途文件并保留 marker 安全清理 | 不能清理其他 Skill 的临时区或文书历史版 |
| `templates/input.schema.json` + 执行汇报 | 增加七章 JSON schema、统一逐页报告 | 导师意见仍由教师本人填写，不生成冒充教师的评价 |

**原样保留的重要细节**：`opening-report-writer` skill name、原 `scripts/project_assets.py` 对应的 `.owned-by-opening-report-writer` 标记、官方 DOCX 原件二进制、共享数据 schema_version=1、`-vN` 版本纪律、引用标记 `[[cite:n]]` 以及原有生成 CLI；升级不要求历史项目重建资产库。
