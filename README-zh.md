语言： [English](README.md) | [中文](README-zh.md)

# KiCad KiKit Panelizer

KiCad KiKit Panelizer 是一个 Codex/ChatGPT Skill 和 Python 工具，用于把 KiCad `.kicad_pcb` 单板准备成 KiKit annotation-mode 拼版输入。它会在 PCB 副本中插入真实的 `footprint "kikit:Tab"` annotation，生成 KiKit JSON preset，并生成 Windows runner，方便用户最终运行 KiKit panelize。

当前版本：`v0.1.0-beta`

## 工具用途

适用于需要 mousebite / 邮票孔拼版、希望先做几何预检查、并使用 KiKit annotation Tab 控制连接筋位置的 KiCad PCB。

核心行为：

- 不覆盖原始 `.kicad_pcb`。
- 插入真实 KiCad footprint：`footprint "kikit:Tab"`。
- 插入新 Tab 前会删除旧的 `footprint "kikit:Tab"` 和 `footprint "PCM_kikit:Tab"`。
- 生成 KiKit annotation mode JSON：`"tabs": {"type": "annotation"}`。
- 支持异形板、凹槽、Type-C / USB 开口、短边、Edge.Cuts 圆孔 keepout。
- 矩阵拼版使用 paired tab placement：top/bottom 共用 X 坐标，left/right 共用 Y 坐标。
- inspect-only 会输出 safe segments、paired intervals、candidate evaluation、selected/skipped 原因、alignment checks 和 warnings。
- 支持 `--framing railstb|railslr|frame`。
- 默认生成 `run_kikit_panelize.ps1` 和 `run_kikit_panelize.bat`。
- 自动位置不理想时，支持 manual tab-plan 工程师 override。

## 安装要求

- Python 3.8+
- KiCad，用于目检
- KiKit 1.8+

已验证环境：

- KiCad 9.0
- KiKit 1.8.0

## 推荐快速流程

1. 先运行 inspect-only。
2. 生成 annotation PCB、JSON preset 和 Windows runner。
3. 双击 `run_kikit_panelize.bat`，或手动运行 `.ps1`。
4. 在 KiCad 中打开生成的 panel PCB 进行目检。
5. 如果 Tab 位置不理想，用自然语言告诉 Agent 想要的坐标，让 Agent 生成 `manual_tab_plan.json`。
6. 使用 `--tab-plan manual_tab_plan.json` 重新生成。

先检查：

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --inspect-only
```

生成文件：

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --output-dir "output"
```

普通 Windows 用户可以双击：

```text
output\run_kikit_panelize.bat
```

也可以手动运行 PowerShell：

```powershell
cd output
powershell -ExecutionPolicy Bypass -File .\run_kikit_panelize.ps1
```

## 默认输出行为

默认命令：

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --output-dir "output"
```

默认生成：

```text
output\<basename>_annotation_tabs.kicad_pcb
output\<basename>_panel_<rows>x<cols>.json
output\run_kikit_panelize.ps1
output\run_kikit_panelize.bat
```

默认不再生成 smoke-test preset：

```text
<basename>_test_2x1.json
<basename>_test_1x2.json
```

默认 runner 只生成用户指定的完整 panel，例如：

```text
<basename>_panel_2x2.kicad_pcb
```

## Windows Runner

普通 Windows 用户推荐双击：

```text
run_kikit_panelize.bat
```

自动化用户或熟悉 PowerShell 的用户推荐运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_kikit_panelize.ps1
```

Runner 行为：

- `.bat` 适合双击运行。
- `.bat` 只调用 `.ps1`，不重复写 KiKit 查找逻辑。
- `.bat` 结束后会停留窗口，方便用户查看成功或失败信息。
- `.ps1` 是主 runner，更适合自动化。
- runner 不修改原始 PCB。
- runner 会自动查找常见 Windows KiCad / KiKit 路径和 PATH。

如需强制指定 KiKit 路径：

```powershell
$env:KIKIT_EXE = "D:\KiCad\9.0\bin\Scripts\kikit.exe"
```

## Mimo / Claude Code / Linux VM 工作流

对于 Mimo、Claude Code、Linux VM 等不能直接调用 Windows KiCad / KiKit `.exe` 的环境：

1. Agent 先生成 annotation PCB、JSON preset 和 runner 文件。
2. 用户在 Windows 中打开输出目录。
3. 双击 `run_kikit_panelize.bat`，或在 Windows PowerShell 中运行 `.ps1`。
4. 不要让 Linux VM 硬调用 Windows KiKit `.exe`。

这样可以让 Agent 负责生成文件，把 KiKit panelize 留在原生 Windows KiCad 环境中执行。

## Smoke-Test Preset

默认输出对普通用户保持简单：只准备用户指定的完整 panel。

