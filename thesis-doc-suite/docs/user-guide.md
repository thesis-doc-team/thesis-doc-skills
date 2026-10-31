# 完整使用手册（User Guide）

本手册面向**使用者**，覆盖每个 Skill 的详细用法、资产复用、版本迭代、清理机制与协作注意事项。命令总览见 [skill-catalog.md](skill-catalog.md)，环境准备见 [prerequisites.md](prerequisites.md)，出错排查见 [troubleshooting.md](troubleshooting.md)。

约定：`<PROJECT_ROOT>` 表示你的项目资产包根目录（如 `E:\thesis-work\env-monitor`）；命令行示例以 Windows 为准，macOS/Linux 把 `python` 换成 `python3`、反斜杠换正斜杠。

---

## 1. 通用约定（所有 Skill 适用）

### 1.1 调用方式

六个业务 Skill 与 `init-project` 设为**仅显式调用**：在 Claude Code 输入框敲 `/thesis-doc-suite:<skill名>`（可附一句话说明你的情况）。`check-project`、`help` 也可以在你提问时自动响应。

### 1.2 Skill 的统一执行骨架

每个业务 Skill 都按同一套生命周期工作，你在执行汇报里能看到每一步的结果：

```
识别项目（PROJECT_ROOT / project_id）
 → 先读后写共享资产（复用已有 FACT/REF/计划，缺的才补）
 → 锁定官方模板（SHA-256 + 结构审计）
 → 逆向参考范本写法（只借写法，不借事实）
 → 撰写内容（严格区分已实现/声明/设计/待确认）
 → 原模板副本填充（只写可填区域）
 → 结构校验（OOXML 逐项比对）
 → 截图验证分析（逐页渲染 + 逐张查看）
 → 交付 -vN 成品 + 执行汇报，record-use 登记
 → 清理本轮运行区（成功/失败都清理）
```

### 1.3 交付与验收分工

- **Skill 负责**：执行、自动检查、如实汇报（包括 WARN/FAIL 与未实测项）。
- **你负责**：最终内容验收。所有 Word 文书都是**供指导教师审定的拟稿**——教师意见栏只有拟稿正文，签名/日期/等级一律空白或不写；指导时间、地点、方式等未经你确认的信息一律留空。

## 2. 六个业务 Skill 详细用法

### 2.1 project-technical-doc｜项目技术文档（MD + 离线 HTML）

**输入准备**：项目源码目录和技术/需求资料（MD/DOCX/PDF）至少给一种；两者都有时会交叉核对"设计 vs 实现 vs 测试"。指定 `<PROJECT_ROOT>` 以便登记共享事实。

**调用**：

```
/thesis-doc-suite:project-technical-doc 项目在 E:\thesis-work\env-monitor\source，技术资料 docs\技术手册.md，项目根目录 E:\thesis-work\env-monitor
```

