# 浏览器截图验证：伪象、量测与探针写法（实战教训沉淀）

> 来源：真实交付复盘。内容生成链路（MD→HTML→对照校验）几乎不会出问题；出问题的全是
> **截图验证的测量假象**和**手写探针脚本**。本文件是 E5 截图验证分析的实施细则，
> 配套工具 `scripts/screenshot_audit.py`（仅标准库）。

## 1. 工具链现实与降级路径

- 有 Playwright/Selenium：正常驱动浏览器（点击、滚动、抓 Console），按 SKILL.md E5 三步走。
- 没有（最常见）：**无头浏览器 CLI + 向运行目录副本注入 JS** 也能完成大部分验证——
  抽屉态、搜索过滤态、空结果态都可以通过注入点击/输入事件实测。
- **降级边界要如实声明**：滚动高亮、阅读进度条这类"随滚动变化"的动效无法逐帧截图时，
  只能代码审查确认，执行汇报写"代码审查确认，未逐帧实测"，**不算截图验证通过项**。
  动效逐帧验证只有驱动级工具（Playwright 等）能做。

## 2. 三大截图伪象（都会诱导误判 FAIL）

### 2.1 Windows 无头 Chrome 的最小布局视口（约 512px）——最坑

- `--window-size=390` 拍出来的图**不是** 390px 布局：窗口被钳到约 512px 布局视口，
  截图只是把 512 宽的排版**裁**成 390 宽的图。标题/按钮"被切断"切的是图，不是页面。
- 误判过程实录：先当成移动端布局 FAIL 去查 CSS 疑凶（min-width 规则等），浪费大量时间。
- **判别法（量测先于定性）**：跑 `screenshot_audit.py probe --html <页面> --width 390`。
  探针用 **390px 固定宽度 iframe 强制真实移动布局视口**（iframe 内容盒宽度即布局视口宽度，
  不受窗口钳制），量 `body.scrollWidth` vs 视口宽：
  - `realHorizontalOverflow=false` 而截图右缘被切 → 裁切伪象，不是页面 bug；
  - `realHorizontalOverflow=true` → 真溢出，`overflowOffenders` 列出越界元素再定点修。
- 截图也要窄视口真图时，同样用 390px iframe 的 harness（`probe` 生成的 harness 即是）。

### 2.2 锚点截图永远从文档顶部开始

- 无头模式 `--screenshot` 忽略 URL 锚点和 `scrollIntoView()`——三张"不同章节"截图
  可能字节级相同（实测踩过：三张全一样=全都没滚）。
- **判别法**：截图后先跑 `screenshot_audit.py dupcheck <截图...>`，相同哈希 = 拍摄失败，
  必须重拍，不能解释成"两章排版一致"。
- **正确切片法**：负偏移 iframe——把页面放进 `position:absolute; top:-偏移px; overflow:hidden`
  的 iframe 窗口（`screenshot_audit.py harness --offset <章节距顶部像素> ...`），
  每章一张，偏移量从 DOM 量测得到。

### 2.3 全页长图有高度上限

- 1440×10000 之类的"全页"截图只能覆盖超长文档的开头一段（实测 28598px 文档只盖住前 1/3）。
- 长文档不要指望一张长图验证全部排版：长图看首屏 + 章节切片逐章补齐。

## 3. 量测先于定性（硬规则）

任何"横向溢出 / 布局错位 / 内容截断"的 FAIL 判定，**必须先有量测数据**（探针 JSON、
DOM rect、哈希对比）再定性；对着截图目测得出的溢出结论一律不作数。
脚本预检 OK ≠ 视觉 PASS，反过来目测"看起来溢出" ≠ 真溢出。

## 4. 手写探针脚本的四条红线（每条都真实翻过车）

1. **不要等事件**：`--virtual-time-budget` 虚拟时钟下 `load` 等事件时序不可靠。
   探针注入后**立即执行**。
2. **不要用带反斜杠转义的 heredoc 注入 JS**：bash 会把 `\\n` 层层转义成 JS 字符串里的
   真实换行 → `Uncaught SyntaxError`，整个脚本静默不执行。要么把 JS 写成独立文件由
   Python 文件 I/O 读取（本套工具的做法），要么用 `String.fromCharCode(10)` 绕开转义。
3. **不要在定时器里反复测量**：第二帧会读到第一帧自毁 DOM 后的废数据（实测报出满屏 MISSING）。
   测一次、写一次结果；轮询取结果可以，但写结果必须一次落定。
4. **报错抓 Console，不要对着截图猜**：`--enable-logging=stderr` 或 dump-dom 里的错误
   信息才是真相；截图只是结果的影子。

## 5. screenshot_audit.py 用法速查

```bash
# 截图查重（拍摄前状态切换后逐张截图，拍完先查重再分析）
python <skill-root>/scripts/screenshot_audit.py dupcheck run-dir/*.png

# 量测真实布局（390px 移动视口）：exit 0=无真溢出 1=真溢出 2=探针失败
python <skill-root>/scripts/screenshot_audit.py probe --html "output/technical-document/<项目名>_用户展示.html" --width 390

# 生成章节切片页（offset=该章距文档顶部像素），浏览器对 harness 截图
python <skill-root>/scripts/screenshot_audit.py harness --html "<页面>.html" --offset 10319 --width 1440 --height 900 --out run-dir/ch5.html

# 图区渲染探针：高度比（<0.9=被压扁）/容器滚动条（必须 false）/黑块填充/标签对比
python <skill-root>/scripts/screenshot_audit.py renderprobe --html "<页面>.html"

# 单幅 SVG 像素证据：截图色彩多样性（≤2 色或近黑 ≥0.9 ≈ 黑块图）
python <skill-root>/scripts/screenshot_audit.py pixelprobe --svg "run-dir/1.svg"

# 截图覆盖矩阵：清单 {"shots":[{"file","width","role"}…]}，9 格齐全且字节互异
python <skill-root>/scripts/screenshot_audit.py coverage --manifest run-dir/shots.json
```

- 浏览器自动发现顺序：`--browser` 参数 → 环境变量 `TDS_BROWSER` → PATH 上的
  chrome/msedge → Windows 常见安装路径；都找不到时报 exit 2 并说明，不假装通过。
- `probe` 的临时文件默认写在 `<html 目录>/.screenshot-audit-tmp/`；验证结束后随本轮
  运行目录一起清理，不进交付目录。
- 量测在 iframe 真实布局视口内进行；图片晚载导致的高度变化不影响水平溢出判定。
- `renderprobe` 一次页面级测量逐幅 SVG：`height_ratio<0.9` = CSS 压扁、`container_scroll=true` = 图容器出现内层滚动条（流程图必须全局显示，禁 `max-height`/`overflow`/`min-width`）、`black_shape_fills>0` = 样式失配黑块签名（箭头 marker 本体有意黑色，探针已排除 `defs,marker` 内图元）；标签文字填充色与节点底色相同判对比不足。
- `pixelprobe` 给像素级反证：黑块图 ≈ 单色（量化后 ≤2 色或近黑占比 ≥0.9 即 `mono`），与 `renderprobe` 的计算样式互相印证；两者都不可用时如实记"未执行"，不算通过。
- `coverage` 只核对清单里的文件字节：1440/768/390 × home/diagram/interactive 9 格缺一即 exit 1，任意两格字节级相同 = 拍摄失败必须重拍（exit 1），清单/文件缺失 exit 2。
