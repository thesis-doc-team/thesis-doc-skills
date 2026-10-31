# 结构化正文 JSON 契约（Agent → 官方 Word 填报器）

本数据是**构建阶段的内容中间件**，不是要提交给学校的文档。生成器只负责把已有真实文本填到官方模板中，不会帮你创作论文或检索资料。

## 输入对象

```json
{
  "cover": {
    "title": "<以当次项目为准>",
    "student_name": "",
    "student_id": "",
    "college": "",
    "major": "",
    "class_name": "",
    "supervisor": "",
    "supervisor_title": "",
    "date_range": ""
  },
  "sections": [
    {
      "id": 1,
      "title": "课题研究立项依据",
      "blocks": [
        {"type": "heading2", "text": "1.1 课题背景"},
        {"type": "paragraph", "text": "<以当前技术文档和真实引用支持的内容编写>[[cite:1]]"},
        {"type": "heading2", "text": "1.2 研究目的和意义"},
        {"type": "paragraph", "text": "<请据实编写>"}
      ]
    },
    {"id": 2, "title": "国内外研究现状及分析", "blocks": ["<同样结构的 blocks>"]},
    {"id": 3, "title": "课题任务要求及实现预期目标的可行性分析", "blocks": ["<同样结构的 blocks>"]},
    {"id": 4, "title": "重点研究的问题及解决思路", "blocks": ["<同样结构的 blocks>"]},
    {"id": 5, "title": "完成课题所需工作条件及解决办法", "blocks": ["<同样结构的 blocks>"]},
    {
      "id": 6,
      "title": "工作方案及进度计划",
      "blocks": [
        {"type": "heading2", "text": "6.1 工作方案"},
        {"type": "paragraph", "text": "<写真实技术路线>"},
        {"type": "heading2", "text": "6.2 进度计划"},
        {"type": "schedule", "items": [
          {"start_week": 1, "end_week": 2, "task": "<对应真实任务书的阶段目标>"}
        ]}
      ]
    },
    {"id": 7, "title": "主要参考文献", "blocks": []}
  ],
  "references": [
    {
      "text": "作者. 经核实的论文题名[J]. 真实期刊, 实际年份, 真实卷(期): 实际页码.",
      "source_type": "journal",
      "source_url": "https://<已实际访问并核实的来源 URL>",
      "verified": true,
      "checked_at": "YYYY-MM-DD"
    }
  ]
}
```

该 JSON 只是**字段示意**，参考文献必须填入当前任务真正核实过的 10 篇以上完整条目；不得以示例内容制作论文参考文献。

## 字段规定

### cover

所有字段都可不填：未提供的个人信息保留原始下划线。**不要猜测学生名字、学号、导师或学校任务日期**。`title` 应对应本次课题。

### sections

必须恰好 7 条、`id` 按 1～7 排序。一级标题默认与 `scripts/build_report.py` 内的七章预设字面完全相等。`blocks` 可包含：

- `heading2` 二级标题：文字里手写 `1.1 ...` 这样的层级编号，生成时保留。
- `heading3` 三级标题：可选，同一文档层级编号一致。
- `paragraph` 普通正文段，默认首行缩进约 2 字。
- `schedule` 仅用于工作计划，`items` 的周次由生成器自动改写成 `第1周--第2周：具体任务`。

第 7 章的 `blocks` 固定为空，文末条目只由 `references` 自动生成，以防重复编号。

### references

每条文献必须：`text`（完整人工整理著录，**无 `[n]` 前缀**）、`source_url` 或 `doi`、`verified: true`、`source_type`。`source_type` 取：`journal`、`conference`、`thesis`、`standard`、`official_doc`、`book`、`blog`。文献按正文第一次引用顺序排序。没有真正核实的论文不得标记 `verified:true`。

### citations

只用 `[[cite:1]]`、`[[cite:1-2]]`、`[[cite:1,3]]` 的标记方法。正文中的普通 `[1]` 被判为错误，因其并非真正 Word 上标。生成器产生 `w:vertAlign=w:superscript` 的 Word 格式，而不是通过 Unicode 字符模拟上标。

## 检查强度

- `build_report.py` 在构建前检查七章、10+文献、引文范围、至少 7 项较可靠文献、博客≤2，文献有来源定位并由 Agent 标记已经核实。
- `check_report.py` 在构建后核对模板、7 章、编号、引用上标、行距、字号/字体、3000 汉字以及固定结构。
- 真实参考文献是否存在、引用是否支持论点、用户是否认可正文，需要 Agent 的来源核对和用户最终验收，不能由数据格式自动保证。

## 输入文件和运行

```bash
python scripts/build_report.py ./output/opening-report/报告内容.json \
  --output ./output/opening-report/开题报告.docx
python scripts/check_report.py ./output/opening-report/开题报告.docx \
  --json ./output/opening-report/报告内容.json \
  --output-report ./output/opening-report/结构校验.json
```

**运行前需准备真实填写完毕的 JSON。** Agent 按 Skill 自动准备，不要求用户手工理解这些字段。
