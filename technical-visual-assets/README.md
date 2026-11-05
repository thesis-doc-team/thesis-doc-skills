# technical-visual-assets v1.4.1

**正交连线** · **中英文图题** · **原生 VSDX** · **表格水平/垂直居中** · **完全离线** · **正式技术 MD 唯一事实源** · **用户自行上传硬件实物图** · **A4 Word 版心** · **黑白 Visio 风格**

详见 `SKILL.md`：

- 资源归档/模块上传清单：`scripts/md_pipeline.py scan / sync / module-list / upload-photo / attach-layout / report`
- 正交通信图：`scripts/visio_diagram.py` 生成 `.svg + .drawio + .vsdx + .figure.json`；`scripts/orthogonal_router.py` 负责 H/V 布线；`scripts/vsdx_writer.py` 生成原生 Visio Open Packaging 格式。
- 质量门禁：`scripts/figure_qc.py` 检查斜线、节点重叠、连线穿节点、标签压字、A4 超版心、中英文图题、SVG/drawio/VSDX 完整性和 RES 关联。
- 位图导出：`scripts/export_png.py` 调用本机 Chrome/Edge 导出 300 dpi PNG，不联网、不安装依赖。
- Word 模板纸张和图表几何审查：`scripts/a4_layout.py`。
- Markdown 表格规划：`scripts/table_layout.py`（输出交给对应 Word Skill 转成原生 Word 表格）。
- 七张截图及总结：`assets/word-figure-references/` + `references/visio-style-a4-guide.md`。
- 正交规则：`references/orthogonal-routing-rules.md`；中英文图题：`references/english-caption-spec.md`；A4 规范：`references/a4-figure-layout-spec.md`。
- 用户照片：`user-uploads/` → 候选 RES/VIS → 模块/权利/事实人工审核。

**明确删除**：在线搜图脚本、互联网图片下载脚本、相关参考文档、主动搜图 CLI 命令。迁移旧代码时由安装器先备份，再移除公开执行入口。

**示例**：

- `examples/visio-style-example.json`：带中英文图题的规范 spec。
- `examples/orthogonal-flow-example.svg`、`examples/orthogonal-flow-example.drawio`、`examples/orthogonal-flow-example.vsdx`、`examples/orthogonal-flow-example.figure.json`、`examples/orthogonal-flow-example-300dpi.png`：正交图示例。
- `examples/before-diagonal-sms-flow-300dpi.png`、`examples/after-orthogonal-sms-flow-300dpi.png`、`examples/orthogonal-upgrade-comparison.png`：修改前后对照。**仅作格式判例**，图中的 SIM900A、AT 指令等节点不得复制为其他项目的技术事实。
- `examples/A4-正交流程图与英文图题示例.docx`、`examples/page-1.png`、`examples/A4-正交流程图与英文图题示例-audit.json`：真实 Word 渲染样例（非学校官方模板）。
- `examples/A4-图表排版示例.docx`、`examples/A4-三线表强制规范示例.docx`：A4/三线表格式样例。

**v1.4.1 新增硬门禁**：所有常规连接线必须正交；判断分支必须有标签；正式图必须提供中英文图题元数据与原生 `.vsdx`；`figure_qc.py` 未通过不得入库。所有表头/数据单元格必须水平+垂直居中。三线表强制要求保持不变。

**保留硬门禁**：所有新生成数据表必须严格 Word 原生三线表；`scripts/three_line_table.py` 负责应用与 OOXML 审计，仅操作指定数据表，不改官方固定表单。

**VSDX 说明**：`.vsdx` 为原生 Visio Open Packaging 包；本机无 Visio 时状态为 `pending-visio-open`，不得伪称已打开验证。

**运行依赖说明**：三线表 DOCX 实施与审计需要现有 Word 生成环境提供 `python-docx`；本 Skill 不自动安装，缺失时须标记为待执行，不可声称三线表已经通过。300 dpi PNG 导出需要本机 Chrome/Edge；没有浏览器时保留 SVG 即可，不自动安装。