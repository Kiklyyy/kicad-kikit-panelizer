Languages: [English](README.md) | [中文](README-zh.md)

# KiCad KiKit Panelizer

KiCad KiKit Panelizer is a Codex/ChatGPT skill and Python utility for preparing KiCad `.kicad_pcb` boards for KiKit annotation-mode panelization. It inserts real `footprint "kikit:Tab"` annotations into a copy of the PCB, generates KiKit JSON presets, and writes Windows runners so the final KiKit panelize step is easy to run.

Current version: `v0.1.0-beta`

## What It Does

Use this project when you need mousebite panelization with repeatable preflight checks and KiKit annotation tabs.

Key behavior:

- Never overwrites the original `.kicad_pcb`.
- Inserts real KiCad footprints: `footprint "kikit:Tab"`.
- Removes old `footprint "kikit:Tab"` and `footprint "PCM_kikit:Tab"` annotations before inserting new ones.
- Generates KiKit JSON presets using annotation mode: `"tabs": {"type": "annotation"}`.
- Supports irregular outlines, notches, Type-C/USB recesses, short edges, and Edge.Cuts circular keepouts.
- Uses paired tab placement for matrix panels: top/bottom share X coordinates, and left/right share Y coordinates.
- Reports safe segments, paired intervals, candidate evaluation, selected/skipped reasons, alignment checks, and warnings in inspect-only mode.
- Supports `--framing railstb|railslr|frame`.
- Generates `run_kikit_panelize.ps1` and `run_kikit_panelize.bat` for Windows users.
- Supports manual tab-plan overrides when automatic placement is not mechanically ideal.

## Requirements

- Python 3.8+
- KiCad for visual inspection
- KiKit 1.8+

Validated environment:

- KiCad 9.0
- KiKit 1.8.0

## Recommended Quick Workflow

1. Run inspect-only first.
2. Generate the annotation PCB, JSON preset, and Windows runners.
3. Double-click `run_kikit_panelize.bat`, or run the PowerShell runner manually.
4. Open the generated panel PCB in KiCad for visual inspection.
5. If the tab locations are not ideal, describe the desired coordinates in natural language and let the agent create `manual_tab_plan.json`.
6. Regenerate with `--tab-plan manual_tab_plan.json`.

Inspect first:

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --inspect-only
```

Generate files:

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --output-dir "output"
```

Then run KiKit from Windows by double-clicking:

```text
output\run_kikit_panelize.bat
```

Or run PowerShell manually:

```powershell
cd output
powershell -ExecutionPolicy Bypass -File .\run_kikit_panelize.ps1
```

## Default Output

The default generation command:

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --output-dir "output"
```

Default output files:

```text
output\<basename>_annotation_tabs.kicad_pcb
output\<basename>_panel_<rows>x<cols>.json
output\run_kikit_panelize.ps1
output\run_kikit_panelize.bat
```

By default, the tool does not generate smoke-test presets:

```text
<basename>_test_2x1.json
<basename>_test_1x2.json
```

The default runner only generates the requested full panel, for example:

```text
<basename>_panel_2x2.kicad_pcb
```

## Windows Runner

Ordinary Windows users should double-click:

```text
run_kikit_panelize.bat
```

Automation and PowerShell users should run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_kikit_panelize.ps1
```

Runner behavior:

- `.bat` is for double-click use.
- `.bat` only calls `.ps1`; it does not duplicate KiKit lookup logic.
- `.bat` pauses at the end so users can read success or failure messages.
- `.ps1` is the main runner and is better for automation.
- The runner does not modify the original PCB.
- The runner automatically looks for KiKit in common Windows KiCad locations and PATH.

To force a KiKit executable path:

```powershell
$env:KIKIT_EXE = "D:\KiCad\9.0\bin\Scripts\kikit.exe"
```

## Mimo / Claude Code / Linux VM Workflow

Some agent environments cannot directly call Windows KiCad or KiKit `.exe` files. In that case:

1. Let the agent generate the annotation PCB, JSON preset, and runner files.
2. Open the output folder in Windows.
3. Double-click `run_kikit_panelize.bat`, or run `run_kikit_panelize.ps1` in Windows PowerShell.
4. Do not force a Linux VM to call the Windows KiKit executable directly.

This keeps generation agent-friendly while leaving the KiKit panelize step in the native Windows KiCad environment.

## Smoke-Test Presets

Default output is intentionally simple for ordinary users: it only prepares the requested full panel.

