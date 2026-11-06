# project-solution-write | 毕设选题探索、候选资产管理与正式方案（V1.4.2）

## 默认用途：帮学生找毕业设计/课程设计题目

**默认入口只有一句话**：你想找什么方向的毕设/课程设计题目？专业、技术偏好、已有的开发板/传感器/实验室条件可以直接说。不需要先选“专业/技术/题目”模式——这些只是内部路由。

- 每批最多 10 个候选；每个候选独立生成 `项目概览.md / 项目概览.docx / 项目概览.html`（只有名称、概述、核心功能）。
- 毕设/课程设计候选默认至少 5 条完整闭环功能、有具体应用场景、使用现成模块、单板/小装置可完成；不要求自绘 PCB、不做大型部署。
- **不主动询问经费或工期**；通过“模块化、单板、功能数量、场景具体性”表达规模边界。
- 用户确认题目与功能后，才进入正式方案：介绍 MD + HTML + 实施 MD。

## 适用范围

将确认后的项目题目与功能转换为两份相互关联、**内容边界严格分离**的 Markdown，并以介绍 MD 为唯一内容源生成**统一视觉、离线可打开、响应式**的项目介绍 HTML。正式阶段在题目/功能齐全后给予用户**成本优先 / 性能优先 / 功能优先 / 均衡方案**四种设计目标选择，Agent 根据选定侧重探索实质不同的候选路线，记录**优先目标→选型变化→取舍代价→实施与验收**；写正文前执行**设计冻结**，写正文时按章节**分批落盘 → 一次组装 → 一次终检**。

1. `<项目>-项目介绍与功能说明-vN.md` —— 面向项目阅读与展示，侧重做什么、功能和体验。
2. `<项目>-项目介绍与功能说明-vN.html` —— 介绍 MD 的可视化表达，单文件离线打开；只复述介绍内容，不引入实施细节。
3. `<项目>-工程实施方案-vN.md` —— 面向实施者，侧重为什么、怎么选、怎么连、怎么设计、怎么逐步验证。

此 Skill **仅生成选题候选文档及正式方案文档，不执行研发、部署、购买、代码修改或实物验收**；不存在无条件生效的固定硬件模板。

## 启动方式

**可以只说“使用 project-solution-write”。** Agent 直接问你想找什么方向的毕设/课程设计题目，并接受专业、技术偏好、已有开发板/传感器与大致想法混合输入；不要求你选择入口。确认题目与功能后才进入正式方案；此时才需要完整功能清单与设计侧重。

例如首次调用：

```text
请使用 project-solution-write。
```

预期回复：“你想找什么方向的毕设/课程设计题目？专业、技术偏好、已有的开发板或传感器都可以直接告诉我。”

正式方案阶段的示例：

```text
请调用 project-solution-write，为【项目名】编写项目介绍和工程实施方案。
功能树：……
设计侧重：成本优先 / 性能优先 / 功能优先 / 均衡方案（未写则让你提供一次选择）
硬性约束：……（可选，例如已有主控/传感器/必须使用的技术）
先筛选可实施路线并说明取舍，再生成独立的两份 MD 与介绍 HTML；不要真正开发项目，不要写收费/交付包装或后续建议章节。
```

## 探索模式用法（候选资产独立保留）

```bash
# 1. 可使用 route_project_intent.py 检查当前输入适合探索还是正式
python scripts/route_project_intent.py --input /path/to/user-input.json
# 2. Agent 结合已知约束和历史拒绝记录创建批次 JSON，最多 10 个候选
python scripts/discovery_registry.py batch --root "$WORKSPACE_ROOT" --input templates/discovery-batch.example.json
# 3. 标记感兴趣与功能补充，生成新版本并保留旧版
python scripts/discovery_registry.py set-status --root "$WORKSPACE_ROOT" --project-id PROJECT-0001 --status interested
python scripts/discovery_registry.py revise --root "$WORKSPACE_ROOT" --project-id PROJECT-0001 --input templates/discovery-revision.example.json
# 4. 拒绝题目后记入持久去重库
python scripts/discovery_registry.py set-status --root "$WORKSPACE_ROOT" --project-id PROJECT-0002 --status rejected
# 5. 用户明确确认题目与核心功能后，才能开始正式工程方案
python scripts/discovery_registry.py set-status --root "$WORKSPACE_ROOT" --project-id PROJECT-0001 --status confirmed --user-confirmed
```

候选版 DOCX 的生成依赖 `python-docx`（见 `requirements.txt`）；原正式方案的 MD+HTML 生成器仍只用标准库。`discovery/` 和 `projects/PROJECT-xxxx/` 属于用户工作区，不属于 Skill 安装目录。每个候选三个文件必须内容一致，版本更新不覆盖原件。

## 目录说明

