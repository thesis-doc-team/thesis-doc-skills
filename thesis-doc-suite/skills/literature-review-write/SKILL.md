---
name: literature-review-write
version: 3.2.1
disable-model-invocation: true
description: 根据本项目真实技术文档和经核验的论文资料，直接在学校官方 DOCX 文献综述模板的原有可填写区域编写毕业设计文献综述（正文≥2500字、真实 Word 上标引文、参考文献及指导教师意见拟稿）；逆向提炼已完成范本的结构、语体和格式而不复制项目事实。与 thesis-taskbook-write-v1.1 完全共用项目根目录 project-assets/ 的事实、文献、计划、审计记录，按“一个项目=一个资产包（数据+成品+运行区）”归档；逐页截图复核、版本化交付并安全清理本轮中间文件。禁止重建或篡改官方模板，也不生成任务书/开题报告/中期检查表。
---

# 文献综述编写 Skill｜官方母版原位填写 + 文献真实可追溯 + 跨 Skill 项目资产

> **本 Skill 的唯一正式文书**：`<课题简称>-文献综述-vN.docx`，不是开题报告、任务书或中期检查记录表。
> 
> 若用户同一段提示混用了“开题报告 / 中期检查 / 任务书”的称谓，但指定的本次官方模板是“文献综述”，以本次选定的文书类型和模板为准；发生实质冲突则明确说明，不得将别的文书生成器硬套到文献综述上。

## 0｜硬性原则（执行前读取）

1. **官方模板是物理结构真源**。使用 `assets/template-lock.json` 固定原版 SHA-256，`scripts/template_tools.py` 对任何未经重新审计的 DOCX 更改一律 fail-closed。必须在当前用户指定的官方 `.docx` 副本中原位填写，禁止 `Document()` 新建仿造，禁止新画封面线条/重建封面表格、改官方标题文字/表格网格/审阅签名区/节/边距/页码。该 Skill 附 `assets/official-literature-review-template.docx` 为本次上传官方原件的只读副本；用户下一次提供新模板时，以新模板为准，结构不匹配须停止自动填充而不是强灌。
2. **一个项目，一个共享资产包**：与 `thesis-taskbook-write-v1.1` 共用项目根目录 `project-assets/project.json、facts.json、references.json、schedule.json、activity.jsonl`。**绝不额外创建 `data/reference_registry.json`、另一套 reference index 或另一份“项目真相”**；完整规则见 `references/shared-project-assets-contract.md`。
3. **文献先复用后增补**：只使用项目共享库中实际核验、与本次研究相关的资料。新增文献先核对原始出处后 `merge --kind references`；现有 `REF-xxx` 稳定 ID 不变，本综述的 `[1]` 由**正文首次引用顺序**生成，不能直接把项目稳定 ID 当文内编号。
4. **文献真实性硬门槛**：优先知网 CNKI、万方、维普、期刊官网、出版社、学位论文库、正式学会、DOI 或可靠论文原文；CSDN/博客/硬件手册可作背景与技术辅助，不得冒充已发表研究。只查到检索片段不得臆造结论或著录元数据；每条记录 `source_url/source_type/verified/checked_at`，严格遵守 `references/citation-policy.md`。
5. **正文≥2500字**：按本次官方模板要求，五号宋体、1.5 倍行距，英文/罗马字符 Times New Roman 正体。标题优先 `1 引言`、`2 国内外研究现状`、`3 评述`、`4 参考文献`，二级标题随当前研究主题自拟。正文段落以研究证据开展综合评述，不是技术手册复述或论文标题堆砌。
6. **正文引用必须是真正的 Word 上标**：例如在句末以独立 `run.font.superscript=True` 写入 `[1]`、`[2,3]`，**不能**仅提高字号或用 Unicode 上标字符代替；文后参考文献列表 `[1]` 则为**正常基线**，逐条检查标号连续、对应、去重，不能有 Word 域错误 `Error! Reference source not found`。
7. **指导教师审阅意见按四范本归纳的学校语体提供拟稿**（不少于50字）：第三人称“该生”→文献检索/理解→研究现状及课题结合→综合评价。拟稿可参考范本收束语，但**不表示真实教师已审阅或批准**，签字与年月日留空，最终由教师审定。见 `references/genre-and-example-rules.md`。
8. **不得为“形似”迁移旧样本私人资料、技术结论、参考文献错误或虚假事实**。项目硬件/方案/已完成状态依据当次技术文档和项目事实资产；拟实现、已实现、预期测试必须区分；不附加“已知问题与改进建议”独立章节。
9. **完成后先检查再汇报**：结构检验 → DOCX 转 PNG 逐页实际看图 → 封面局部放大检查双行题目、同起止下划线、每处中英文下沉/重叠 → 文献上标及尾页导师意见检查；修改后重新渲染。禁止单凭代码断言“截图已检查”或未经 WPS 实测宣称 WPS 正常。
10. **用户验收权最高**：Agent 负责完成、核对并如实汇报，不声明学校或用户已经验收；新版本 `-v2/-v3` 等不覆盖旧成品；临时文件仅清理本轮有所有权标记的运行区。
11. **实质性分页门禁：页数本身不是目标，按当次内容的自然排布判断**。官方空白模板的页数**仅是参考**，成品页数随正文（≥2500 有效字）自然排布，**不得为凑足或压缩到某个页数而增删事实、稀释或堆砌文字**。硬性 FAIL 只有两类：为凑/压页数增删事实或破坏官方固定版式；最后一页只剩签名/日期或整页空白（孤页）。逐页截图核对页数与孤页；出现孤页先调整正文措辞与段落分配（只动可填正文，不改官方框架），只删真正冗余措辞——≥2500 字与真实文献是底线；仍无法消除孤页、或内容确需长于模板基准时，如实向用户说明并请求判断，不得静默缩小字号、行距硬塞页数。

