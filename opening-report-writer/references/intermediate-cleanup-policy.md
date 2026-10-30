# 中间文件清理与版本保护（硬规则）

所有本轮临时数据只允许进入 `<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/`，必须通过 `scripts/project_assets.py workdir` 建目录，产生 `.owned-by-opening-report-writer` 所有权标记。禁止把 Skill 安装目录、`deliverables/`、`project-assets/` 当临时区。

**临时项**：过程 `报告内容.json`、草稿、检索脚本、论文 PDF 缓存、屏幕截图、渲染 PDF、测试结果、临时修复 docx；成功失败均需清理。

**永久项**：用户上传技术文档与源码、官方模板、已脱敏范本及 Skill 包、`project-assets` 的所有资产、`deliverables/opening-report/` 的历史 `-vN` 正式文书、已按要求保留的执行汇报和核验台账、其他 Skill 的成果。不得重命名/删除/覆盖。

**正确顺序**：`status → workdir → 准备事实与文献 → build → check → render → 逐页视觉审查 → 写执行汇报及核验台账 → 通过后 record-use → finally cleanup`。记录本轮失败原因与引用证据后清理；清理命令会检查 run-id、目录合法性及标记，不能代替成 `rm -rf` 项目目录。出错也尝试清理，仅操作自己拥有的目录，失败则明确告知路径。

对 `deliverables/opening-report/` 只清理**本轮误放入的非成品中间件**，历史已存在的文件未经授权不得批量删除。生成成品版本自动递增，三项按同一 `-vN` 成组，确认已存在路径则拒绝覆盖并改用下个版本。
