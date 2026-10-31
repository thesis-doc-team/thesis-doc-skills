---
name: thesis-guidance-record-write
description: 只编写塔里木大学毕业论文（设计）指导记录（不写开题报告/任务书/中期检查表）。严格以不可修改的学校官方 DOCX 为底稿，从去标识化已填范本逆向学习内容结构、格式和问题→整改一一对应方式；按真实项目技术资料逐次拟稿、至少8次、自动复制官方13行记录表、保留全部固定栏目及教师评价签名空白；与其他毕设Skill共享一个项目资产包（数据+成品+运行区），输出DOCX及结构/逐页截图检查、追溯使用的文献和事实、安全清理中间文件。未确认的指导时间、地点、方式与评价不予编造。
---

# thesis-guidance-record-write｜毕业论文（设计）指导记录编写

## 0. 任务边界与判定优先级（执行前必须读）

**唯一正式输出类型：**《毕业论文（设计）指导记录》**可供指导教师审核的 Word 拟稿**。即使用户提示词误写“开题报告”“任务书”，只要本轮明确指定的是指导记录官方模板，本 Skill **只负责指导记录**。不得顺带生成开题报告、任务书、论文正文、中期检查表、技术报告、HTML 网站或独立文献综述。

**优先级：** 用户本轮明确要求（仅在不破坏正式模板的范围内）＞ 用户当次上传的正式学校空白模板的固定架构与说明 ＞ 当次项目技术资料及实际指导证据 ＞ 同项目共享资产中有来源的事实/计划/文献 ＞ 已填范本的语言节奏及条目写法 ＞ 常识。**版式冲突服从官方，技术事实冲突服从真实证据；不存在“多数范本投票可以覆盖官方”**。

**严禁：** 改写官方模板原文件字节；重新绘制/新建仿制表格；改变封面、填写说明、纸张与页边距、学校固定文字、13行记录区的行高/列宽/边框/合并关系、评价选项或签字栏；冒写导师真实评价、签名、真实会议/具体日期/地点、已完成项目进度或测试通过；继承范本里的人名、学号、日期、设备参数和结论。**允许**复制官方的13行空白记录区作为更多次数的记录页，填写指定的空白单元格及记录正文，必要时在记录正文单元格内增添正文段落；不得减少或更换固定栏目。源原件应始终 SHA256 相同。

**必须承认的学校要求：** 官方填写说明要求指导记录及指导评价手工填写、方框打勾；每月提交的记录不少于4次，其中面授不少于2次，且由教师审核签字。**AI 的 Word 文件是待审核拟稿/打印底稿，不是可以代替实际指导与手写签字的正式证明**。不自动勾选面授，不伪造符合每月次数的日期。若用户提供真实日期/方式/教师签字记录，照证据填写允许字段；当前脚本默认保留面授/评价/签字空白供人工处理。见 `references/official-template-layout.md`。

## 1. 单一项目资产包（不可在 Skill 安装目录存储项目事实）

项目根目录 `<PROJECT_ROOT>` 下：

```text
<PROJECT_ROOT>/
├── project-assets/                       # 数据：共享事实、文献、周计划
│   ├── project.json                      # 真实项目和人员信息（可缺省）
│   ├── facts.json                        # FACT-xxx 真实技术事实+状态+证据
│   ├── references.json                   # REF-xxx 已核验文献/来源
│   ├── schedule.json                     # 跨文书唯一周计划（草案/确认）
│   ├── progress.json                     # PROG-xxx 时点进展（可选，兼容中期Skill）
│   └── activity.jsonl                    # 资产变更+成品哈希+历史使用日志
├── deliverables/
│   ├── taskbook/                         # 任务书Skill维护
│   ├── opening-report/                   # 开题报告Skill维护
│   ├── midterm/                          # 中期检查Skill维护
│   └── guidance/                         # 本Skill只写这里
│       └── <课题简称>-指导记录-vN.docx
└── .skill-tmp/
    └── thesis-guidance-record-write/
        └── <run-id>/                     # 有本Skill专属所有权标识的运行区
```

**一个项目 = 一个资产包（数据 + 成品 + 运行区）**，`project_id` 是跨 Skill 的稳定标识。先 `status`，不存在再 `init`，不得为每种文书创建第二套文献库或周计划，不得覆盖旧版本文件。`project-assets` 的基础结构兼容上传的 `thesis-midterm-check-write v1.3` 及其所述任务书资产协议 `schema_version=1`；共用 REF/FACT/PROG 稳定 ID。后续集成以 `references/shared-assets-contract.md` 为准。