| 目录/文件 | 用途 |
|---|---|
| `SKILL.md` | 选题信息混合路由、候选与正式双阶段、执行顺序、质量门禁 |
| `references/` | 需求澄清、**设计目标选择、候选路线深度探索与取舍追踪**、**写前设计冻结与跨文档一致性**、**分批写入与一次终检**、**HTML 视觉规范/内容映射/质量检查**、硬件与软件推导、事实引用、成文规则 |
| `assets/reference-samples/` | 四类匿名化工程案例 + 用户认可的 HTML 视觉参考，**仅参考设计方法/样式**，不作为新项目事实来源 |
| `templates/` | 两份 MD 结构、需求矩阵、**四选项聊天模板与候选决策追踪模板**、**设计冻结表**、**单文件 HTML 模板**、输入 schema、执行反馈模板 |
| `scripts/route_project_intent.py` | 先判别专业/关键词/想法入口或正式方案 |
| `scripts/discovery_registry.py` | 候选批量生成、拒绝去重、状态/版本/内容资产管理 |
| `scripts/render_candidate.py` | 每个候选同源生成 MD、DOCX、离线 HTML |
| `scripts/check_input.py` | **仅正式方案**核对题目和功能，缺项才询问 |
| `scripts/project_workspace.py` | 可选的项目资产包初始化/身份核验/下个版本查询 |
| `scripts/compose_markdown.py` | 按文件名顺序组装分批 MD 草稿；检查单一 H1、章节结构与批次数量 |
| `scripts/validate_docs.py` | 两份 MD 的静态越界、结构和需求覆盖初检 |
| `scripts/generate_intro_html.py` | 介绍 MD → 结构化数据 → 单文件 HTML；只读介绍 MD |
| `scripts/validate_intro_html.py` | 介绍 HTML 的离线、安全、内容边界、功能一致性与场景标注检查 |
| `tests/` | 标准库 unittest 回归测试（含 HTML 三类项目、动态数量、XSS、缺失章节、分批组装） |
| `VERSION.md` | 版本与适用范围 |

## 工程定位和边界

- 只做项目方案；不是技术文档逆向整理、毕业文书填充或真实工程开发 Skill。
- 不把用户未要求的传感器、云平台、数据库、RTOS、视觉识别等自动加成正式功能；功能优先也不得越界。
- 成本、性能、功能、均衡四种倾向必须驱动可解释的设计取舍，并写出实际影响、代价和验证指标；若不同目标确实同解，说明原因而不是假造差异。任何选择都不能违反安全和已确认需求；未经核实的价格、性能不得伪造。
- 正式 MD 不要出现“工程实施交付说明、免费/付费介绍、收费策略、已知问题与改进建议、后续扩展建议”等元内容。
- 介绍 HTML 只读取同版本介绍 MD，不读取工程实施方案；不出现 GPIO/引脚/接线/协议帧/代码/密钥/部署命令；统一视觉、单文件离线、响应式；缺失章节隐藏，场景示意固定标注“未实测”。
- 介绍与实施均按章节分批写入（各建议至少 4 批），每批落盘后再写下一批；全部落盘后用 `compose_markdown.py` 一次组装，随后一次终检；禁止一次性整篇生成。
- 只有项目材料确有依据时才可以写“已实现/已实测”；否则写“拟采用/待验证”。
- 仿照原参考 Skill 的目录分层和跨 Skill 项目资产意识，但**不携带其官方 Word 模板或学校专用检查规则**。

## 简易质量检查

```bash
python scripts/check_input.py --input /path/to/current-project-input.json
# 若提示 NEEDS_INPUT，请先向用户询问缺少的项目题目/功能，不要继续生成。
python scripts/validate_docs.py \
  --intro /path/to/project-intro.md \
  --implementation /path/to/implementation.md \
  --title '项目题目' \
  --report /path/to/qa.json
python scripts/compose_markdown.py \
  --parts-dir /path/to/batches/introduction \
  --out /path/to/project-intro.md \
  --kind introduction --title '项目题目' \
  --report /path/to/compose-intro.json
python scripts/compose_markdown.py \
  --parts-dir /path/to/batches/implementation \
  --out /path/to/implementation.md \
  --kind implementation --title '项目题目' \
  --report /path/to/compose-impl.json
python scripts/generate_intro_html.py \
  --intro /path/to/project-intro.md \
  --out /path/to/project-intro.html \
  --data-out /path/to/project-data.json
python scripts/validate_intro_html.py \
  --intro /path/to/project-intro.md \
  --html /path/to/project-intro.html \
  --report /path/to/html-qa.json
python -m unittest discover -s tests -v
```

静态初检无法验证电气连接或真实 API。人工技术核对仍是必要门禁，最终验收由用户判断。HTML 静态 PASS 也不等于浏览器视觉验收；有 Chrome/Edge 时应补桌面/移动截图检查。