When debugging top/bottom or left/right connections, add `--include-smoke-tests`:

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --include-smoke-tests --output-dir "output"
```

Additional files:

```text
<basename>_test_2x1.json
<basename>_test_1x2.json
```

With smoke tests enabled, the runner generates:

```text
<basename>_panel_2x1.kicad_pcb
<basename>_panel_1x2.kicad_pcb
<basename>_panel_<rows>x<cols>.kicad_pcb
```

## Framing

Use `--framing` to choose the KiKit framing style written into the preset:

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 5 --cols 4 --framing frame
```

Supported values:

| Value | Meaning |
|-------|---------|
| `railstb` | Top/bottom rails. This is the default legacy behavior. |
| `railslr` | Left/right rails. |
| `frame` | Full four-side outer frame. Useful for many practical fabrication panels. |

A successful frame generation still requires KiCad visual inspection.

## Inspect-Only

Inspect-only is the recommended first step:

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --inspect-only
```

Inspect-only:

- Writes no files.
- Generates no runner.
- Reports board bbox and board size.
- Reports Edge.Cuts segments and Edge.Cuts circles.
- Reports circle keepouts and safe segments.
- Reports paired intervals and candidate evaluation.
- Reports paired top/bottom X positions and paired left/right Y positions.
- Reports alignment checks, selected/skipped reasons, warnings, and strong warnings.

Use it to decide whether automatic tab placement is mechanically reasonable before writing output files.

## Natural-Language Manual Tab Plans

Users do not need to hand-write JSON. If automatic tab placement is not ideal, describe the desired tab coordinates to the agent in natural language.

Example:

```text
Place the top/bottom tabs at X=87.4 and X=121.5. Place the left/right tabs at Y=109.2. Use 2.2mm width for the side tabs.
```

The agent should create `manual_tab_plan.json`, for example:

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

Then regenerate:

```powershell
python scripts\panelize.py "board.kicad_pcb" --rows 2 --cols 2 --framing frame --tab-plan "output\manual_tab_plan.json" --output-dir "output"
```

Rules:

- Top/bottom use X coordinates.
- Left/right use Y coordinates.
- Top and bottom must be paired with the same X values.
- Left and right must be paired with the same Y values.
- Width defaults to `3.0mm` when not specified.
- A manual tab plan is an engineer override.
- Manual tab-plan output still requires KiCad visual inspection.

## Command-Line Options

| Option | Meaning |
|--------|---------|
| `--rows N` | Panel row count. |
| `--cols N` | Panel column count. |
| `--framing railstb|railslr|frame` | KiKit framing style. |
| `--inspect-only` | Print geometry and placement diagnostics without writing files. |
| `--tab-plan JSON_OR_PATH` | Manual tab plan as a JSON string or JSON file path. |
| `--include-smoke-tests` | Also generate 2x1 / 1x2 smoke-test presets and runner steps. |
| `--no-runner` | Do not generate `run_kikit_panelize.ps1` or `run_kikit_panelize.bat`. |
| `--output-dir DIR` | Output directory. Defaults to `panel_output`. |
| `--annotation-offset MM` | Move `kikit:Tab` footprint origins outside the board edge. Default `0.5`. |
| `--tab-width MM` | Standard tab width. Default `3.0`. |
| `--narrow-width MM` | Narrow tab width. Default `1.8`. |
| `--drill MM` | Mousebite drill diameter. Default `0.4`. |
| `--spacing MM` | Mousebite hole spacing. Default `0.7`. |
| `--offset MM` | KiKit mousebite `cuts.offset`. Default `-0.15`. |
| `--prolong MM` | KiKit mousebite prolong value. Default `0.6`. |

## Safety and Acceptance Checks

KiKit success does not mean the panel is ready for production. Always open the generated panel PCB in KiCad before ordering boards.

Check that tabs and mousebites are not too close to:

- Connectors
- Pads
- Mounting holes
- Gold fingers
- Large cutouts
- Type-C / USB recesses
- Keepout areas
- Board-edge slots and notches

For complex irregular boards, connector-heavy edges, large cutouts, or proven production tab locations, use a natural-language manual tab-plan workflow and regenerate with `--tab-plan`.

## Repository Contents

```text
kicad-kikit-panelizer/
??? SKILL.md
??? README.md
??? README-zh.md
??? CHANGELOG.md
??? LICENSE
??? agents/
?   ??? openai.yaml
??? scripts/
?   ??? panelize.py
??? references/
?   ??? DEFAULTS.md
?   ??? MANUAL.md
??? dist/
    ??? skill.zip
```

## License

MIT