## 1｜资产包：数据 + 成品 + 运行区

```text
<ProjectRoot>/                               # 同一个毕业设计项目的唯一根目录
├── project-assets/                        # 数据层：多个 Skill 共同维护，不可删
│   ├── project.json                       # project_id、姓名/学院等已确认元数据
│   ├── facts.json                         # FACT-xxx：项目事实、来源与状态
│   ├── references.json                    # REF-xxx：真实文献、核验时间与来源
│   ├── schedule.json                      # 同一份项目级周计划基线（本 Skill 只读）
│   └── activity.jsonl                     # 每次新增/变更/成品使用审计
├── deliverables/                          # 成品层：版本保存，不互相覆盖
│   ├── technical-document/
│   ├── taskbook/                           # 任务书 Skill 写，本文仅可读
│   ├── literature-review/
│   │   ├── <课题简称>-文献综述-v1.docx
│   │   └── <课题简称>-文献综述-v2.docx
│   ├── proposal/
│   └── midterm/
└── .skill-tmp/                             # 运行层：运行完清理本次目录
    ├── thesis-taskbook-write/             # 不碰其他 Skill 的运行区
    └── literature-review-write/<run-id>/  # 只有本 Skill 创建、可清理
```

- `project-assets/` 放项目根目录，不放 `.claude/skills/` 或 `.agents/skills/`；**Skill 安装包中的参考范本永不存项目事实**。
- 第一次运行且无资产：用 `project_assets.py init` 初始化；**已存在则先 status、逐项复用，严禁重新初始化/覆盖**。`project_id` 不一致直接停止。
- `facts.json` 采用 `implemented / declared / unverified / proposed`；新文书不改变旧事实的状态。若发现事实矛盾，记录冲突、找原资料核实，不能暗改。
- `references.json` 不能保存同一 DOI/同题目的重复条目；编号保持 `REF-xxx` 稳定。文书本地 `[1]` 与共享 `REF-xxx` 独立映射。
- `schedule.json` 只作一致性参考。文献综述不编写或修改项目周计划；其他 Skill 新计划应另走共享维护流程。
- `record-use --doc-type literature-review` 将最终 DOCX 路径、SHA-256、所用 `REF-xxx` 写入 `activity.jsonl`，新版本各登记一次。
- **最终版本唯一（每次执行只交付一份最终版本）**：执行内发现缺陷需修复时，修复完成后生成修正版（如 `-v2`），随即将其**改名为本轮应交付的版本名**（如 `-v1`，先删缺陷稿再改名）；一次执行结束时交付目录里本次成品只保留一份最终版，过程稿、缺陷稿不与最终版并存。缺陷稿不是历史版本，按此回收不算违反"永不覆盖、永不删除"；若缺陷稿曾 `record-use` 登记，回收后以最终定名文件 `--replace --reason` 补登记。跨次执行不受影响：内容变更或用户要求重新生成时仍递增产出 `-v2`、`-v3`…并各自登记。
- 成功或失败都清理**本轮**`.skill-tmp/literature-review-write/<run-id>`，不删源文件、文献库、原模板、已交付历史版本。具体见 `references/shared-project-assets-contract.md` 和 `references/asset-integration.md`。

