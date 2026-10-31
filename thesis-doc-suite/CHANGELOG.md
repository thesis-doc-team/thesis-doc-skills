# Changelog

本文件记录 Thesis Doc Suite（`thesis-doc-suite`）插件的版本变化。插件语义化版本与各 Skill 自身版本独立（见 `core/contracts/skill-catalog.json`）。

## 0.1.0 — 2026-10-30

首次插件化发布：把 6 个独立的毕业设计文书 Skill 整合为一个可安装的 Claude Code 插件「Thesis Doc Suite Taru」，并建立统一的项目资产与质量基础设施。

### 迁移（原有能力保留）

| Skill | 命令 | Skill 版本 | 迁移状态 |
|---|---|---|---|
| `project-technical-doc` | `/thesis-doc-suite:project-technical-doc` | 5.2.0 | 完整迁移 |
| `thesis-taskbook-write` | `/thesis-doc-suite:thesis-taskbook-write` | 1.2.2 | 完整迁移 |
| `opening-report-writer` | `/thesis-doc-suite:opening-report-writer` | 4.1.0 | 完整迁移 |
| `literature-review-write` | `/thesis-doc-suite:literature-review-write` | 3.2.1 | 完整迁移 |
| `thesis-guidance-record-write` | `/thesis-doc-suite:thesis-guidance-record-write` | 1.2.0 | 完整迁移 |
| `thesis-midterm-check-write` | `/thesis-doc-suite:thesis-midterm-check-write` | 1.3.2 | 完整迁移 |

迁移方式为**复制迁移**：原始 Skill 目录未做任何修改（git 状态可证），迁移副本位于 `skills/`，原工程保留作回退依据。详见 `docs/migration-report.md`。

### 新增

- **统一共享资产协议**：`core/contracts/shared-project-assets-contract.md`（schema_version=1），统一 4 种原契约变体；`core/asset-management/project_assets.py` 规范参考实现。
- **公共基础设施**：`core/reference-management/`（文献真实性与 REF-xxx 规范）、`core/quality-check/`（教师意见五要素链、实质性分页门禁、截图验证分析三步）、`core/template-protection/template_guard.py`（模板哈希锁定校验）。
- **3 个管理 Skill**：`init-project`（初始化项目资产包）、`check-project`（PASS/WARN/BLOCK 前置检查）、`help`（使用导航）。
- **插件级脚本**：`scripts/check_env.py`（环境/模板/资产检查）、`scripts/verify_plugin.py`（插件结构与一致性自检）、`scripts/package_plugin.py`（ZIP 打包）。
- **测试体系**：`tests/run_all.py` 汇总 19 项（4 项插件级 + 15 项 Skill 回归），含跨 Skill 资产共享/隔离行为测试与 README/网站/目录一致性测试。
- **文档与网站**：`README.md`、`docs/`（快速开始、使用手册、架构、资产管理、Skill 目录、环境依赖、问题排查）、迁移报告与测试报告、`examples/demo-project/`（合成示例）、`site/`（离线介绍网站）。
- 本地 marketplace 清单（仓库根 `.claude-plugin/marketplace.json`）。

### 修复（仅修复迁移副本，原工程未改动）

- `thesis-guidance-record-write` 测试：`read_text()/write_text()` 缺省编码在 zh-CN Windows 下按 GBK 解码导致 3 处 `UnicodeDecodeError` → 显式 `encoding='utf-8'`。
- `thesis-taskbook-write` 测试：symlink 用例在非管理员 Windows 上 `OSError` → 无法创建符号链接时跳过（`skipTest`）。
- `thesis-midterm-check-write` 测试：`test_shared_assets.py` 以脚本方式运行时 `import tests.test_pipeline` 失败 → 补 `sys.path` 修正。
- 全部 Skill 脚本/测试中的 `subprocess.run(text=True)` 补 `encoding='utf-8', errors='replace'`（16 处），消除 Windows GBK 控制台解码中断风险。

### 已知限制

- LibreOffice 渲染与逐页截图链路未在本机实测（LibreOffice 未安装），相关验收项标注「未测试」，见 `docs/test-report.md`。
- 未实测 WPS 兼容性，文档中不做 WPS 兼容声明。
- 官方模板当前锁定塔里木大学版本；其他院校模板需另行提供并重建 `template-lock.json`。
