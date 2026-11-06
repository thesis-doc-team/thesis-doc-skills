# 与 thesis-doc-suite 项目资产契约的兼容关系

**唯一正式共享资产协议**仍为上级插件的 `core/contracts/shared-project-assets-contract.md`。本文件只描述 visual Skill 在 1.3.1 下的附加规范，冲突时以 shared contract 为准。

- 项目 `project_id` 不可变；`project-assets/` 保存 FACT/REF/VIS 和新增 RES 索引；`deliverables/` 历史正式文书版本不覆盖；`/.skill-tmp/` 仅清理本次运行产生的临时文件。
- 视觉资产 `VIS-xxx` 保留原审核及事实门槛；RES 六分类用于网站查询，不替代 VIS 的正式审核。
- 用户上传模块图不得未审核即视为“经授权正式照片”；同一 MD SHA + 图像哈希防重复；所有有效登记写活动审计。
- 完全不依赖联网搜图，没有新增外部网络照片资产入口。旧历史线上候选仅保留审计，迁移时禁用，不继续使用。
- `md_pipeline.py` 不编辑 `facts.json`、技术 MD、学校 DOCX、HTML；可新建同项目 `resource-catalog` 索引及 `module-requests`。
- DOCX A4 尺寸取自真实官方模板，最终 DOCX 需 Word/WPS 视觉验收，不改变模板章节及样式。

## v1.4.0 图题与路由字段

- 正式技术图 RES 条目新增：`figure_number`、`caption_zh`、`caption_en`、`caption_zh_full`、`caption_en_full`、`caption_position`、`caption_review_status`、`routing_status`、`figure_meta`、`print_vsdx`、`print_vsdx_sha256`、`native_visio_vsdx`、`vsdx_verification`。
- `figure_meta` 指向 `*.figure.json`；图题不画进图片像素，Word/HTML 使用原生段落。
- `routing_status=orthogonal` 只表示几何布线通过；`caption_review_status=pending-human-semantic-and-Word-page-review` 表示语义与 Word 页面仍需人工验收。
- 旧 v1.3.1 资产没有这些字段时仍可读取；升级不删除历史 RES/VIS/FACT，不覆盖历史成品。
- 新生成图必须通过 `figure_qc.py`；QC 通过不等于视觉验收通过。
