# 测试验证报告

- 日期：2026-10-30 / 2026-10-31
- 原则：**只记录实际运行过的结果**。未实际运行的项目一律标注「未测试」，不做通过声称。
- 运行环境：Windows 11 Home China（10.0.26200）；Python 3.12（用户级安装）；依赖 python-docx 1.x / lxml / PyMuPDF / markdown-it-py / beautifulsoup4；**LibreOffice 未安装**；WPS 未验证。

---

## 1. 总测试套件 `tests/run_all.py` — **PASS（19/19）**

执行命令：`python tests/run_all.py --json tests/last-run.json`（2026-10-31 复跑，与首跑结论一致）

| # | 项目 | 结果 | 实测输出摘要 |
|---|---|---|---|
| 1 | plugin-structure（`scripts/verify_plugin.py`） | PASS | SUMMARY: PASS=49 WARN=0 FAIL=0（清单/目录/9 个 Skill frontmatter/内部引用/模板锁/绝对路径 lint） |
| 2 | asset-consistency（7 份 project_assets 实现 × 行为契约） | PASS | OK（56 用例） |
| 3 | asset-isolation（跨 Skill 共享/隔离/防静默覆盖/清理越界） | PASS | OK（4 用例） |
| 4 | doc-consistency（README/网站/目录 命令一致性、无外链） | PASS | OK（6 用例） |
| 5 | techdoc: pipeline | PASS | 原文一致、离线页面、越界拦截、重复生成不覆盖 |
| 6 | techdoc: project-assets | PASS | OK |
| 7 | taskbook: pipeline | PASS | OK |
| 8 | taskbook: reference-samples | PASS | OK |
| 9 | taskbook: shared-assets | PASS | OK（skipped=1：symlink 用例在无权限环境跳过，见 §3） |
| 10 | opening: anonymized-example | PASS | OK |
| 11 | opening: guards | PASS | OK |
| 12 | opening: pipeline | PASS | OK |
| 13 | opening: project-assets | PASS | OK |
| 14 | opening: upgraded-contract | PASS | OK |
| 15 | lit-review: smoke | PASS | 隔离资产 init/merge/compose/fill/validate/record-use/cleanup；模板哈希与产出哈希断言通过 |
| 16 | lit-review: regression | PASS | 模板哈希锁定 / 不覆盖 / 引文上标 / 教师栏固定 / 拒绝未核验引文 |
| 17 | guidance: pipeline | PASS | OK |
| 18 | midterm: pipeline | PASS | OK |
| 19 | midterm: shared-assets | PASS | OK |

> 注：上述每项均为子进程实际执行、按退出码判定；报告文件 `tests/last-run.json` 保留逐项尾部输出。

## 2. 官方插件校验 `claude plugin validate` — **PASS**

- 首次运行：**FAIL（1 项）** — `skills/check-project/SKILL.md` frontmatter 的 `argument-hint: [项目根目录] [目标Skill名称]` 是非法 YAML（两个流式序列相邻）。
- 修复：`check-project`/`help`/`init-project` 三个管理 Skill 的 `argument-hint` 值加引号（`help` 原写法解析为列表而非字符串，一并修正）。
- 复跑：`✔ Validation passed`（清单 + 全部 Skill frontmatter）。**该修复同时消除了运行期 frontmatter 被静默丢弃的风险。**

## 3. 打包与内容审计 — **PASS**

- `python scripts/package_plugin.py` → `E:\Code\thesis-doc-skills\dist\thesis-doc-suite-0.1.0.zip`（253 文件，约 2.8 MB；打包前强制 verify，PASS=49）。
- SHA256：`d33b6def8123f6b93e3c11e5d6dbde8318807ed656689b7fa9d7e7469d4bb664`（frontmatter 修复后复打的最终包）。
- 内容扫描（实际执行）：无 `__pycache__`/`.skill-tmp`/`.pyc`/`dist`/`.git` 条目；关键词扫描（QiDeng / `Users\` / `C:\Users` / api_key / token= / password）命中 2 处，经逐一查看均为良性——`plugin.json` 的作者署名（预期元数据）、`verify_plugin.py` 的绝对路径 lint 正则常量。**无个人隐私、凭据、缓存或临时运行文件。**

## 4. 基线对比（迁移前原件测试）

迁移前对原始 6 个 Skill 实测回归，发现 **3 处原有缺陷**（原工程现状，未改动原件）：

| 原有缺陷 | 表现 | 迁移副本处置 |
|---|---|---|
| guidance `tests/test_pipeline.py` 缺省编码 | zh-CN Windows 下 3 处 `UnicodeDecodeError`（GBK） | 显式 `encoding='utf-8'`，已 PASS |
| taskbook symlink 用例 | 非管理员 Windows 报 `OSError` | 无权限时 `skipTest`，已 PASS（skipped=1） |
| midterm `tests/test_shared_assets.py` 导入 | 以脚本运行时 `ModuleNotFoundError: tests` | 补 `sys.path`，已 PASS |

另做防御性加固：全部 Skill 脚本/测试 `subprocess.run(text=True)` 补 `encoding="utf-8", errors="replace"`（16 处），消除 GBK 控制台解码中断风险（含 2 处我方引入的重复关键字参数错误，已修复并复跑确认）。

## 5. 未测试项（如实标注，**不计入通过**）

| 项目 | 状态 | 原因 / 后续 |
|---|---|---|
| LibreOffice（soffice）DOCX→PDF 渲染 + `render_visual.py` 逐页截图 | **未测试** | LibreOffice 未安装；Skill 内截图验证分析三步门禁在实际生成时执行 |
| WPS 打开/兼容性 | **未测试** | 未在装有 WPS 的机器验证；全部文档按约定**不做 WPS 兼容声明** |
| 浏览器目视验收 `site/index.html` | **未测试** | 无浏览器自动化；已完成静态检查（无 CDN 外链、9 命令齐全、锚点齐备、复制按钮脚本在位） |
| `claude --plugin-dir` 实际加载 + 9 条 `/thesis-doc-suite:…` 端到端调用 | **未测试** | 需交互式会话逐条实测；结构与 frontmatter 已过官方 `plugin validate` 与 49 项自检 |
| Word 成品逐页视觉效果（字体/缩进/分页） | **未测试** | python-docx 结构检查已 PASS；视觉效果依赖渲染链路（上表第 1 行） |

## 6. 结论

- **自动化测试：PASS**（19/19 套件 + 官方 validate + 打包审计）。
- **渲染链路与浏览器目视：未测试**，需在装有 LibreOffice/WPS 的环境按 `docs/prerequisites.md` 补验。
- WARN 项：无（本报告范围内）。FAIL 项：无（最终状态；过程中发现的 1 个 frontmatter 缺陷与 3 个原有缺陷均已修复并复测）。
