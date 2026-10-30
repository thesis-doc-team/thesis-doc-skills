# 技术资料、文献与外部来源规则

- 技术资料只证明其写到的方案/接口/状态；不能证明具体导师日期或测试结论。技术事实拆成 FACT-xxx，`source`写文件、章节/页码/代码路径，`status`用`implemented`/`declared`/`unverified`/`proposed`。
- 论文来源：CNKI（知网）、万方、维普、正式期刊、学位论文库、IEEE、ACM、出版社、Crossref/DOI。必须核对作者、题名、刊物、年份和可追溯落地页。
- 工程来源：ST/Arm/传感器/模块厂商手册，标准组织（比如 MQTT OASIS）与平台官方资料优先；CSDN只作经验/排障补充，必须标为`blog`，不能冒充学术论文。
- 先复用`project-assets/references.json`的已核验 REF-ID，新增前去重；如元数据不可核验，`verified=false`，不要臆造。真实 URL/访问或查证时间需入资产；链接是来源，不自动证明测试已通过。
- 官方指导表中没有文献列表栏目，不新加“参考文献”或编号引用栏；若本次文字确实参考来源，可在执行报告用 REF-ID 追溯，必要的材料说明放项目共享资产，而不是偷偷改 Word 表格。
- 周计划只维护一份`project-assets/schedule.json`，草稿和用户确认状态分开；不能直接把周计划写成已发生指导日期。
