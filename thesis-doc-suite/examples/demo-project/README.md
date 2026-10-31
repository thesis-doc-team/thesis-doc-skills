# 示例项目（纯合成数据）

本目录是一个**脱敏示例项目资产包骨架**，演示 `project-assets/` 数据层各文件的格式，供学习与测试参考。

> ⚠️ **重要**：本目录所有内容均为**纯合成数据**（日期用 2099 年、URL 用 `example.invalid`、姓名用"示例学生/示例作者"）。**不得**把这些条目当作真实文献、真实技术事实或真实个人信息使用，也不要把示例 REF/FACT 直接复制进你的真实项目资产。

## 目录结构

```
demo-project/
├── README.md                ← 本说明
└── project-assets/          ← 数据层示例（合成）
    ├── project.json         ← 项目身份
    ├── facts.json           ← 技术事实 FACT-xxx（结论 + 出处 + 状态）
    ├── references.json      ← 参考文献 REF-xxx（元数据 + 核验状态）
    ├── schedule.json        ← 项目级周计划基线
    └── activity.jsonl       ← 审计流水示例（追加写，每行一个 JSON 事件）
```

正式使用时，资产包由 `/thesis-doc-suite:init-project` 在**你的项目根目录**创建，还会包含 `deliverables/`（成品层）与 `.skill-tmp/`（运行层）。各字段含义与读写规则见 [../../docs/asset-management.md](../../docs/asset-management.md)。

## 在临时目录试跑（不会污染本示例）

```bash
# 复制到临时位置再实验
xcopy /E /I demo-project C:\Temp\demo-try
python ..\..\core\asset-management\project_assets.py status --root "C:\Temp\demo-try"
```

预期输出：`project_id=DEMO-2099-ONLY`、文献 2 条（已核验 1 条）、事实 3 条、周计划 `PLAN-DEMO-2099`（draft，18 周 4 阶段）。
