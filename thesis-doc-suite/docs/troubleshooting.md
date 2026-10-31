# 常见问题排查（Troubleshooting）

每条给出**症状 → 原因 → 处理**。先跑两条自检命令定位问题：

```bash
python scripts\check_env.py --root "E:\thesis-work\env-monitor" --skill <目标skill名>
python scripts\verify_plugin.py
```

---

## 1. Skill 没有加载 / 找不到命令

**症状**：输入 `/thesis-doc-suite:` 没有补全，或提示未知命令。

**原因**：插件未加载；或加载的目录不对（应指向含 `.claude-plugin\plugin.json` 的 `thesis-doc-suite\` 目录）。

**处理**：
1. 用 `claude --plugin-dir E:\Code\thesis-doc-skills\thesis-doc-suite` 重新启动（注意是 `thesis-doc-suite\` 这一层，不是它的上层）。
2. 或确认 marketplace 安装成功：`/plugin` 面板查看是否列出 `thesis-doc-suite`。
3. 仍不行：`python scripts\verify_plugin.py` 检查 `plugin.json` 与 9 个 `SKILL.md` 的 frontmatter（`name` 必须与目录名一致）。修复后重新加载（更新插件后需重新加载才生效）。

## 2. 缺少官方模板 / 模板哈希不符

**症状**：执行报 `模板哈希不符` / `template-lock.json 校验 FAIL` / `官方模板不是可识别结构`。

**原因**：内置 `assets/official-*-template.docx` 被改动或替换过；或你提供了学校新版模板，结构与旧锁定坐标不同。

**处理**：
- 不要手改内置模板。用 `python scripts\verify_plugin.py` 确认哪些模板失配；从插件发行包恢复原件。
- 确实是学校**新版**模板：把它交给对应 Skill 说明"这是新官方模板"，Skill 会做只读结构审计、重建填写坐标并更新锁文件；在此之前填充脚本会拒绝"强灌"（这是保护，不是故障）。
- 只有图片/PDF 没有可编辑 DOCX：无法保证"原 DOCX 保真"，需提供正确的官方 DOCX。

## 3. 参考文献核验失败 / 被拒绝

**症状**：报 `文献未经实际核验，不得使用` / `verified=true 的文献必须记录核验日期` / `缺少字段`。

**原因**：条目缺必填字段（citation/source_url/source_type/verified）；标了 `verified=true` 却没有 `checked_at`；或引用了不存在的 REF-ID。

**处理**：到知网/万方/维普/期刊官网/DOI 等可核验来源补齐元数据与核验日期；确实查不到就保留 `verified=false` 并在执行汇报披露——**绝不伪造元数据**。CSDN 等博客请标 `source_type=web`，不能当期刊论文。

## 4. LibreOffice 缺失 / 渲染失败

**症状**：`render_visual.py` 报找不到 soffice；执行汇报写"截图验证分析未完成"。

**原因**：未安装 LibreOffice（或不在 PATH）。

**处理**：安装 LibreOffice（免费）后重试；或提供本机 Word/WPS 的等价渲染方式。无法渲染时 Skill 会如实报告"未完成视觉验收"——此时请务必人工逐页检查排版后再提交。**不能把"脚本无报错"当视觉检查通过。**

## 5. "WPS 已验证"能不能写？

**症状**：想向学校说明文档已在 WPS 检查。

**处理**：只有**真正用 WPS 客户端打开过**成品并检查，才能写"WPS 已验证"；只用 LibreOffice/兼容渲染器检查过，应写"未在 WPS 客户端实测，需进一步复核"。Skill 的执行汇报会照此如实标注，请勿改写成已验证。

## 6. Python 依赖缺失

**症状**：`ModuleNotFoundError: No module named 'docx' / 'fitz' / 'markdown_it' / 'bs4'`。

**处理**：

```bash
python -m pip install python-docx lxml PyMuPDF markdown-it-py beautifulsoup4
```

或进入对应 Skill 目录 `python -m pip install -r requirements.txt`。Windows 上若 `python` 不是有效命令，先安装 Python 3.10+ 并加入 PATH（`py --version` 验证）。

## 7. 运行区清理失败 / 残留文件

**症状**：执行汇报写"清理未完成，残留路径 …"；或报 `目录缺少合法所有权标记，禁止删除`。

**原因**：文件被占用（预览器/杀毒软件锁住 PNG）；或试图清理不属于本 Skill 的目录（所有权保护）。

**处理**：关闭占用文件的程序后手动删除汇报中列出的**残留路径**（仅限 `.skill-tmp\<skill-name>\<run-id>\` 内）。所有权保护是刻意设计——**它拒绝删除共享资产、成品、官方模板和其他 Skill 的运行区**，不要绕过它扩大删除范围。

## 8. 成品覆盖保护（-vN）

**症状**：生成时提示目标 `-vN` 已存在、拒绝覆盖。

**原因**：同一版本号的成品已存在（历史版本永不覆盖）。

**处理**：正常现象。Skill 会自动改用 `-v(N+1)`；如需替换旧版，请确认旧版可作废后再处理（默认永远保留历史版本更安全）。

## 9. project_id 不匹配 / 拒绝合并

**症状**：报 `该目录已有其他项目资产；不可改用新 project_id 覆盖` / `跨项目资产拒绝写入`。

**原因**：给这个项目目录用了另一个 project_id，或把 A 项目的资产往 B 项目合并（防串项目保护）。

**处理**：确认 `<PROJECT_ROOT>` 是否指对；同一项目请沿用 `project-assets\project.json` 里的原 project_id（`python core\asset-management\project_assets.py status --root ...` 查看）。换新项目请用**新目录**重新 init，不要复用旧项目目录。

## 10. GBK / Unicode 编码报错（Windows 中文环境）

**症状**：`UnicodeDecodeError: 'gbk' codec can't decode byte …`。

