# 正交连线与工程图布局规则（technical-visual-assets v1.4.0）

## 1. 目标

把“技术上能生成图”提升为“可直接用于毕业论文的规范化工程图”。本文件是 `scripts/orthogonal_router.py`、`scripts/visio_diagram.py` 和 `scripts/figure_qc.py` 的共同规则来源。

**硬约束**：常规连接线只能是水平线、垂直线或二者组成的 90° 折线。箭头尖端自身的斜边不算连接路径。只有图形语义明确要求特殊斜线时才允许例外，并必须在 spec 中写 `routing_exception_reason`，由人工复核。

## 2. 连线规划顺序

1. 主流程优先自上而下（`TD`）；需要横向展开时从左到右（`LR`）。
2. 先放主链节点，再放判断分支，最后放回环/异常支线。
3. 判断节点优先左右分支；目标主要在下方时才走底边。
4. 同级节点统一宽高、统一间距；判断分支左右尽量对称。
5. 回环/重试支线从图形外侧绕行，不穿过中间节点。
6. 复杂流程先拆成逻辑完整子图；不允许靠缩小整图适配 A4。

## 3. 锚点规则

每个矩形/菱形/起止节点有四个锚点：

| 锚点 | 坐标 | 适用 |
|---|---|---|
| top | 上边中点 | 从上方进入，或向上回环的终点 |
| bottom | 下边中点 | 主流程向下、判断“是”向下 |
| left | 左边中点 | 目标在左侧、左侧回环 |
| right | 右边中点 | 目标在右侧、判断“否”向右侧 |

- 不允许从节点中心穿入。
- 允许在 spec 中用 `from_port` / `to_port` 显式指定锚点；路由器优先采用。
- 同一判断节点的两个分支应使用不同锚点，避免两条线重叠。

## 4. 分支约定

1. 判断节点的出边必须有标签（“是/否”“Y/N”“通过/不通过”），不得只靠位置猜。
2. 目标主要在下方：`是` 从 bottom 出，`否` 从朝向目标的侧面出。
3. 目标主要在侧方/上方：分支从朝向目标的侧面出，避免先向下再折返。
4. 同一判断节点的标签不得重复，且必须靠近对应线段。
5. 汇合点必须符合业务语义；不同语义的支线不得强行合并。

## 5. 障碍、交叉与转折

`orthogonal_router.py` 用正交 A* 布线：

- 节点矩形按 clearance（默认 2.5mm，必要时降到 0.6mm）扩张为障碍。
- 分区框的文字标签也作为障碍条带，防止连线压住“感知层/控制层”等标签。
- 代价 = 线段长度 + 转折惩罚（8）+ 交叉惩罚（60）+ 反向重叠惩罚（30/段）+ 同向重叠惩罚（2/段）。
- T 型接头：显式母线布局允许；A* 搜索中仍作为潜在碰撞点惩罚。
- 如果找不到路径：先扩大间距、移动节点、扩大画布或拆图；**不得**退回斜线或穿节点。
- 交叉数由 `figure_qc.py` 统计；默认上限 0，复杂图可显式放宽并人工说明。

## 6. 标签与文字

1. 分支标签放在线段旁，优先放在垂直段右侧；必须有白色底衬。
2. 标签不得压在任何节点上；QC 用标签包围盒检查。
3. 节点文字水平/垂直居中，不超过 4 行；行宽按中文字符 1em、ASCII 0.58em 估算。
4. 插入 Word 后正文不小于 9pt；建议 9–10.5pt。不得靠缩小字号解决超版心。
5. 图题不进图片像素；见 `english-caption-spec.md`。

## 7. SVG / draw.io 的真实性

- SVG 的每条连接线必须是 `<polyline>`，点坐标成对出现，任意相邻两点只能有一个坐标变化。
- draw.io 每条边必须使用 `edgeStyle=orthogonalEdgeStyle`，并带 `source`/`target` 和必要 waypoint。
- `figure_qc.py` 会解析实际文件；只写样式名不构成合格。
- `.drawio` 可编辑，但不是原生 `.vsdx`；不得伪称。

## 8. 修改前后对照

- 失败样本：`examples/before-diagonal-sms-flow-300dpi.png`（v1.3.1：斜线分支、回环拥挤、无英文图题）。
- 修订样本：`examples/after-orthogonal-sms-flow-300dpi.png`（v1.4.0：仅 H/V 线段、分支标签清晰、图题进入元数据）。
- 并排图：`examples/orthogonal-upgrade-comparison.png`。

## 9. 质量门禁清单

| 检查 | 工具 | 失败级别 |
|---|---|---|
| 斜线 | `figure_qc.py` / `orthogonal_router.is_orthogonal` | BLOCK |
| 节点重叠 | `route_spec` / `figure_qc.py` | BLOCK |
| 连线穿节点 | `audit_routing` / `figure_qc.py` | BLOCK |
| 标签压节点 | `place_label` / `figure_qc.py` | BLOCK |
| 分支标签缺失/重复 | `decision_branch_issues` | BLOCK |
| 交叉数超限 | `count_crossings` | WARN（默认 0） |
| 转折过多 | `figure_qc.py`（>8） | WARN |
| A4 超版心 | `a4_layout.py` / `figure_qc.py` | BLOCK |
| 箭头/来源元数据缺失 | `figure_qc.py` | BLOCK |
| 图题缺失/笼统 | `validate_caption` | BLOCK |
| 英文题语义可疑 | `validate_caption` 关键词预警 | WARN + 人工 |
| 实际 Word 分页/重叠 | 人工目检 / `figure_qc.py --docx` | 未检查 = PENDING |

**程序通过不等于视觉验收通过。** 最终必须由人在 Word/WPS 中逐页检查。