## 2｜输入、缺失策略与真实性

**必要**：当前课题技术资料（MD/DOCX/PDF 或源码事实报告）、当前官方 DOCX（若未上传可用本包内随附的当前官方模板）、项目根目录/资产包。**可选**：文献综述范本、已核验文献/论文链接、用户确认的封面资料、写作细节要求。

先提取**课题事实矩阵**：研究对象及场景 → 具体工程问题 → 主控制器与感知技术 → 通信/云端方案 → 与现有研究可比较的维度 → 实现状态与证据 → 需要从论文查证的论点。所有外部扩展标注为研究背景或拟议，不擅称项目已实现。未知姓名、学号、学院、导师、职称、时间一律留空；不得拿匿名范本覆盖。

**特别区分**：对当前胡杨林课题，可讨论 STM32、温湿度/粉尘/土壤/火焰感知、4G/MQTT、短信告警的相关研究，但不默认其他新项目使用这些器件，更不能把技术文档中的预期指标写成实测成果。

## 3｜逆向写作：从“例文”提炼方法，不抽取隐私或复制研究内容

1. **抽取固定框架**：读取官方模板的 `sectPr`、封面既有段落、页码、唯一两行一列表格的 `tblPr/tblGrid/trPr/tcPr`、说明文字及教师意见签字日期；输出只读结构报告。**实测本次模板：2节、1张2行×1列表格；表格第1行含说明与正文，第2行含审阅区。**
2. **对多个例文做共性矩阵**：四份范本中多数采用“引言/国内外研究现状/评述/参考文献”；一份把“设计内容”单独展开，但不是官方强制项。通常由研究问题引入→分类比较国内外文献→作出限定性的总结与技术切入点；教师意见为独立一个自然段。详见 `references/genre-and-example-rules.md`。
3. **求同存异**：官方明示的格式不可变；官方没有规定的标题措辞或二级节次，优先多数范本共性与学术合理性；少数例文的奇怪空行、重复论文、乱码或不匹配论据一律不继承；实质争议才询问用户。
4. **文体变换**：从技术文档提取研究主题，而不是把“模块实现”“JSON 字段”“测试用例”逐条直接移进综述。文献综述回答“别人做了什么、证据说明了什么、还存在什么限制、本课题据此如何设计”，不能变成产品说明书或申请书。
5. **参考范本**：优先阅读 `assets/reference-samples/sample-a-environment-monitor.docx` 至 `sample-d-mobile-inspection.docx` 四份脱敏范本，并用 `scripts/inspect_reference_styles.py` 只读统计；旧路径 `examples/anonymized-style-reference.docx` 仅为兼容保留。它们都是去掉学生/学号/导师等标识后的风格参照，**不是官方版式真源，也不是可抄袭的引用库**。其部分旧版格式/引文错误已明确列在 `references/genre-and-example-rules.md`，不可照搬。

## 4｜文献检索与共享入库（不能跳过）

