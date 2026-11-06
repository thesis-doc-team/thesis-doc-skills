# 安全清理与历史版本保留

## 成品命名

`deliverables/project-introduction/<项目简称>-项目介绍与功能说明-v1.md`

`deliverables/project-introduction/<项目简称>-项目介绍与功能说明-v1.html`

`deliverables/implementation-plan/<项目简称>-工程实施方案-v1.md`

重新生成从现有最大 `vN` 往上加，不覆盖同名历史成品。用户仅要求修订其中一份时，只给那一份递增版本，另一份不无故重生成。介绍 HTML 与同版本介绍 MD 共用 `-vN`；介绍 MD 改动后必须重新生成 HTML，HTML 视觉调整不得反向改写介绍 MD 或工程实施方案。

## 临时文件边界

草稿、临时复制件、截图、QA JSON、索引缓存全部放 `.skill-tmp/project-solution-write/<run-id>/`（`workdir` 创建，带 `.owned-by-project-solution-write` 标记，内容为技能名）。`cleanup --run-id` 只删该带标记的单个目录，遇符号链接、路径越界或标记不符一律拒绝；禁止通配符删除 `.skill-tmp/` 整体、用户原件、其他运行目录。

## 执行报告

**只在聊天回复汇报结果**：生成了哪两份 MD 与哪一份 HTML（或指定范围）、核验情况、HTML 静态与视觉检查结果、当前无法实测的事实限制、重要未确认前提。执行日志不属于正式项目介绍、介绍 HTML 或工程实施方案正文。
