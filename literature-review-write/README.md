# literature-review-write

**唯一文书：塔里木大学毕业论文（设计）文献综述 DOCX。**

基于用户最新提供的官方空白 Word 模板开发；包内复制官方原件，不修改源文件。参考范本（`examples/`）已去除原学生个人信息，**仅用于风格参考**，有明确的旧版引文错误提示。

与 `thesis-taskbook-write-v1.1` 共享同一个 `project-assets/` 事实/参考文献/周计划/记录机制；编写文献综述时周计划只读，不另建资产库。运行区单独隔离，最后清理本轮。

## 文件结构

- `SKILL.md`：核心路由、写作及 Word 操作规则（Claude/Codex 可直接读）
- `assets/official-literature-review-template.docx`：**官方空白原件副本**
- `examples/anonymized-style-reference.docx`：最早范本去个人标识参考
- `references/`：逆向写作规则、引用核验、项目共享契约、跨 Skill 接口、质量门禁
- `scripts/project_assets.py`：继承任务书 v1.1 共享资产 schema；独立运行区
- `scripts/inspect_template.py`：模板只读盘点
- `scripts/compose_review.py`：按共享 REF-ID 组装本次文书 JSON
- `scripts/fill_review.py`：在原官方 DOCX 原位填写
- `scripts/validate_review.py`：不变区、字数、上标、引用一致性验证
- `templates/review-draft.schema.json`：本轮草稿结构
- `tests/smoke_test.py`：在隔离虚拟项目中运行生成、验证、共享资产清理，不影响真实项目

## 安装

将最外层 `literature-review-write-v3.0/` 目录放在 Claude Code 的 Skills 目录或 Codex 的 Skills 目录即可。具体触发方式取决于你当前使用的客户端设置；也可直接要求 Agent “读取 `literature-review-write-v3.0/SKILL.md` 并执行”。

**重要**：Skill 安装目录不是项目数据目录，不允许把论文或个人数据放到本 Skill 的 `examples/` 和 `assets/`。

## 版本边界

这是**可安装并带脚本的 Skill**，不包含当前胡杨林项目的正文或已核验参考文献数据。只有运行时读取当前项目技术文档和共享数据才能生成实际论文综述。`tests/` 的数据仅用于代码完整性测试，绝不能用作真实文献。
