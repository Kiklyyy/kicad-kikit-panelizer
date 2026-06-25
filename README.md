Languages: [English](README.md) | [中文](README-zh.md)

# KiCad KiKit Panelizer

KiCad KiKit Panelizer is a Codex/ChatGPT skill and Python utility for preparing KiCad `.kicad_pcb` boards for KiKit annotation-mode panelization. It inserts real `footprint "kikit:Tab"` annotations into a copy of the PCB and generates KiKit JSON presets.

Current version: `v0.1.0-beta`

## What it is for

Use this project when you need matrix panelization with mousebite tabs and want repeatable preflight checks before running KiKit. It is especially useful for boards with Type-C/USB edge openings, short edges, or Edge.Cuts circular holes that should become tab keepouts.

## Features

- Parses KiCad `.kicad_pcb` text without overwriting the original board.
- Extracts complete `gr_line`, `gr_arc`, and `gr_circle` Edge.Cuts blocks.
- Removes old `footprint "kikit:Tab"` and `footprint "PCM_kikit:Tab"` annotations before inserting new ones.
- Inserts real KiCad `footprint "kikit:Tab"` entries with edge-aware rotation.
- Generates KiKit JSON presets using annotation mode: `"tabs": {"type": "annotation"}`.
- Uses unit strings for length parameters such as `"hspace": "2mm"` and `"vspace": "2mm"`.
- Supports `--inspect-only` for bbox, Edge.Cuts, recommended tabs, keepouts, and warnings.
- Supports `--tab-plan` for manually supplied tab coordinates and widths.
- Treats near-edge Edge.Cuts `gr_circle` holes as tab keepouts.
- Moves annotation footprint origins outside the board by default with `--annotation-offset 0.5`.
- Reduces tab width or tab count on short safe segments instead of forcing overlapping tabs.

## Requirements

- Python 3.8+
- KiCad for visual review
- KiKit 1.8+

Validated environment:

- KiCad 9.0
- KiKit 1.8.0

## Quick start

Always inspect first:

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 5 --cols 10 --inspect-only
```

If the reported bbox, Edge.Cuts segments, recommended tabs, keepouts, and warnings look reasonable, generate the annotation PCB and presets:

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 5 --cols 10
```

Then run KiKit 1.8 with `-p`:

```powershell
kikit panelize -p panel_output\board_panel_5x10.json panel_output\board_annotation_tabs.kicad_pcb panel_output\board_kikit_panel_5x10.kicad_pcb
```

## Safety workflow

Before production:

1. Run `--inspect-only`.
2. Review warnings for openings, short edges, Edge.Cuts holes, connector keepouts, and reduced tab counts.
3. Open the annotation PCB in KiCad and visually inspect every tab.
4. Run small `2x1` and `1x2` panel tests before a full production panel.
5. Review the KiKit output PCB before ordering or fabrication.

Do not skip inspect-only unless you are deliberately doing a fast local experiment.

## Common commands

Generate a 2x1 vertical connection test:

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 2 --cols 1
kikit panelize -p panel_output\board_panel_2x1.json panel_output\board_annotation_tabs.kicad_pcb panel_output\board_kikit_panel_2x1.kicad_pcb
```

Generate a 1x2 horizontal connection test:

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 1 --cols 2
kikit panelize -p panel_output\board_panel_1x2.json panel_output\board_annotation_tabs.kicad_pcb panel_output\board_kikit_panel_1x2.kicad_pcb
```

Use a manual tab plan:

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 5 --cols 10 --tab-plan path\to\tab-plan.json
```

Example tab plan:

```json
{
  "tabs": [
    {"edge": "bottom", "x": 145.8, "width": 3.0},
    {"edge": "bottom", "x": 163.5, "width": 2.2},
    {"edge": "left", "y": 76.0, "width": 3.0}
  ]
}
```

## Defaults

- Top/bottom: 2 tabs per edge when safe geometry allows it.
- Left/right: 1 tab per edge.
- Standard tab width: `3.0mm`.
- Narrow tab width: `1.8mm` default, with `1.5mm` to `2.2mm` recommended range.
- Mousebite cuts: drill `0.4mm`, spacing `0.7mm`, offset `-0.15mm`, prolong `0.6mm`.
- Annotation origin offset: `0.5mm` outside the board edge.
- KiKit tabs mode: annotation.

## Repository contents

```text
kicad-kikit-panelizer/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
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

