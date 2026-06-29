---
name: kicad-kikit-panelizer
description: Panelize KiCad PCB files by adding real KiKit annotation tabs and generating KiKit JSON presets. Use when working with .kicad_pcb files that need mousebite panelization, inspect-only geometry checks, Type-C or USB opening handling, Edge.Cuts circle keepouts, short-edge tab reduction, or KiKit annotation-mode presets.
---

# KiCad KiKit Panelizer

Use `scripts/panelize.py` to create an annotated copy of a KiCad `.kicad_pcb` file and KiKit JSON presets. The original PCB must never be overwritten.

Load `references/DEFAULTS.md` when you need exact default values. Load `references/MANUAL.md` when you need detailed operating guidance.

## Required Workflow

1. Confirm the input `.kicad_pcb` file exists.
2. Confirm panel `--rows` and `--cols`.
3. Always run inspect-only before generating production files:

```bash
python scripts/panelize.py <input.kicad_pcb> --rows <ROWS> --cols <COLS> [--framing railstb|railslr|frame] --inspect-only
```

Inspect-only does not write files. It reports board bbox, Edge.Cuts segments, Edge.Cuts circles, circle keepouts, safe segments, paired interval sources, paired candidate evaluation, paired top/bottom X positions, paired left/right Y positions, alignment checks, recommended tabs, tab intervals, annotation offset results, and warnings.

Do not skip inspect-only unless the user explicitly asks for fast generation. If warnings mention openings, short edges, holes near edges, connector keepouts, reduced tab counts, or spacing risks, pause and confirm with the user before formal output.

4. Generate annotation PCB and presets only after inspect-only looks reasonable:

```bash
python scripts/panelize.py <input.kicad_pcb> --rows <ROWS> --cols <COLS> [--framing railstb|railslr|frame]
```

5. Run KiKit 1.8+ with `-p`:

```bash
kikit panelize -p <preset.json> <annotation_pcb.kicad_pcb> <output_panel.kicad_pcb>
```

By default, generation writes only the requested full panel preset. For debugging or extra confidence, add `--include-smoke-tests` to also generate `2x1` and `1x2` smoke-test presets and include them in the runner. Always visually inspect the generated panel in KiCad before fabrication.

## Simple Output Defaults

Default generation writes only:

- `<basename>_annotation_tabs.kicad_pcb`
- `<basename>_panel_<rows>x<cols>.json`
- `run_kikit_panelize.ps1`
- `run_kikit_panelize.bat`

It does not write `2x1` or `1x2` smoke-test presets unless the user passes `--include-smoke-tests`. With `--include-smoke-tests`, generation also writes `<basename>_test_2x1.json` and `<basename>_test_1x2.json`, and the runner also produces `<basename>_panel_2x1.kicad_pcb` and `<basename>_panel_1x2.kicad_pcb` before the full panel.

## Core Rules

- Never overwrite the original `.kicad_pcb`.
- Remove old `footprint "kikit:Tab"` and `footprint "PCM_kikit:Tab"` blocks before inserting new tabs.
- Insert real KiCad footprints: `footprint "kikit:Tab"`.
- Never generate pseudo `(kikit:Tab ...)` nodes.
- JSON presets must use annotation mode: `"tabs": {"type": "annotation"}`.
- Length values such as `hspace` and `vspace` must include units, for example `"2mm"`.
- Mousebite defaults: drill `0.4mm`, spacing `0.7mm`, cuts.offset `-0.15mm`, prolong `0.6mm`.
- Annotation offset defaults to `0.5mm` outside the board edge. This is separate from mousebite `cuts.offset`.
- Top/bottom/left/right rotations are `270 / 90 / 0 / 180`.
- Default tab counts are top/bottom `2` and left/right `1`, unless geometry is too short or keepouts block safe placement.
- Standard tab width is `3.0mm`; narrow tabs use `1.8mm` by default, with `1.5mm` to `2.2mm` as the recommended narrow range.
- Parse complete `gr_line`, `gr_arc`, and `gr_circle` blocks, then filter each block for `(layer "Edge.Cuts")`.
- Treat near-edge Edge.Cuts `gr_circle` holes as keepouts before selecting tabs.
- Matrix panel tab planning must use opposite-edge pairing, not independent edge placement.
- Top and bottom tabs must share the same X coordinates. Left and right tabs must share the same Y coordinates.
- For top/bottom, compute top safe intervals and bottom safe intervals, then place tabs only in their X-axis intersections.
- For left/right, compute left safe intervals and right safe intervals, then place tabs only in their Y-axis intersections.
- For a board with an irregular top edge and a full bottom edge, bottom tabs must follow the top safe X positions. For a board with one irregular side edge and one full side edge, both side tabs must use common safe Y positions.
- If there are not enough overlapping safe intervals, reduce the paired tab count and warn. If no safe paired point exists, emit a strong warning.
- Never fall back to unaligned independent edge tab placement.
- On short paired intervals, try standard tabs, then narrow tabs, then reduce tab count with a strong warning.
- Automatic placement must enumerate multiple paired candidates from paired intervals instead of using only the first interval or midpoint.
- Candidate scoring may prefer feature clearance, opening/cutout distance, longer stable intervals, and board-center placement, but it must preserve top/bottom X pairing and left/right Y pairing.
- If a paired candidate fails feature clearance, try the next paired candidate. Never use an unaligned fallback.
- Inspect-only must show paired candidate evaluation so the user can see selected/skipped reasons.
- `--framing` controls KiKit framing: `railstb` is the default, `railslr` creates left/right rails, and `frame` creates a full four-side frame. Full frames still require KiCad visual inspection.
- Use manual `--tab-plan` for complex irregular boards, boards with proven production tab locations, or automatic placements that are valid but mechanically undesirable. Manual plans are engineer overrides and do not imply the automatic algorithm must choose the same location.
- For long narrow irregular boards, if automatic connector avoidance produces an unnatural side-tab location, specify the preferred middle connection in a manual tab plan and use `--framing frame` when a full four-side frame is needed.
- KiKit panelize success does not prove the mechanical connection locations are reasonable; visually inspect the generated panel in KiCad.


