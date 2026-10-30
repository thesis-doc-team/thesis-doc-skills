# v1.2（2026-10-30）— 截图验证分析环节

- 步骤 8 与 G4 统一**截图验证分析**（Screenshot Verification Analysis）：截图 → 逐张分析 → 留痕汇报固定三步与红线（未逐张分析不得宣称验收通过、不得登记 record-use）；执行汇报模板同步固定字段。

# v1.1（2026-10-30）— 并入统一资产包版本意识

- 对齐 opening-report-writer v3.1 / project-technical-doc V5 的**项目资产包（bundle）与版本意识**：成品文件名带 `-vN`（`<课题简称>-中期检查记录表-vN.docx`），重生成产出 `-v2`、`-v3`…不覆盖、不删除历史版本；每个版本单独 record-use 留痕，activity.jsonl 即变更史。
- `deliverables/` 子目录命名与全系统一致：`taskbook/`、`technical-document/`、`opening-report/`、`midterm/`（原 `proposal/` 改名 `opening-report/`）。
- G5 生命周期门禁与执行汇报模板同步版本纪律；历史 `-vN` 版本列入永不删除清单。
- 数据层不变：project-assets 核心 schema v1 与可选 progress.json 扩展均与既有协议兼容，回归测试 8/8 通过。

# v1.0（2026-10-30）

- 定位：仅中期检查记录表；固定“官方附件6”为 DOCX 原样底稿，范本作写法逆向参考。
- 继承：`thesis-taskbook-write v1.1` 的 project-assets 核心 Schema v1 与 REF/FACT/计划基线/活动日志/安全清理原则。
- 扩展：可选中期快照 `progress.json`，带 PROG-ID、as_of、来源和 draft/confirmed 状态；与任务书旧脚本兼容。
- 真实性：技术方案 ≠ 实际已完成进展；导师意见仅拟稿；无官方参考文献栏，不额外增栏或强制10篇。
- 工具：模板锁定校验、原空白段落填充、严格结构验收、内置离线回归测试。
- 交付：Word DOCX；Agent 负责逐页渲染和如实反馈；本轮运行中间文件自动安全清理。
