# 分组框（subgraph）布局与 `<br/>` 标签规范（v1.4.3）

## 1. 分组框样式（强制）

- **虚线边框**（SVG `stroke-dasharray` / draw.io `dashed=1`）。
- **浅色底**：默认 `#F7F8FC`，不透明度约 55%；复杂图必须有底色，否则连线和框线混在一起。
- **必须有分组标签**，标签带白色底衬，不能被连线/节点压住。
- 分组框之间不得互相压盖；嵌套必须有明确语义（包含关系 ≥95%）。
- 节点应完整落在所属分组框内；跨越边界只允许 WARN，并需人工确认分组语义。
- 连线不得穿过无关分组框；正交路由器会把无关分组框作为软障碍，无法绕行时回退并标记 `crosses_group`，由 QC 警告。

## 2. `<br/>` 标签

- Mermaid/外部 spec 的 `<br/>`、`<br>`、HTML 标签在 `prepare_spec` 前由 `subgraph_layout.normalize_labels` 归一化为真实换行/纯文本。
- 渲染后的 SVG 不得残留 `<br/>`；`figure_qc` 会检查 spec 和 SVG。
- 不允许把 `<br/>` 当普通字符画进节点；也不允许因净化标签而丢字。

## 3. 自动子图布局

`subgraph_layout.layout(spec)`：

1. 归一化标签；
2. 按 `node.group` / `node.group_id` 识别成员；未声明时按节点中心落在哪个分组框推断，多个框重叠时取最小框；
3. 组内节点按网格排列（列数按节点宽度自适应）；
4. 分组框 = 成员网格 + 内边距 + 顶部标签高度；
5. 分组框纵向堆叠，能并排时并排，保证框不重叠；
6. 布局总高超过 A4 上限时 BLOCK，提示拆图；**不删节点、不改连线语义**；
7. 丢弃旧连线 `points`，交给 `orthogonal_router` 重路由。

## 4. 命令

```powershell
python scripts/visio_diagram.py --spec figure.json --out-prefix figure `
  --template 官方模板.docx --require-caption --auto-layout
```

或在 spec 中写：

```json
{"layout": "subgraph"}
```

`figure_qc.py` 会检查：

- 分组框重叠 / 标签重叠 / 未标注；
- SVG 分组框是否虚线、是否有底色、是否有标签；
- 节点跨分组边界（WARN）；
- 连线穿过无关分组框（WARN）；
- `<br/>`/HTML 残留（FAIL）。

## 5. 信息完整性

分组多、节点多是系统架构图的正常形态。布局优先通过**加大间距、调整分组、改方向、Graphviz 重排**解决；拆图是最后手段，且必须保留全部节点、连线、分组标签和来源。不得为了“看起来不挤”删除节点或分组语义。