- **项目事实**存最小原子结论+来源/状态，不把某次指导完整正文当作项目技术事实；
- **文献**先复用 `references.json` 的 `REF-ID`，缺且确需外部依据才查证新文献，新增需保留核验链接/类型/时间；
- **计划**只在 `schedule.json` 一处维护，不能据此伪造已进行的会面和项目完成度；
- **拟稿**仅进入本轮运行区和最终DOCX；经教师确认的真实指导信息以后才可据来源补充到项目资产中；
- **成品**按 `v1/v2/...` 不覆盖；结构检查与逐页截图检查通过后才能 `record-use --doc-type guidance`；
- **中间文件**必须安全清理本轮有所有权标记的 `run-id` 目录；不许删模板、资料、资产、历史成果、其他 Skill 的工作目录。

## 2. 原始材料及模板锁定

安装包包含：

- `assets/official-guidance-template.docx`：本轮上传的官方《塔里木大学毕业论文（设计）指导记录》未经改写的原样副本；
- `assets/template-lock.json`：SHA256、节、表格及13行分组的审计锁；
- `assets/reference-samples/anonymized-guidance-sample.docx`：从用户最初已填范本去个人身份、学号、项目标识、日期和地点后得到，仅用于逆向写作/布局观察；
- `references/reverse-engineering.md`：求同存异、内容体裁、判定规则、负面样本特征；
- `tests/format-smoke-input.json`：胡杨林监测项目8次**虚拟拟稿**的非个人数据，**不是已发生的指导日志**。

**一定先读取用户本次的官方模板**。若上传了新版，与内置 SHA 不同则必须停止旧版定位脚本，另做只读结构审计、重新适配、更新锁和测试；**不能为了方便偷偷用内置旧版冒充用户新版**。官方空白示例只有2组记录，每组是同样的13行；**记录次数不受原模板页数限制，默认至少8组**。

官方原件有2节、2张表（填写说明4行2列、指导表26行11逻辑列），指导表每13行一组，许多单元格横/纵合并。脚本追加的是`deepcopy`已有13行结构，而不是`Document.add_table()`重画。注意 `python-docx` 的逻辑列11不等于实际物理单元格数；必须依据锁定结构处理合并格。

## 3. 文本逆向：范本求同存异→统一生成规范

逆向前阅读 `references/reverse-engineering.md` 和 `references/numbered-pairs.md`，对照官方表与已填范本。识别**不变项**（每次记录的栏目顺序、两组指导语言、评价、签名）与**可变项**（每次技术主题、2—4个问题、每个整改动作、阶段衔接、字数）。已填范本格式可能有字号、缩进、复选框乱码、表格跨页等差异，这些**不能凌驾官方**。直接提取写作方法，不复制示例句、项目状态、人物或月份。

每次统一使用：

```text
指导教师指出存在问题：
1. <明确对象/风险/需要核实之处>；
2. <明确对象/风险/需要核实之处>。
指导教师提出修改意见：
1. <针对问题1的动作、实施方法、检查方式>；
2. <针对问题2的动作、实施方法、检查方式>。
```

**一问题一措施，编号/条数/顺序严格配对**，每条独立成段，统一段落首行缩进和字号，不能写作一大坨无换行文本。建议每次2组，必要时1—4组，长内容不能超出固定正文区域而被裁切。**修改意见必须可执行、可观察，禁止意义不明的指令文字**：落到"具体对象（指令名/信号/参数/数值/数据字段/器件）+ 动作 + 看到什么算通过"三要素，例如"逐条执行 AT、ATE0、AT+CMGF=1、AT+CMGS+Ctrl+Z 并记录每条实际返回，拔卡模拟无信号确认重试后转本地蜂鸣"，而非"加强学习""尽快完善"，也**禁止**"按§X指令时序设计检查表并记录返回码"这类文字——指导记录是独立文书，读者看不到你的文档目录，正文不得出现"§X/第X章/附录X"式内部章节引用（须展开成具体事实），不得出现"设计表格/整理资料/记录返回码/进行验证/建立机制"等后面不接具体对象与判据的空泛元动作，编号（如用例T07）可保留但须伴随独立可懂的动作描述。三要素判据与反例→正例对照见 `references/numbered-pairs.md`。“尚需核查/建议测试”与“已出现故障/已测试不通过”要按证据区分。先写**真实技术阶段**，不是从时间线上杜撰8次会议。

**推荐8次技术推进主线，但按具体项目调整：** 需求和系统结构→硬件资源/电源→传感器通信→数据采集处理→显示与交互→远程传输/云端→异常告警→系统联调/论文整理。不是所有项目都必有硬件/云平台；资料没提的模块不可编造。胡杨林示例的器件（STM32F103、D1、SHT40、ADC/DMA、OLED、4G DTU、SIM900A、MQTT/JSON）只用于测试此 Skill 的表达能力，绝不作为其他课题的默认技术栈。