- 先读 `<PROJECT_ROOT>/project-assets/references.json`：筛选 `verified=true`、`checked_at` 有值、主题相关、著录字段完整的条目；仅在缺相关论文时检索补充。
- 优先按研究问题设置检索组合：研究对象+监测/安全；核心算法/传感器+应用；通信协议+可靠性；国外对照；可跨领域选相关技术但必须解释迁移条件。
- 通过知网/万方/维普/出版社/学位论文库查文献基本信息，若有可访问正文、摘要、研究方法，则进一步核对论点；**只看到目录页就只支持论文存在，不能推断实验结论**。
- 核实并登记每条 `citation`, `source_url`, `source_type`, `verified`, `checked_at`, `tags`, `project_relevance` 与可选 `doi`、限制/不足；同名跨平台去重。由 `project_assets.py merge --kind references` 写入共享库，更新旧条目时须 `--replace --reason`。
- CSDN 可补技术实现（例如 HAL/通信调试），但不能虚称为期刊文章；期刊/学位论文仍应为主要论证来源。默认建议不少于8篇独立、真实、有用的正式文献，样本为11～15篇左右；**实际数量服从本次学校/用户要求，不为凑数造文献**。本包 `compose_review.py` 默认门槛为 8（可依真实校规调整，不可用假资料绕过）。
- 正文使用 `[[REF:REF-001]]` 标记项目 ID，由组装脚本按首次引用生成 `[1]` ...，最后填充脚本对正文这些标注设置 Word 上标；文后参考文献列表正常编号。

## 5｜正文结构和教师意见（框架稳定、内容因项目变化）

```text
1 引言
  研究对象与现实问题 → 研究需求与意义 → 相关技术发展背景
2 国内外研究现状
  围绕有研究证据的技术主题分段展开 → 国内外对比 → 方法、效果及局限
3 评述
  已有工作取得的进展 → 与本课题相关的客观约束 → 本方案的合理选择及待验证事项
4 参考文献
  [1] ...
  [2] ...
指导教师审阅意见：（不少于50字）
  该生围绕…选题，能够查阅并整理…文献…把握现状；综述结构完整、条理清晰，
  引用文献真实可查，写作规范；能够结合选题分析…不足…技术路线与待验证事项。
  建议按计划进入毕业设计下一阶段工作，最终评价以指导教师审定为准。（供教师审定拟稿）
指导教师（签字）：（保持原位，空白）
年    月    日（保持原位，空白）
```

论文内容与研究证据相关联，禁止重复堆砌段落凑字数。技术事实必须有来源。**教师意见为“建议稿”**，不填真实签名、不自行盖章/写签署日期、不写“优秀/良好”等等级，形式与旧范本相近但评价必须针对实际写出的综述，不能只替换原项目名。写法按**教师意见拟稿统一规范（跨文书共用写法）**五要素链：①主体与选题→②能力→③文书质量→④针对性→⑤收束`建议按计划进入毕业设计下一阶段工作，最终评价以指导教师审定为准`；与任务书/开题/中期同源口径（本 Skill 四范本反向规则即该规范母版）。

## 6｜生成流程：原模板原位填写，不再“造模板”

**分节起草、分批写入（硬性，禁止一次性整篇生成）**：正文 `sections` 分批写入 `review-draft.json`——先写 1/2/3 主章标题骨架，再逐节成文（含二级小节），一节落盘后再写下一节；教师意见拟稿与引用映射单独成批。**禁止一次性生成整篇综述**。草稿全部落盘后 `compose_review.py`→`fill_review.py` 一次性填充，第 5/6 步（结构校验 + 逐页渲染分析）为**唯一终检**，写作中途不反复全文重检；终检问题只定点修订可填区内容后重新渲染复检。执行汇报注明分几节写入与一次终检结论。

**动笔前先摸口径，出片走两段式（防"验收器口味"与版本号烧号）**：

- **字数口径以最严者为准**：`compose_review.py` 的 2500 门槛**含标点**（去空白、去 `[[REF:…]]` 标记后计数），`validate_review.py` 的"2500 有效字符"**只算汉字/字母/数字（不计标点与引用编号）**——同一门禁两套口径。动笔前先对比生成/校验脚本的计数实现（先读后写），按**最严口径**写并留余量（余量大小按内容自然，不设死数字）；别按宽松口径压线，否则严格校验必挂、又烧一轮返工。
- **两段式出片**：先在本轮 `$WORKDIR` 构建运行区构建件（不带 `-vN`、不进交付区），`validate_review.py` + 逐页渲染分析都对构建件执行；**全部通过后**才移入 `deliverables/literature-review/<课题简称>-文献综述-vN.docx`（N=交付目录已有最大版本号+1，预检目录、禁止覆盖历史文件）。失败稿留在运行区随 `cleanup` 删除，**不进交付目录、不占版本号**。交付后才发现缺陷时按第 1 节"最终版本唯一"改名回收。

