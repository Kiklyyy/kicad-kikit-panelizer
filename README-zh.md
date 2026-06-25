语言： [English](README.md) | [中文](README-zh.md)

# KiCad KiKit Panelizer

用于 KiCad / KiKit 的拼版辅助工具，可为 `.kicad_pcb` 文件添加 KiKit annotation Tab，并生成 KiKit panelize JSON preset。

本项目用于辅助 PCB 拼版准备工作。它不会替代工程师审查，也不能保证输出文件可以直接用于生产。正式投板前，应在 KiCad 中检查 annotation PCB 和 KiKit 生成的 panel PCB，并结合板厂工艺规范确认邮票孔、连接筋、禁布区和装配空间。

当前版本：`v0.1.0-beta`

## 功能特性

- 读取 KiCad `.kicad_pcb` 文件，并在副本中插入 KiKit annotation Tab。
- 插入真实 KiCad footprint：`footprint "kikit:Tab"`。
- 删除旧的 `footprint "kikit:Tab"` 和 `footprint "PCM_kikit:Tab"` 后再生成新 annotation。
- 生成 KiKit panelize JSON preset，并使用 annotation 模式：`"tabs": {"type": "annotation"}`。
- 支持 mousebite / 邮票孔拼版。
- 支持矩阵拼版，包含上下连接和左右连接。
- 按完整 `gr_line`、`gr_arc`、`gr_circle` block 解析 Edge.Cuts，避免误读其他图层。
- 支持 Edge.Cuts 圆孔 keepout，将靠近板边的圆孔从可用 Tab 区域中扣除。
- 支持 Type-C 凹槽、USB 边缘开口、短边等风险场景的检查和避让。
- 支持 `--inspect-only`，在不写文件的情况下输出几何检查结果。
- 支持 `--tab-plan`，允许手动指定 Tab 坐标和宽度。
- 默认将 annotation footprint 原点向板外偏移，降低 KiKit 判断 annotation 位于板内的风险。
- 不覆盖原始 PCB 文件。

## 适用场景

本工具适用于以下场景：

- 使用 KiCad 设计 PCB，并使用 KiKit 进行 panelize。
- 需要通过 KiKit annotation Tab 控制 mousebite / 邮票孔位置。
- 需要生成 2x1、1x2 或 NxM 矩阵拼版 preset。
- 板边存在 Type-C、USB、槽口、开口、圆孔或较短边，需要先检查 Tab 风险。
- 希望在正式 KiKit panelize 前，先得到 bbox、Edge.Cuts segment、keepout 和 recommended tabs 等检查结果。

不建议将本工具视为自动生产工具。它是拼版辅助和预检查工具，最终输出必须经过工程师和板厂工艺规范确认。

## 安装要求

- Python 3.8+
- KiCad，用于打开和检查 `.kicad_pcb`
- KiKit 1.8+

已验证环境：

- KiCad 9.0
- KiKit 1.8.0

## 快速开始

先运行 inspect-only：

```powershell
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 5 --cols 10 --inspect-only
```

检查结果没有明显问题后，再生成 annotation PCB 和 JSON preset：

```powershell
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 5 --cols 10
```

使用 KiKit 1.8 正确命令格式生成拼版 PCB：

```powershell
kikit panelize -p "panel_output\board_panel_5x10.json" "panel_output\board_annotation_tabs.kicad_pcb" "panel_output\board_kikit_panel_5x10.kicad_pcb"
```

## 推荐工作流

建议按以下顺序执行：

1. 先运行 `--inspect-only`，检查板框、Edge.Cuts、keepout、recommended tabs 和 warnings。
2. 生成 2x1 测试，用于验证上下连接。
3. 生成 1x2 测试，用于验证左右连接。
4. 检查无误后，再生成完整拼版参数。
5. 使用 KiKit panelize 实际生成 panel PCB。
6. 在 KiCad 中打开 annotation PCB 和 panel PCB 进行目检。

示例命令：

```powershell
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 2 --cols 1 --inspect-only
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 2 --cols 1
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 1 --cols 2
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 5 --cols 10
```

KiKit 示例：

```powershell
kikit panelize -p "panel_output\board_panel_5x10.json" "panel_output\board_annotation_tabs.kicad_pcb" "panel_output\board_kikit_panel_5x10.kicad_pcb"
```

## 命令行参数

常用参数：

```text
--rows N                  拼版行数
--cols N                  拼版列数
--tab-top N               top 边 Tab 数量，默认 2
--tab-bot N               bottom 边 Tab 数量，默认 2
--tab-left N              left 边 Tab 数量，默认 1
--tab-right N             right 边 Tab 数量，默认 1
--tab-width MM            普通 Tab 宽度，默认 3.0
--narrow-width MM         narrow Tab 宽度，默认 1.8
--drill MM                mousebite 孔径，默认 0.4
--spacing MM              mousebite 孔间距，默认 0.7
--offset MM               mousebite cuts.offset，默认 -0.15
--prolong MM              mousebite prolong，默认 0.6
--annotation-offset MM    annotation footprint 原点向板外偏移，默认 0.5
--inspect-only            只输出检查结果，不写文件
--tab-plan JSON           手动 Tab plan，支持 JSON 字符串或 JSON 文件路径
--output-dir DIR          输出目录，默认 panel_output
--prefix NAME             输出文件名前缀
```

## 输出文件

默认输出到 `panel_output/`，常见文件包括：