**事实分层：** `已证实实施` / `技术文档声称实现但无测试佐证` / `设计计划` / `待验证或缺证据`。技术手册的“✅已实现”或“测试方案”不能自动变成某月实际完成或导师现场指导。输入只有技术文档时生成 **8次建议性记录草稿**，一律 `status=draft`，日期/地点/方式/教师评价/签字留空。附执行报告列出需本人和导师核实的事项。

## 4. 排版保护与分页冲突

**强制：** 保持官方模板的标题、填写说明、表格整体结构、A4尺寸、边距、行高、列宽、边框、合并关系和评价选项。可填区域里根据范本采用宋体中文/Times New Roman数字英文、10.5pt左右的编号正文及明确首行缩进；只有可填正文允许增加段落及必要的正文样式设置。`fill_guidance.py` 不修改固定行高或页边距，正文样式只作用于内容单元格。`validate_guidance.py` 比较原本和成品每一行的 `trPr`、每一物理格的 `tcPr`、表格 `tblPr`/`tblGrid`，以及固定文字和评价签字。

**学校官方模板原来的固定行高总和可超过单页可打印高度，导致一条记录跨页。这是源模板特性，不是靠缩字号或改页边距可以私自修复的问题。** **实质性分页门禁：页数本身不是目标，按当次内容的自然排布判断**——用户已明确“空白模板页数仅参考、按实际需要扩展”，所以：

1. **绝不限制成品必须2、3或10页**；8次记录按真实排版产生实际页数；**不得为凑足或压缩到某个页数而增删事实、稀释或堆砌文字**。硬性 FAIL 只有两类：为凑/压页数增删事实或改动官方固定框架；最后一页整页空白或只剩签字/评价的孤页且未先通过调整措辞与段落分配消除、也未如实报告。
2. 渲染后每页查：文本被截断、单元格内容溢出、题目超宽、边框断裂、跨页评价/签字、最后签名孤页、中文标点或乱码。
3. 如官方原本自然跨页，须在检查报告中标 `WARN—官方固定行高跨页`，不是虚报视觉完美；优先减少不必要冗词（不删技术必要内容）。**禁止未经用户授权压缩或改变固定框架**；如跨页妨碍提交，报告模板天然冲突，由用户/学校决定是否允许衍生排版版式。
4. 若技术文字超出正文区域造成遮挡/丢字 → `FAIL` 并重写正文；不能通过缩到8pt、调表格框架“修图”。
5. 结构验证通过≠视觉验收通过；必须渲染全部页 PNG，Agent/人工逐张审阅并报告张数和异常。WPS 未实际打开则注明“WPS未实测”。

## 5. 参考资料的来源及复用（没有参考文献栏时绝不擅自添加）

若需要外部资料核实理论、技术背景、测试方法：优先**中国知网 CNKI、万方数据、维普、正式学术期刊网站、高校学位论文库、IEEE Xplore、ACM Digital Library、Springer、ScienceDirect、Crossref/DOI**。STM32、I2C、AT指令、MQTT等的技术规范优先 ST/芯片/平台/标准组织**官方手册**。**CSDN 可用作排障案例/工程经验，但它是博客而不自动算学术论文**；不得把 CSDN 文章编成期刊论文或凭空写作者、发表日期、DOI/卷期页码。

文献完整字段应有作者、标题、出处、年份、URL/DOI、来源类型、核验时间及实际用途；从项目 `references.json` 中读 `REF-xxx` 复用，没有必要不重复搜索；若链接或元数据无法证实，`verified=false`，不能声称已查证。指导记录官方表**没有参考文献栏目**，不得因用户要求来源真实就擅加新章节；参考文献存项目级资产并在执行报告以ID追溯。详见 `references/source-and-citation-policy.md`。

## 6. 完整执行链（不得跳过截图检查）

**逐次起草、分批写入（硬性，禁止一次性整篇生成）**：≥8 次指导记录按次推进——每次记录（主题、`issue_pairs`、要点）起草完成即写入草稿文件，一次落盘再写下一次；**禁止一次性倾倒全部次数的内容**。全部记录落盘后再形成输入并一次性生成 DOCX。第 8 步（结构校验 + 截图验证分析）为**唯一终检**，写作中途不反复全文重检；终检问题只定点修可填区内容后重新生成复检，不推倒全部草稿。执行汇报注明分几次写入与一次终检结论。

