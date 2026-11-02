# opening-report-writer｜毕业设计开题报告专用 Skill

**结构参考**：`thesis-midterm-check-write-v1.3` 的“官方模板锁→匿名范本清单→体裁逆向→共享项目资产→结构校验→全页截图→安全清理”。**内容边界不借用中期表**：本 Skill 只写《开题报告》。使用当前项目技术文档作为事实、正式论文与官方资料作为外部证据。

## 安装

解压后把整个 `opening-report-writer/` 目录放入 Claude Code 的 `.claude/skills/` 或 Codex 的 `.agents/skills/`。Skill 名保持为 **`opening-report-writer`**，兼容 V3.4 的调用方式。运行脚本需要 Python 3.10+、`python -m pip install -r requirements.txt`；逐页 PNG 检查还需要 `PyMuPDF`；DOCX→PDF 转换链依次探测 soffice（LibreOffice）→ Word COM → WPS COM，亦可 `--pdf` 直通已转换 PDF。

**不要把项目数据放进 Skills 安装目录**。一个项目用一个 `<PROJECT_ROOT>/` 资产包，包含 `project-assets/`（数据）、`deliverables/`（成品）、`.skill-tmp/`（本轮运行区）。任务书/技术文档/开题/中期等 Skill 共用项目身份、事实、文献和唯一周计划，却分别负责自己的官方模板和填充代码。

## 工具包结构

```text
opening-report-writer/
├── SKILL.md                            主要执行契约；0~7章与中期Skill同风格
├── README.md  VERSION.md  manifest.txt requirements.txt
├── assets/
│   ├── official-opening-report-template.docx  官方空白原件（绝不修改）
│   ├── template.sha256  template-lock.json    官方哈希与结构锁
│   └── reference-samples/
│       ├── README.md  samples-manifest.json   脱敏样本规则与清单
│       ├── SAMPLE-A.sha256                   脱敏样本哈希
│       └── sample-a-smart-interaction-anonymized.docx  已填写参考范本（非官方）
├── references/
│   ├── genre-reverse-engineering.md   逆向写作与求同存异
│   ├── v4-alignment-map.md           与中期Skill v1.3的形式对应关系
│   ├── sample-style-audit.json         样本格式结构化测量
│   ├── anonymized-sample-usage.md      可借鉴写法/禁止复用事实
│   ├── technical-input-and-writing.md  技术事实状态与章节写法
│   ├── template-boundary-and-layout.md 官方固定/填写/呈现三层保护
│   ├── official-template-invariants.md 官方模板OOXML检查
│   ├── literature-policy.md           论文网站、核验与引用规则
│   ├── content-writing-guide.md       七章写作方法
│   ├── shared-project-assets-contract.md 共享项目资产兼容协议
│   ├── intermediate-cleanup-policy.md 临时文件安全清理
│   ├── report-json-contract.md        结构化内容接口
│   ├── quality-gates.md               QA门禁
│   └── integration-contract.md        跨Skill接口
├── templates/
│   ├── input.schema.json  execution-report.md  evidence-register.md
│   └── cross-skill-integration-snippet.md
├── examples/report-input.example.json 仅供字段理解的虚拟结构样例
├── scripts/
│   ├── inspect_template.py  inspect_reference_styles.py
│   ├── check_reference_example.py sanitize_reference_sample.py
│   ├── build_report.py check_report.py render_visual.py check_render.py
│   └── project_assets.py
└── tests/                        离线测试和缺陷回归（不作为论文来源）
```

## 一次性执行流程

1. 从本次技术资料及 `project-assets` 读取项目真实事实、REF、FACT和计划，确认 project_id。
2. 先审计官方空白 DOCX 与锁，后阅读 `reference-samples` 的匿名范本规则；先学写法，不搬人物/历史项目事实。
3. 检索并核对不少于10项真实参考文献（优先知网/万方/维普/IEEE/ACM/出版商官网；CSDN仅限少量工程经验），编写学校要求的七部分≥3000汉字正文，形成运行目录的 `报告内容.json`。
4. `build_report.py` 从官方原件副本填充；`check_report.py` 严查七章、字体/行距/正文缩进、引文真上标、文末单次编号及固定模板结构。
5. `render_visual.py` 生成每一页 PNG 与 PDF，Agent逐张打开检查；出现孤立签名或其他视觉问题优先调新写入正文，不改学校固定排版。
6. 保留同一 `-vN` 版本的开题DOCX、执行汇报、文献核验台账，合格后 `record-use`，最后删除**本轮有所有权标记**的 `.skill-tmp` 运行目录。历史版本和共享资产永久保留。

## 快速调用

```text
使用 opening-report-writer Skill。请读取我这次给你的项目技术文档和现有 project-assets，
先锁定内置官方空白开题报告模板，再按内置匿名已填范本逆向规则组织写作。
只生成开题报告，不生成技术文档/中期表；七部分齐全、正文至少3000字，
参考文献至少10篇并逐条核验，正文真上标，文末单次编号、左对齐悬挂缩进、1.5倍行距。
在官方模板副本写入，不改表格和签字栏。执行结构检查与每页截图检查，
最终交付带-vN的 DOCX、执行汇报、文献核验台账，清理本轮中间件，由我最终验收。
```

## 回归与限制

执行 `python -m unittest discover -s tests -v`，再运行 `python scripts/check_reference_example.py`。测试用例中的论文是 `.invalid` 测试占位，**不得用于真实参考文献**。程序不会联网搜索或读取知网付费全文，也不能单凭字数脚本证明文学研究内容准确；生成时实际的文献核验和逐页检查由 Agent 完成。未在 WPS 实际打开不可声称 WPS 验收通过。

**与原 V3.4 的升级关系**：保留 `opening-report-writer` Skill 名、`project-assets` v1 数据结构、`.skill-tmp/opening-report-writer` 所有权标识和已有 CLI；将原 `examples/` 参考 DOCX 迁入 `assets/reference-samples/`，增加目录清单/模板锁/体裁统计/可视 QA 脚本及正文缩进严格检查。完整说明见 `VERSION.md`。