如果需要调试 top/bottom 或 left/right 连接，可以加 `--include-smoke-tests`：

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --include-smoke-tests --output-dir "output"
```

额外生成：

```text
<basename>_test_2x1.json
<basename>_test_1x2.json
```

启用 smoke tests 后，runner 会生成：

```text
<basename>_panel_2x1.kicad_pcb
<basename>_panel_1x2.kicad_pcb
<basename>_panel_<rows>x<cols>.kicad_pcb
```

## Framing 外框

使用 `--framing` 选择 KiKit preset 中的 framing 类型：

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 5 --cols 4 --framing frame
```

支持：

| 参数 | 含义 |
|------|------|
| `railstb` | 上下 rail，默认旧行为。 |
| `railslr` | 左右 rail。 |
| `frame` | 完整四边外框，适合很多实际打板场景。 |

即使 KiKit 成功生成 frame，也仍然需要 KiCad 目检。

## Inspect-Only 检查

推荐第一步总是运行 inspect-only：

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --inspect-only
```

inspect-only：

- 不写文件。
- 不生成 runner。
- 输出 board bbox 和 board size。
- 输出 Edge.Cuts segments 和 Edge.Cuts circles。
- 输出 circle keepouts 和 safe segments。
- 输出 paired intervals 和 candidate evaluation。
- 输出 paired top/bottom X positions 和 paired left/right Y positions。
- 输出 alignment checks、selected/skipped 原因、warnings 和 strong warnings。

它适合在正式生成前判断自动 Tab 位置是否合理。

## 自然语言 Manual Tab Plan

用户不需要自己手写 JSON。当自动 Tab 位置不理想时，可以用自然语言告诉 Agent 想要的 Tab 坐标。

中文例子：

```text
上下两个 Tab 我想放在 X=87.4 和 X=121.5；左右 Tab 我想放在 Y=109.2；左右宽度用 2.2mm。
```

Agent 应生成 `manual_tab_plan.json`，例如：

```json
{
  "tabs": [
    {"edge": "top", "x": 87.4, "width": 3.0},
    {"edge": "bottom", "x": 87.4, "width": 3.0},
    {"edge": "top", "x": 121.5, "width": 3.0},
    {"edge": "bottom", "x": 121.5, "width": 3.0},
    {"edge": "left", "y": 109.2, "width": 2.2},
    {"edge": "right", "y": 109.2, "width": 2.2}
  ]
}
```

然后重新生成：

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --tab-plan "output\manual_tab_plan.json" --output-dir "output"
```

规则：

- top / bottom 使用 X 坐标。
- left / right 使用 Y 坐标。
- top 和 bottom 必须成对使用同一个 X。
- left 和 right 必须成对使用同一个 Y。
- 未指定宽度时默认 `3.0mm`。
- manual tab-plan 是工程师 override。
- 使用 manual tab-plan 后仍需 KiCad 目检。

## 命令参数表

| 参数 | 含义 |
|------|------|
| `--rows N` | 拼版行数。 |
| `--cols N` | 拼版列数。 |
| `--framing railstb|railslr|frame` | KiKit framing 类型。 |
| `--inspect-only` | 只输出几何和 Tab 诊断，不写文件。 |
| `--tab-plan JSON_OR_PATH` | manual tab plan，支持 JSON 字符串或 JSON 文件路径。 |
| `--include-smoke-tests` | 额外生成 2x1 / 1x2 smoke-test preset 和 runner 步骤。 |
| `--no-runner` | 不生成 `run_kikit_panelize.ps1` 和 `run_kikit_panelize.bat`。 |
| `--output-dir DIR` | 输出目录，默认 `panel_output`。 |
| `--annotation-offset MM` | 将 `kikit:Tab` footprint 原点向板外偏移，默认 `0.5`。 |
| `--tab-width MM` | 标准 Tab 宽度，默认 `3.0`。 |
| `--narrow-width MM` | narrow Tab 宽度，默认 `1.8`。 |
| `--drill MM` | mousebite 孔径，默认 `0.4`。 |
| `--spacing MM` | mousebite 孔间距，默认 `0.7`。 |
| `--offset MM` | KiKit mousebite `cuts.offset`，默认 `-0.15`。 |
| `--prolong MM` | KiKit mousebite prolong，默认 `0.6`。 |

## 安全与验收检查

KiKit 成功不等于可以直接生产。送板前必须用 KiCad 打开生成的 panel PCB 目检。

至少检查 Tab 和邮票孔是否过于接近：

- 连接器
- 焊盘
- 安装孔
- 金手指
- 大镂空
- Type-C / USB 凹槽
- 禁布区
- 板边槽口和异形边

对于复杂异形板、连接器密集边、大镂空，或已有量产验证位置的板子，推荐使用自然语言 manual tab-plan 工作流，并用 `--tab-plan` 重新生成。

## 仓库结构

```text
kicad-kikit-panelizer/
├── SKILL.md
├── README.md
├── README-zh.md
├── CHANGELOG.md
├── LICENSE
├── agents/
│   └── openai.yaml
├── scripts/
│   └── panelize.py
├── references/
│   ├── DEFAULTS.md
│   └── MANUAL.md
└── dist/
    └── skill.zip
```

## License

MIT