1. **识别项目**：技术 MD/文档、用户原表、已填范本、个人字段、真实指导记录、`PROJECT_ROOT`。信息缺失默认留白并报告；用户没有提供老师/日期就不重复索要，先交草稿。
2. **资产复用**：`project_assets.py status`；有根目录时无历史才 `init`；先读 `project/facts/references/schedule/progress`，核验同一个 `project_id`。更新事实/计划需真实来源，覆盖需要 `--replace --reason`。
3. **审计底稿**：运行 `inspect_template.py`；SHA 匹配 `template-lock.json` 才可执行填充脚本。官方原件永远只读。
4. **逆向范本**：读取去标识化DOCX、`reverse-engineering.md`，必要时运行 `inspect_samples.py`；归纳共性而不是照搬项目细节，审查冲突与负面写法。
5. **编写草稿**：根据技术资料和事实矩阵设计不少于8次的独立主题，填写各自 `issue_pairs`（problem/action）并做“对象/动作/验证”的语义检查，记录阶段事实级别；严格保持草稿标识。
6. **形成输入**：运行区内写 JSON，按 `templates/input.schema.json`；可调用 `project_assets.py compose` 验证共享资产ID（只组合已有字段不自动代写正文）。
7. **生成DOCX**：`fill_guidance.py` 将源表26行保留，按需复制其13行模板块，填写封面及每次记录的可填区域；保留导师评价空白、勾选空白、签字空白。输出 `deliverables/guidance/<课题>-指导记录-vN.docx`，禁止覆盖已有版本。
8. **验证**：运行 `validate_guidance.py` 对比结构/固定栏目/字段、问题与修改意见一一对应、首行缩进、记录次数；随后进入**截图验证分析（Screenshot Verification Analysis，交付前硬性环节，缺一不可）**——**截图**（`render_visual.py` 出全部页 PNG/PDF，只存本轮运行目录，不进交付目录）→ **逐张分析**（缺一张即未完成：字形缺损、字符裁切、溢出/遮挡、边框、表头、签字栏、跨页评价/签字、孤页、过密/过空）→ **留痕汇报**（执行汇报固定填写截图引擎/工具、截图张数、实看张数、逐张结论 PASS/WARN/FAIL 与问题清单、返工复检次数、WPS 实测边界声明）。未逐张分析不得宣称视觉验收通过、不得登记 record-use；截图是验证手段不是交付物。若跨页源自官方原本，则要真实披露，不假装已经修复。
9. **归档**：完成结构+视觉复核后 `record-use` 只登记最终正式版本路径、SHA256及**实际引用的**REF-ID；用户保留验收权，输出最终 DOCX 和短版执行报告。
10. **清理**：`finally` 里 `project_assets.py cleanup` 仅删除有本 Skill 所有权标记的 `.skill-tmp/.../<run-id>`；不删用户输入、原官方表、持久资产、成品版本和其他 Skill 运行文件。失败也要清理并如实汇报。

## 7. 快速调用

```bash
# 进入解压后的 thesis-guidance-record-write 目录；PROJECT_ROOT 是用户项目目录
python -m pip install -r requirements.txt
python scripts/project_assets.py status --root "$PROJECT_ROOT"
# 若尚未初始化：
# python scripts/project_assets.py init --root "$PROJECT_ROOT" --project-id "$PROJECT_ID" --name "$TITLE"
python scripts/project_assets.py workdir --root "$PROJECT_ROOT"     # 保存输出的 RUN_ID 和 WORKDIR
python scripts/inspect_template.py assets/official-guidance-template.docx --json "$WORKDIR/template-audit.json"
# Agent 基于真实资料编写 $WORKDIR/guidance-draft.json，不凭测试数据直接生成正式项目报告
python scripts/project_assets.py compose --root "$PROJECT_ROOT" --draft "$WORKDIR/guidance-draft.json" --out "$WORKDIR/guidance-input.json"
python scripts/fill_guidance.py --template assets/official-guidance-template.docx --data "$WORKDIR/guidance-input.json" --out "$FINAL_DOCX"
python scripts/validate_guidance.py --template assets/official-guidance-template.docx --data "$WORKDIR/guidance-input.json" --file "$FINAL_DOCX" --report "$WORKDIR/structure-report.json"
python scripts/render_visual.py --file "$FINAL_DOCX" --outdir "$WORKDIR/render"
# Agent 必须逐张打开 render/page-*.png，处理问题，记录检查结果
python scripts/project_assets.py record-use --root "$PROJECT_ROOT" --file "$FINAL_DOCX" --doc-type guidance --ref-ids "$ACTUALLY_USED_REF_IDS"
python scripts/project_assets.py cleanup --root "$PROJECT_ROOT" --run-id "$RUN_ID"
```

使用范例见 `README.md`、`templates/execution-report.md` 与 `references/integration.md`。**用户拥有最终验收权；AI对执行、真实写作依据、结构/截图检查和风险汇报负责。**
