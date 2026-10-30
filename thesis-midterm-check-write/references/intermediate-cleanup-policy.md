# 临时产物清理（硬性）

临时工作只允许在 `<PROJECT_ROOT>/.skill-tmp/thesis-midterm-check-write/<run-id>/` 内进行，`project_assets.py workdir` 创建时写入 `.owned-by-thesis-midterm-check-write`。`cleanup --run-id` 会检查 run_id 规则、祖先目录、不允许符号链接的父路径、所有权标记；只删一个本轮有权目录，不能任意 `rm -rf` 项目根目录，也不能清理 `.skill-tmp/thesis-taskbook-write/`。

中间：`draft/input.json`、临时 DOCX、模板检查 JSON、渲染 PNG、调试 PDF、对照截图/错误日志。必须在成功或失败结束时清除；提前把需要的失败摘要/最终文档持久化后再清理。

永久：用户原始技术资料、官方模板、范本、最终 DOCX、`project-assets/` 的 `project/facts/references/schedule/progress/activity`、经用户要求持久化的正式执行报告。保护它们不被清理脚本触碰。

使用 try/finally：建 workdir → 执行 → 完成审计/写报告 → finally cleanup。途中出错也执行 cleanup；清理失败不扩大范围，并向用户解释异常。