```text
board_annotation_tabs.kicad_pcb
board_test_2x1.json
board_test_1x2.json
board_panel_5x10.json
```

其中：

- `board_annotation_tabs.kicad_pcb` 是插入 annotation Tab 的 PCB 副本。
- `board_test_2x1.json` 用于上下连接小样测试。
- `board_test_1x2.json` 用于左右连接小样测试。
- `board_panel_5x10.json` 用于完整拼版。

原始 `.kicad_pcb` 不会被覆盖。

## 默认规则

默认值：

```text
上下边默认 2 个 Tab
左右边默认 1 个 Tab
普通 Tab 宽度 3.0mm
narrow Tab 默认宽度 1.8mm，建议范围 1.5mm 到 2.2mm
短边可自动使用 narrow width
空间不足时自动减少 Tab 数
annotation_offset 默认 0.5mm
mousebite drill 0.4mm
mousebite spacing 0.7mm
mousebite offset -0.15mm
mousebite prolong 0.6mm
```

`annotation_offset` 与 `cuts.offset` 是两个不同参数：

- `annotation_offset` 是 KiKit Tab annotation footprint 原点相对板边向板外偏移的距离，默认 `0.5mm`。它用于让 KiKit 识别 Tab annotation 位于板边或板外。
- `cuts.offset` 是 mousebite 孔列相对于连接筋/板边的偏移，默认 `-0.15mm`。它影响邮票孔切割位置，不改变 annotation footprint 原点。

Tab rotation 默认值：

```text
top: 270
bottom: 90
left: 0
right: 180
```

## KiKit 拼版

KiKit 1.8 的正确命令格式是：

```powershell
kikit panelize -p <preset.json> <annotation_pcb.kicad_pcb> <output_panel.kicad_pcb>
```

示例：

```powershell
kikit panelize -p "panel_output\board_panel_5x10.json" "panel_output\board_annotation_tabs.kicad_pcb" "panel_output\board_kikit_panel_5x10.kicad_pcb"
```

## inspect-only 检查

`--inspect-only` 不会写文件，适合在正式生成前检查几何识别和 Tab 推荐结果。

它至少用于检查：

- board bbox
- Edge.Cuts segments
- Edge.Cuts circles
- keepout intervals
- safe segments
- recommended tabs
- warnings
- strong warnings
- anchor 坐标和 footprint 坐标
- Tab 是否向板外偏移

示例：

```powershell
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 5 --cols 10 --inspect-only
```

如果输出包含 strong warning，应先检查原因，再决定是否继续生成，或改用手动 `--tab-plan`。

## 手动 Tab 计划

当自动放置不符合实际机械要求时，可以使用 `--tab-plan` 手动指定 Tab。

示例 JSON：

```json
{
  "tabs": [
    {"edge": "bottom", "x": 145.8, "width": 3.0},
    {"edge": "bottom", "x": 163.5, "width": 2.2},
    {"edge": "left", "y": 76.0, "width": 3.0}
  ]
}
```

命令示例：

```powershell
python scripts/panelize.py "path\to\board.kicad_pcb" --rows 5 --cols 10 --tab-plan tab_plan.json
```

手动计划仍会生成真实 `footprint "kikit:Tab"`，并保持对应边的 rotation 和 annotation offset。

## 安全与生产检查

工具生成成功不等于可以直接生产。KiKit panelize 成功也不等于没有机械风险。

生产前必须在 KiCad 中目检，至少检查邮票孔和连接筋是否碰到或过于接近：

- Type-C 凹槽
- 安装孔
- Edge.Cuts 圆孔
- 板边连接器
- 金手指
- 焊盘
- 丝印
- 装配禁布区

最终应以工程师检查和板厂工艺规范为准。对于关键项目，建议先制作小样或使用板厂 DFM 工具复核。

## 常见问题

### KiKit 报 `Cannot create tab` 怎么办？

常见原因包括：

- annotation Tab footprint 位于板内。
- annotation offset 方向不正确。
- Tab rotation 不正确。
- Tab 被放在凹槽、短边内部或其他非安全位置。

建议处理方式：

- 先运行 `--inspect-only`。
- 检查 anchor 坐标和 footprint 坐标。
- 检查 top / bottom / left / right 的 rotation。
- 检查 keepout intervals、safe segments、warnings 和 strong warnings。
- 必要时使用 `--annotation-offset` 调整外移距离，或使用 `--tab-plan` 手动指定位置。

### 为什么短边只放了一个 Tab？

通常是因为短边长度不足，或 Edge.Cuts 圆孔、开口、连接器 keepout 占用了安全区域。

脚本会先尝试普通宽度，再尝试 narrow width。如果仍无法满足 end clearance 和最小 Tab 间距，就会自动减少 Tab 数，避免 Tab 重叠、邮票孔过密或掰板困难。

### 为什么要先做 2x1 / 1x2？

`2x1` 用于验证上下连接和 top/bottom Tab。`1x2` 用于验证左右连接和 left/right Tab。

小样通过后再生成完整拼版，可以更早发现方向、offset、keepout、Tab 间距和 KiKit preset 配置问题，降低整版失败风险。

## 版本与验证环境

当前版本建议标记为：`v0.1.0-beta`

已验证环境：

- KiCad 9.0
- KiKit 1.8.0

该版本已完成真实 KiKit panelize 验证，但仍建议在不同板形、不同板厂规则和不同 KiKit 版本下进行独立检查。

## License

MIT