## Natural-Language Manual Tab Plans

When a user describes preferred tab coordinates in natural language, do not ask them to hand-write JSON. Convert the request into a `tab_plan.json` file in the output directory, then rerun `scripts/panelize.py` with `--tab-plan`.

Example user request: "Put two top/bottom tabs at X=87.4 and X=121.5; put the left/right tabs at Y=109.2; use 2.2mm width for the left/right tabs."

The agent should create a file such as `manual_tab_plan.json`:

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

Then rerun:

```bash
python scripts/panelize.py <input.kicad_pcb> --rows <ROWS> --cols <COLS> --framing <railstb|railslr|frame> --tab-plan <output_dir>/manual_tab_plan.json --output-dir <output_dir>
```

Rules for natural-language tab plans:

- Top/bottom tabs use X coordinates.
- Left/right tabs use Y coordinates.
- Top and bottom must be paired with the same X values.
- Left and right must be paired with the same Y values.
- If the user only says left/right width is `2.2mm`, apply `2.2` only to left/right and keep top/bottom at the default `3.0mm`.
- If no width is specified, use `3.0mm`.
- Manual tab plans are engineer overrides; they still require KiCad visual inspection.
- KiKit success does not mean the panel is ready for production.

## Windows KiKit Runner

Generation writes `run_kikit_panelize.ps1` and `run_kikit_panelize.bat` by default. Use `--no-runner` to suppress both. Inspect-only never writes files and never writes either runner. By default the runner only panelizes the requested full panel; add `--include-smoke-tests` to include `2x1` and `1x2` smoke panels.

For Mimo, Claude Code, Linux VMs, or other environments that cannot directly call Windows KiCad executables, the agent can generate the annotation PCB, JSON presets, and `run_kikit_panelize.ps1`; the user can then run the PowerShell script on Windows.

Recommended Windows command:

```powershell
cd <output_dir>
powershell -ExecutionPolicy Bypass -File .
un_kikit_panelize.ps1
```

Alternative:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.
un_kikit_panelize.ps1
```

The runner finds KiKit by checking `KIKIT_EXE`, common KiCad Windows paths, then `Get-Command kikit.exe` and `Get-Command kikit`. To force a path:

```powershell
$env:KIKIT_EXE = "D:\KiCad\9.0in\Scripts\kikit.exe"
```

The `.bat` file only calls the `.ps1`; the `.ps1` contains the KiKit lookup and panelize logic. The runner does not modify the original PCB. Generated panels still need KiCad visual inspection; KiKit success does not mean the panel is ready for production.

## Output Checks

After generation, verify:

- The annotation PCB exists and contains `footprint "kikit:Tab"`.
- The annotation PCB does not contain pseudo `(kikit:Tab ...)` nodes.
- Old `footprint "PCM_kikit:Tab"` blocks are gone.
- Presets contain `"tabs": {"type": "annotation"}`.
- `hspace` and `vspace` are unit strings.
- Top, bottom, left, and right tab rotations are correct.
- Top and bottom tab X coordinates are paired exactly.
- Left and right tab Y coordinates are paired exactly.
- Inspect-only reports paired interval sources, paired candidate evaluation, selected/skipped reasons, and alignment checks.
- The original PCB hash or modification time did not change.
