# 原生 VSDX 导出规范（technical-visual-assets v1.4.1）

## 1. 为什么生成 VSDX

用户要求交付 Visio 文件，即使当前机器没有安装 Visio。`scripts/vsdx_writer.py` 从同一份正交布局 spec 生成 **Visio 2013+ Open Packaging (.vsdx)**，而不是把 SVG/PNG 改后缀，也不是把图片塞进 Visio 外壳。

## 2. 包结构

生成的 `.vsdx` 是 ZIP 包，包含：

```text
[Content_Types].xml
_rels/.rels
docProps/core.xml
docProps/app.xml
visio/document.xml
visio/_rels/document.xml.rels
visio/pages/pages.xml
visio/pages/_rels/pages.xml.rels
visio/pages/page1.xml
visio/pages/_rels/page1.xml.rels
visio/windows.xml
```

- `document.xml`：Visio 文档设置、颜色、字体、样式表。
- `pages/pages.xml`：页面尺寸（A4 图形宽度 + 图题预留高度）。
- `pages/page1.xml`：原生节点 Shape、连线 Shape、分支标签/图题文字 Shape。
- 关系与内容类型：OPC 标准关系，所有 Target 必须存在。

## 3. 形状映射

| 图形元素 | VSDX 表达 |
|---|---|
| 普通操作 | 原生矩形 Shape + 几何 + 文本 |
| 判断 | 原生菱形 Shape（四顶点几何）+ 文本 |
| 开始/结束 | 圆角/胶囊近似矩形 Shape |
| 连线 | 原生 Shape + 多段 `MoveTo/LineTo` 几何 + `EndArrow` |
| 分支标签 | 白底文字 Shape，位于线段旁 |
| 中文图题 | 页面底部的原生文字 Shape（可编辑，不是像素） |
| 英文图题 | 页面底部的原生文字 Shape（可编辑，不是像素） |

坐标：spec 的毫米坐标按 25.4mm = 1 inch 转为 Visio 页面英寸；Y 轴从 Visio 左下角起算，已翻转。图题在图下预留 18mm。

## 4. 验证状态（必须如实标注）

`vsdx_writer.validate_vsdx()` 检查：

1. ZIP 必需部件是否齐全；
2. 所有 XML 是否可解析；
3. `[Content_Types].xml` 是否声明 document/pages/page；
4. 每个 `.rels` 的 Target 是否存在于包内；
5. `page1.xml` 是否至少有一个 Shape；
6. 记录 `shape_count`。

状态：

| 状态 | 含义 |
|---|---|
| `STRUCTURALLY_VALID_VSDX` | 包结构、XML、关系、页面形状检查通过 |
| `INVALID_VSDX` | 缺件/坏 XML/关系断链/无形状，必须 BLOCK |
| `vsdx_verification=pending-visio-open` | 本机没有 Visio/WPS 实际打开验证；**不得**写成“Visio 已打开合格” |
| `vsdx_verification=VISIO_OPEN_VERIFIED` | 只有真实 Visio/WPS 打开并保存/渲染后才允许 |

本机没有 Visio 时仍生成 `.vsdx`，这是用户明确要求；但报告必须保留 `pending-visio-open`，不能伪称已验证。

## 5. 命令

`visio_diagram.py` 默认同时生成 `.vsdx`：

```powershell
python scripts/visio_diagram.py --spec figure.json `
  --out-prefix figure --template 官方模板.docx --require-caption
# 输出 figure.svg / figure.drawio / figure.vsdx / figure.figure.json
```

关闭 VSDX（不推荐）：`--no-vsdx`。

单独生成/校验：

```powershell
python scripts/vsdx_writer.py --spec figure.json --out figure.vsdx
```

绑定 RES：

```powershell
python scripts/md_pipeline.py attach-layout --root $ROOT --technical-md $MD `
  --id RES-xxx --svg figure.svg --drawio figure.drawio --vsdx figure.vsdx `
  --template 官方模板.docx --figure-meta figure.figure.json `
  --evidence "已逐条核对 MD 的真实节点、连线与箭头方向"
```

资源条目会记录 `print_vsdx`、`print_vsdx_sha256`、`native_visio_vsdx=true`、`vsdx_verification=pending-visio-open`。

## 6. Visio 打开验证（有 Visio 时）

1. 用 Visio 打开 `.vsdx`，检查页面、节点、文字、箭头、图题。
2. 另存/导出 PDF 或 PNG，保存证据。
3. 只有完成上述步骤，才把 `vsdx_verification` 改为 `VISIO_OPEN_VERIFIED`。
4. 如果 Visio 报修复/不兼容，记录具体错误并修复生成器，不得强行标记合格。

## 7. 限制

- 生成器不依赖 Visio、不联网、不安装包。
- `.vsdx` 的视觉效果、字体替换、连接点行为必须在 Visio/WPS 中实际检查。
- 不生成原生 `.vsdx` 母版（master）；节点/连线是可直接编辑的 Shape。
- 不把 `.drawio` 当 `.vsdx`；两者是不同格式。
- 论文插图仍优先用 SVG/300dpi PNG；`.vsdx` 是用户要求的 Visio 交付格式。