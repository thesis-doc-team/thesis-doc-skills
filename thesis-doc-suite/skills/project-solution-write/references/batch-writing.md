# 分批写入与一次终检（硬性，禁止一次性整篇生成）

## 一、为什么

两份 Markdown 和派生 HTML 都可能很长。一次性整篇生成容易出现截断、漏章节、跨文档引用漂移，也会让审查变成反复全文重读。thesis-doc-suite 六件套统一采用“**分批落盘 → 组装 → 一次终检**”；本 Skill 按同一口径执行。

## 二、硬性规则

1. **介绍 MD 至少 4 批**：按 `00-meta`、`01-overview`、`02-scenarios`、`03-features`、`04-system-workflow`、`05-boundaries-demo` 拆分；功能很多时把 `03-features` 再拆成 `03a`/`03b`。每批写成独立 `.md` 片段，落盘后再写下一批。
2. **实施 MD 至少 4 批**：按范围/基线、架构/数据流、选型/资源、接口/连接、软件架构、核心功能、协议/数据、调度/可靠性、阶段实施、测试验收、技术依据拆分；每批落盘后再写下一批。
3. **禁止一次性倾倒整篇**：不得用一个超大写入调用生成整份介绍或整份实施；每批只写一个章节或一组紧密相关章节。
4. **单一 H1**：只有 `00-meta.md` 写项目一级标题；其余批次只写 `##`/`###` 章节，不重复 H1。
5. **组装后才做 HTML**：全部介绍批次落盘 → `compose_markdown.py` 组装 `draft-introduction.md` → 再用 `generate_intro_html.py` 生成 HTML；不得在批次未齐时生成 HTML。
6. **一次终检**：两份草稿组装完成后，运行 `validate_docs.py` + `validate_intro_html.py` + 人工一次性复核；**写作中途不反复全文重检**。终检问题只定点修受影响批次，重新组装；介绍 MD 改动后重新生成 HTML；不推倒全部草稿。
7. **执行汇报**：注明介绍/实施各分几批、每批包含哪些章节、一次终检的结论。

## 三、工作区布局

```text
<WORKDIR>/batches/introduction/
├── 00-meta.md
├── 01-overview.md
├── 02-scenarios.md
├── 03-features.md          # 功能多时可拆 03a/03b
├── 04-system-workflow.md
└── 05-boundaries-demo.md

<WORKDIR>/batches/implementation/
├── 00-meta.md
├── 01-scope.md
├── 02-architecture.md
├── 03-selection.md
├── 04-interfaces.md
├── 05-software.md
├── 06-functions.md         # 功能多时可拆 06a/06b
├── 07-protocol.md
├── 08-reliability.md
├── 09-stages.md
├── 10-tests.md
└── 11-sources.md
```

批次文件是内部草稿，不进入 `deliverables/`；`cleanup` 随运行区删除。最终成品只保留两份 MD 与一份 HTML。

## 四、组装命令

```bash
python scripts/compose_markdown.py \
  --parts-dir "$WORKDIR/batches/introduction" \
  --out "$WORKDIR/draft-introduction.md" \
  --kind introduction --title "$PROJECT_TITLE" \
  --report "$WORKDIR/compose-introduction.json"

python scripts/compose_markdown.py \
  --parts-dir "$WORKDIR/batches/implementation" \
  --out "$WORKDIR/draft-implementation.md" \
  --kind implementation --title "$PROJECT_TITLE" \
  --report "$WORKDIR/compose-implementation.json"
```

`compose_markdown.py` 只按文件名顺序拼接，不改写内容、不补写事实；检查：

- 每个批次是有效 UTF-8 且非空；
- 组装结果恰好一个一级标题；
- 至少有一个二级章节；
- 批次数量少于建议值时给出 WARN（不阻止小项目，但执行汇报必须说明）；
- 按 `--kind` 提示缺少的常见章节（介绍：项目概述/功能/使用流程；实施：范围/架构/实现/实施步骤/验收），不静默补写。

## 五、批次内容边界

- 每批只使用已确认的需求、设计冻结表和 `decisions.md` 中的结论；不得在某一批里新增功能、指标或实测结论。
- 介绍批次遵守介绍边界（不写引脚/接线/协议帧/代码/收费/后续建议）；实施批次遵守实施边界（不写商业交付/泛化建议）。
- 批次之间不重复整段内容；需要交叉引用时写“见第 X 节”，由最终文档的章节号统一。
- 失败或中断时，已落盘批次保留在运行区，下一轮可继续；不得把半成品复制进交付目录。

## 六、一次终检清单

1. 两份草稿的章节顺序、编号、术语、默认值一致。
2. 介绍 MD 与 HTML 的功能/场景/状态/“未实测”标注一致；HTML 只读介绍 MD。
3. 需求矩阵中每个 `confirmed` 功能在两份 MD 与 HTML 中可追踪。
4. 协议/数据/状态/资源在实施 MD 内部一致；不泄露到介绍与 HTML。
5. 运行 `validate_docs.py` 与 `validate_intro_html.py`；失败只修受影响批次并重新组装/生成。
6. 有浏览器时做桌面/移动视觉检查；没有则如实说明未做视觉验收。

## 七、与普通“重写一遍”的区别

- 分批不是把同一段反复重写，而是每批只落盘一次、一次组装；终检前不全文重读。
- 终检发现的问题只修对应批次，避免连锁返工。
- 批次文件与最终成品分开：最终成品不携带批次碎片，也不出现“本批/下一批”等过程语言。