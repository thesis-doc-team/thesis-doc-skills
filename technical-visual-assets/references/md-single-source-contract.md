# 技术 MD 唯一技术事实源协议 v1.3

1. 唯一事实输入：`<PROJECT_ROOT>/deliverables/technical-document/<TECH_MD>.md`，保存 SHA-256。项目唯一 `project_id`。FACT-xxx 只作同项目追溯与 VIS 旧契约兼容。
2. `scan`：只读提取 Mermaid、ASCII、Markdown table、本地图片引用；每项 `source.{technical_md,technical_md_sha256,start_line,end_line,section}`。
3. `sync`：生成和复用 `project-assets/resource-catalog/index.json` 资源，`RES-xxx` 主类别限六项；图源 `.mmd`、表格 `.md` 按哈希去重；新增 `module-requests.json/.md`。
4. `module-list --save`：返回 `MOD-xxx` 用户照片需求，`name_from_md`、准确证据行号、`claim_strength`、`user_upload_status`；不向外请求，不添加硬件事实。
5. `upload-photo`：要求 `module_id` 存在、文件位于同项目 `user-uploads/`、基本 PNG/JPG/WEBP 校验、用户提供来源/授权文字；建立用户照片 `RES` 和旧 VIS 映射，保持待审。
6. `report`：按六类返回资源和模块缺口；任何历史 `web-image-candidate` 只保留审计，不允许被批准、插入或新建。
7. 统一前端显示可以消费 `module-requests.json` 和 `resource-catalog/index.json`；对管理员显示技术/版权/Word版式审核三个独立状态。不把未通过纸张验证的图展示为“可直接用于 Word”。
8. 表格：`resource-catalog/tables/RES-xxx.md` 代表完整原文。下游负责 Word 原生表格，布局规划 `scripts/table_layout.py`；不能把表格都缩成图片。
9. 图表：以 MD 为技术来源，`diagram-spec.json` 作为显式布局数据输入；用 `scripts/visio_diagram.py` 生成 SVG+drawio，可编辑源仍保留。复杂 Mermaid 不支持时必须说明，不能通过转简化错误图掩盖。
10. Word 真正交付由业务 Skill 调用模板 `profile`、`fit-figure`、`audit` 和实际 Word/WPS 页面检查；静态通过不是排版已验收。