**产出**（`deliverables\technical-document\`）：`<项目名>-技术文档.md`（唯一事实正文）、`<项目名>_用户展示.html`（从 MD 派生的单文件离线网页）、`执行汇报.md`、（大型项目）`项目事实与证据台账.md`。

**验收要点**：
- HTML 双击可离线打开；章节目录、表格、流程图与 MD 对应。
- 抽查关键结论是否标注了证据等级（"代码实现 / 资料声明 / 设计目标 / 待确认"）。
- 该 Skill **不生成**"已知问题与改进建议"等评审章节——这是有意的内容边界。

**特别注意**：本 Skill 是 `FACT-xxx` 的主要提炼者，写完后任务书/开题报告直接复用这些事实。

### 2.2 thesis-taskbook-write｜毕业设计任务书

**输入准备**：技术资料或技术 MD（必需）；课题题目；起止日期（未知则保留占位）；院系/班级/姓名/学号/导师/职称（**缺失留空，不从范本继承**）；官方模板用内置只读副本即可，学校发了新模板则提供新文件。

**调用**：

```
/thesis-doc-suite:thesis-taskbook-write 项目根目录 E:\thesis-work\env-monitor，课题"基于STM32的环境监测系统"，起止日期 2099-03-01 至 2099-12-31
```

**产出**（`deliverables\taskbook\`）：`<课题简称>-毕业设计任务书-vN.docx` + 执行汇报。

**验收要点**：
- 官方栏目/表格/附注/签名栏原样；首页单元格居中无假居中（空格凑的）。
- "主要参考文献"≥10 篇且**全部可追溯**（执行汇报列 REF-xxx 与核验状态）。
- 周次从第 1 周连续覆盖到总周数、无重无缺。
- 下达人意见为**拟稿**（≥50 字），签名与日期空白。
- 页数是自然排布的结果，不以官方空白模板页数为基准。

### 2.3 opening-report-writer｜毕业设计开题报告

**输入准备**：项目技术文档（上游技术 MD 最佳）；共享资产里已有文献/计划会被复用；封面个人信息（缺失留白）。

**调用**：

```
/thesis-doc-suite:opening-report-writer 项目根目录 E:\thesis-work\env-monitor，使用 deliverables\technical-document\ 下的技术 MD
```

**产出**（`deliverables\opening-report\`）：`<课题简称>-毕业设计开题报告-vN.docx`、`执行汇报-vN.md`、`文献核验台账-vN.md`（每版恰好三项）。

**验收要点**：
- 七项内容完整（立项依据、研究现状、任务与可行性、重点问题、工作条件、进度计划、参考文献），正文汉字 ≥3000（不含封面与文献）。
- 正文引文是**真正的 Word 上标**，与文末文献一一对应、单次编号、悬挂缩进。
- 研究现状是"文献观点 + 分析 + 与本课题关联"，不是文献标题堆砌。
- 进度计划与共享 `schedule.json` 一致；**拟开展的工作没有被写成已完成**。
- 教师审阅意见为 ≥50 字拟稿，签名/日期空白。

### 2.4 literature-review-write｜文献综述

**输入准备**：课题技术资料；已核验文献（共享库复用优先，缺的才检索补充）；封面信息（缺失留白）。

**调用**：

```
/thesis-doc-suite:literature-review-write 项目根目录 E:\thesis-work\env-monitor，课题"基于STM32的环境监测系统"
```

**产出**（`deliverables\literature-review\`）：`<课题简称>-文献综述-vN.docx` + 执行汇报。

**验收要点**：
- 正文 ≥2500 字，结构为"引言 → 国内外研究现状 → 评述 → 参考文献"。
- 综述回答"别人做了什么、证据说明什么、还有什么限制、本课题据此如何设计"，不是技术手册复述。
- 引文真上标；文后 `[n]` 正常基线、连续无重复；无 `Error! Reference source not found`。
- 封面无范本残留的他人信息；导师意见拟稿 ≥50 字、签名日期空白。

### 2.5 thesis-guidance-record-write｜指导记录

**输入准备**：真实项目技术资料（用于按真实技术阶段组织记录主题）；如果你手上有**真实的**指导时间/地点/方式/教师评价，提供给 Skill 照实填写——没有就留空。

**调用**：

```
/thesis-doc-suite:thesis-guidance-record-write 项目根目录 E:\thesis-work\env-monitor
```

**产出**（`deliverables\guidance\`）：`<课题简称>-指导记录-vN.docx` + 执行汇报。

**验收要点**：
- 默认 ≥8 次记录（每组 13 行官方表格结构原样复制；次数不受原模板页数限制）。
- 每次"指导教师指出存在问题"与"指导教师提出修改意见"**编号、条数、顺序一一对应**；修改意见具体到"对象 + 动作 + 看到什么算通过"。
- 日期/地点/方式/面授勾选/教师评价/签名**一律空白**，等真实填写——这是待审核拟稿/打印底稿，不能代替实际指导与手写签字。
- 官方固定行高导致的自然跨页会如实标注 WARN，不私自改表格框架。

### 2.6 thesis-midterm-check-write｜中期检查记录表

**输入准备**：真实项目技术资料 + **阶段进展证据**（做到哪一步、有什么测试/成果、遇到什么问题）；共享计划与进展快照（有则复用）；检查日期（未知留空）。

**调用**：

```
/thesis-doc-suite:thesis-midterm-check-write 项目根目录 E:\thesis-work\env-monitor，检查日期 2099-06-15
```

**产出**（`deliverables\midterm\`）：`<课题简称>-中期检查记录表-vN.docx` + 执行汇报。

**验收要点**：
- 三个栏目各 ≥200 有效字：完成进度、存在的问题及整改措施、指导教师意见（拟稿）。
- "存在问题"与"整改措施"分两组小标题顶格，各以（1）（2）…编号，**一问题一措施、同号成对**，一条一段。
- **计划 ≠ 实际**：周计划安排不能被写成已完成进度；无证据的成果不写"已完成/测试通过"。
- 学院意见栏默认完全空白。

## 3. 资产复用示例

典型的一次复用链：

1. `project-technical-doc` 把"STM32F103 主控 + 4G 模块 MQTT 上报"核实为 `FACT-001`（`status=implemented`，出处：`source/main.c:120`）。
2. `thesis-taskbook-write` 直接引用 `FACT-001` 拟定设计任务，不重查源码；检索并核验 12 篇文献（`REF-001`…`REF-012`）入库；建立周计划基线（`PLAN-2099-01`，`draft`）。
3. `opening-report-writer` 复用 `FACT-001` 与其中相关的 10 个 REF；正文 `[1]`~`[10]` 按本次引用顺序重排（与 REF 稳定 ID 是两套编号，通过映射关联）；进度安排直接取 `PLAN-2099-01`。
4. `thesis-midterm-check-write` 对照同一 `PLAN-2099-01` 写"计划 vs 实际进展"，实际进展以 `PROG-xxx` 记录（带 `as_of` 与证据来源）。

操作层面只需遵守：**先 `status` 看已有，缺的才 `merge`，改旧条目必须 `--replace --reason`**。Skill 会自动执行这些规则，你主要是在执行汇报里确认"复用了哪些、新增了哪些"。

```bash
# 随时查看共享资产状态
python core\asset-management\project_assets.py status --root "E:\thesis-work\env-monitor"
```

## 4. 多轮迭代与版本（-vN）

- 第一版交付 `xxx-v1.docx`；你提修改意见后再次调用同一 Skill，生成 `xxx-v2.docx`——**旧版保留**，可对照、可回退。
- 每版单独 `record-use` 登记（路径 + SHA-256 + 实际使用的 REF-xxx）；`activity.jsonl` 就是这个项目的文书变更史。
- 修改意见尽量具体（"任务书第 3 条任务改为 XX"、"增加传感器选型对比"），Skill 会在新版中落实并在执行汇报说明改动。
- 如果是**技术事实**错了：先修订技术资料/事实库，再重新生成下游文书——Skill 不允许直接在 DOCX 里手改出"双版本漂移"的内容。

## 5. 清理机制（你无需手动删临时文件）

- 每轮运行的中间文件（渲染 PNG、临时 JSON、审计报告）只写入 `.skill-tmp\<skill-name>\<run-id>\`，结束（无论成功失败）自动清理。
- 清理有**所有权标记**保护：只能删本 Skill 自己创建的运行目录；不会碰你的原始资料、官方模板、共享资产、成品（含历史 -vN）和其他 Skill 的运行区。
- 若清理受阻（如文件被占用），执行汇报会列出残留路径和原因，不会扩大删除范围。
- 截图等验证材料是**验证手段不是交付物**，结论写进执行汇报后随运行区清理。

## 6. 与指导教师协作的注意事项

- **不代签、不代章、不编造**：所有教师意见栏都是"供教师审定的拟稿"；签名、日期、等级、面授勾选留白；不虚构指导会面、文献、数据、成果。
- 拿到教师真实反馈后：把反馈作为新一轮输入（例如"教师要求压缩任务书第 2 条"），生成 -v2；经教师确认的真实信息（如真实指导日期）可以补入项目资产（带来源）。
- 文书中的参考文献应能被教师/学校复核；`verified=false` 的条目会在执行汇报和台账中显式标注，不要把它们当"已核实"提交。
- 兼容渲染检查通过 ≠ WPS/Word 客户端已验证；只有真正用 WPS/Word 打开过，才能对学校说"已在 WPS 检查"。

## 7. 常用命令速查

```bash
# 创建项目资产包（也可用 /thesis-doc-suite:init-project）
python core\asset-management\project_assets.py init --root "E:\thesis-work\env-monitor" --project-id "ENV-MONITOR-2099" --name "基于STM32的环境监测系统"

# 环境与项目检查（也可用 /thesis-doc-suite:check-project）
python scripts\check_env.py --root "E:\thesis-work\env-monitor" --skill thesis-taskbook-write

# 插件结构与模板哈希自检
python scripts\verify_plugin.py

# 共享资产（init 见上）
python core\asset-management\project_assets.py status --root "..."
python core\asset-management\project_assets.py merge  --root "..." --kind references --input new-refs.json

# 打包分发
python scripts\package_plugin.py
```

各业务 Skill 内部脚本（inspect/fill/validate/render 等）的完整命令行见对应 `skills/<name>/SKILL.md` 的"执行命令"章节。忘记命令或不知道先做什么时，随时输入 `/thesis-doc-suite:help` 查看导航。
