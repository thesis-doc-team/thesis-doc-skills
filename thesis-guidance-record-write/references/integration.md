# 与中期检查、任务书、开题报告、技术文档 Skill 的合并方式

1. 顶层所有 Skill 共同读取一个`<PROJECT_ROOT>/project-assets`，只通过`project_id`确认是同一项目。
2. 让各生成 Skill 使用统一`project_assets.py`版本；若暂时各自打包兼容副本，基础字段与命令保持schema=1，运行区`WORK_BASE`和所有权标记**各Skill独立**。
3. 技术文档 Skill 负责维护技术事实及原始材料；任务书 Skill 维护唯一周计划；中期 Skill 维护有证据的进展；本 Skill 仅维护指导拟稿并引用上述信息，不改变其他 Skill 的成品。
4. 参考文献 REF-ID 复用，不重编来源编号。即使报告不显示参考文献条目，执行报告仍应列出真正使用过的 REF-ID。
5. `guidance`是文书类型，不是`midterm`或`proposal`。不要将本 Skill 的`compose`传入其他文书的填充脚本。
6. 样本、测试数据在安装目录中只读，不接触用户项目资产；技术文本、身份信息、正式Word只存项目根下相应目录。