1. 使用 `scripts/inspect_template.py` 扫描模板，并通过 `scripts/template_tools.py` 与 `assets/template-lock.json` 校验真实 SHA-256；不相同直接拒绝而非猜测。只读保存模板原件。映射应与本次官方模板匹配：封面固定字段、题目两行位置、2节、1张2×1跨页表格、说明及签字区。
2. 在本次工作区生成 `review-draft.json`：课题题目、可选 **title_lines 必须拼回完整题目**、已知封面字段、正文 `sections`（固定1/2/3三个主章，二级标题可用 `{"text": "2.1 ...", "kind": "subheading"}`）、教师意见拟稿、引用以 `[[REF:REF-xxx]]` 表示。**禁止在草稿手填 `[1]` 等本地编号**。
3. `scripts/compose_review.py` 从共享 `references.json` 读取核验资料，验证每处引用来源，按**首现顺序编号**并生成本轮 `review-input.json`。**不修改共享项目文献原始编号、引用元数据或周计划**。
4. `scripts/fill_review.py` 仅在**实际官方模板的已存在段落与表格可填区域**写入：题目按原封面两行，使用居中制表位及制表符线条保持左右端点一致；留空的封面字段保留统一下划线；正文保留原说明段落、原 2 行 1 列表格、教师审阅标签和签字/日期。正文新增段落只在第一行可填区内，教师评语只在第二行可填区内。
5. `scripts/validate_review.py` 对原始 `sectPr`、官方固定段落 XML、表格/签字/日期 XML、正文 10.5pt 中西文字体、1.5倍行距、2500有效字符、所有 Word 引用上标（含 `[1,2]` 范围）、文后著录逐条验证；**脚本 PASS 只是程序结构通过**，不能代替视觉截图。
6. **实际渲染每页 DOCX**：`python scripts/render_visual.py --file "$TEMP_DOCX" --outdir "$WORKDIR/render"`（依赖 LibreOffice 和 PyMuPDF；或使用本机等价渲染工具），逐张看图、必要时裁剪放大封面及参考文献/教师意见。检查题目两行是否同中心、下划线是否同起止、线与字是否重叠、页码、字体、表格断裂、乱码、上标、孤行、签名日期。修复只允许动可填区域，修后再全部渲染。若某个一级标题孤立在页末，可先尝试对该节草稿设置 `page_break_before: true`，但某些渲染器会忽略跨页表格中的分页指令；若截图仍有孤立标题，需要调整仅新增的正文分段并复验，未解决时明确报告 FAIL，不得碰官方模板分节/表格。**版式几何量测只是辅助，放大目检才是判定依据**：制表位引导线（tab leader）、下划线端点这类元素在 PDF 绘制层常不是整段矩形，`get_drawings`/宽度过滤可能漏测（实测踩过：差点误判"双行题目下划线不等长"，3× 放大目检才确认端点对齐）——"同起止/等长"类判定以裁剪放大目检为准，几何量测可继续用作初筛但不得单独定性；工具量不到 ≠ 版式有问题，量测与目检冲突时先放大复检再定性，不得仅凭残缺量测判 FAIL 或返工。
7. **全部通过后才定版号、才进交付区**：把运行区构建件移入 `<PROJECT_ROOT>/deliverables/literature-review/<课题简称>-文献综述-vN.docx`，N 在这一刻按交付目录已有最大版本号 +1 确定（预检目录、禁止覆盖历史文件）；`record-use` 登记本版 SHA256 与引用 `REF-xxx`；填写执行报告与未知项；最后 `cleanup` 安全清理本轮运行目录。

**不允许**保留用户可见 Word 的错误后只说“各端软件有差异”。渲染无法修好就如实标明未通过，不可虚报成功。只有**真正使用 WPS**检查后，才可写“WPS 已验证”；用 LibreOffice 等兼容渲染器则必须写“未在 WPS 客户端实测”。

## 7｜Codex / Claude Code 可执行命令