**原因**：Windows 中文系统默认 GBK，读写 UTF-8 文件时未显式指定编码（常见于自写脚本或旧版测试）。

**处理**：插件内脚本已统一 UTF-8。若你在自写脚本里读写项目资产/JSON，请显式 `open(..., encoding='utf-8')` 或 `Path.read_text(encoding='utf-8')`。也可以临时设置环境变量 `PYTHONUTF8=1` 再运行。仍失败请把完整报错贴给 Claude Code 排查。

## 11. 权限问题（写入 / 符号链接）

**症状**：`PermissionError` 写不进项目目录；或安全测试 `test_symlinked_workbase_blocked` 显示 skipped。

**处理**：
- 写权限：确认 `<PROJECT_ROOT>` 可写（不要放在 Program Files 等受保护位置）；只读介质请换可写目录。
- 符号链接测试被跳过是**正常现象**：Windows 默认禁止普通用户创建符号链接（需管理员权限或开发者模式），跳过不代表功能失效；运行区清理的越界保护依然有效。

## 12. 内容被判定"证据不足 / 待确认"

**症状**：成品里出现"待确认"标注；执行汇报列了缺口清单。

**原因**：资料本身没有覆盖该部分，或资料之间矛盾（如手册说已实现、代码里没有）。

**处理**：这是**如实披露**，不是缺陷。补充对应资料/证据后重新生成（-v2）；Skill 绝不以猜测填补——宁可留"待确认"，也不编造功能、数据或成果。

## 13. 生成的文书能否直接提交？

**症状**：拿到 DOCX 后不确定下一步。

**处理**：所有 Word 文书都是**供指导教师审定的拟稿**——请先自行核对内容（课题名、任务、进度、文献），把教师意见栏的拟稿交导师审定，签名/日期/评价由导师本人处理；封面个人信息如有留白请补填。最终内容验收由你和指导教师完成。

---

仍未解决：把 `check_env.py` 与 `verify_plugin.py` 的完整输出、执行汇报中的 WARN/FAIL 项一并交给 Claude Code 分析；插件本身的问题可在项目仓库提 issue。