```bash
# 进入安装的 literature-review-write/ 目录，PROJECT_ROOT 是真实项目根目录
python -m pip install -r requirements.txt

# A. 第一次 init；已存在的同一项目直接用 status，不覆盖
python scripts/project_assets.py init --root "$PROJECT_ROOT" \
  --project-id "$PROJECT_ID" --name "$PROJECT_NAME"
python scripts/project_assets.py status --root "$PROJECT_ROOT"

# B. 创建本轮有所有权标记的临时运行区，记下输出 WORKDIR 与 RUN_ID
python scripts/project_assets.py workdir --root "$PROJECT_ROOT"
python scripts/inspect_template.py assets/official-literature-review-template.docx \
  --json "$WORKDIR/template-inspect.json"
python scripts/inspect_reference_styles.py --report "$WORKDIR/style-audit.json"

# C. Agent 在 WORKDIR 构建真正的 review-draft.json；读现有 references.json，
#    不足时依据检索来源新增，并先 merge 到共享资产库（不能用模拟文献）
python scripts/compose_review.py --root "$PROJECT_ROOT" \
  --draft "$WORKDIR/review-draft.json" --out "$WORKDIR/review-input.json"

# D. 两段式：先以官方原模板为底稿填充到运行区构建件（不带 -vN、不进交付区），
#    输出路径不得与官方模板或任何旧版成品相同
python scripts/fill_review.py --template assets/official-literature-review-template.docx \
  --data "$WORKDIR/review-input.json" --out "$WORKDIR/build.docx"
python scripts/validate_review.py --template assets/official-literature-review-template.docx \
  --file "$WORKDIR/build.docx" --data "$WORKDIR/review-input.json" \
  --report "$WORKDIR/validation.json"

# E. 逐张打开 render 中的页面 PNG 进行真正视觉分析（对运行区构建件执行）
python scripts/render_visual.py --file "$WORKDIR/build.docx" --outdir "$WORKDIR/render"
# 需要逐页真正打开渲染 PNG；预检 JSON 中的 PENDING 不是通过

# F. 全部通过才发布和登记：此时才移入交付区定 -vN（N=目录已有最大版本号+1，
#    预检目录、禁止覆盖历史文件；失败稿留在运行区随 G 清理，不占版本号）。
#    引用 ID 按 review-input.json selected_reference_ids 组装
mv "$WORKDIR/build.docx" "$PROJECT_ROOT/deliverables/literature-review/<课题简称>-文献综述-vN.docx"
python scripts/project_assets.py record-use --root "$PROJECT_ROOT" \
  --file "$PROJECT_ROOT/deliverables/literature-review/<课题简称>-文献综述-vN.docx" \
  --doc-type literature-review --ref-ids "REF-001,REF-002"

# G. 最后清理本轮专属运行区（成功/失败均执行，不清理历史版本或资产）
python scripts/project_assets.py cleanup --root "$PROJECT_ROOT" --run-id "$RUN_ID"
```

**路径示例是命令形状，不是实际文件路径**。填充脚本只支持经扫描验证的本次官方模板；如用户给出的官方模板与本包底稿不同，必须先重新建立“只填可写位置映射”并补自动化测试，而不是临时重建官方格式。

## 8｜回归稳定性与验收

每次修改本 Skill 后运行：`python tests/smoke_test.py` 与 `python tests/test_regression.py`。后者必须拒绝：改过的官方模板、覆盖已有成品、非上标引用、教师固定栏目篡改、直接手填 `[n]` 引用。程序测试使用 2099 年及 example.invalid 的**纯虚构**资料，不能用作正文论据。打包后检查 ZIP 完整性、官方 SHA、四份样本中的身份信息是否已经脱敏；如修改涉及版式，必须重新生成测试 Word 并截图查看。

## 9｜验收门槛与执行报告

参考 `references/quality-gates.md`、`references/format-reverse-engineering.md`、`references/sample-style-audit.json` 和 `templates/execution-report.md`。正式交付前必须满足：真实技术事实、正文≥2500、正文引文均上标且对应真实已核验文献、封面无示例私人数据、教师评语拟稿≥50、原官方签字日期没变、原 DOCX 两节一表框架保留、逐页 PNG 已实际查看、仅本轮临时目录清理。

**报告要写实**：成品路径及 `-vN`、技术资料来源、复用多少/新增多少 REF-ID、正文实际字符数、文献数量及状态、各章结构、教师拟稿状态、审计结果、截图页数/逐页 PASS-WARN-FAIL、是否实际用 WPS 检查、未知/留空字段、是否清理临时目录。**最终验收由用户和真实指导教师决定。**
