# Operating Manual

This manual describes how to use the KiCad KiKit Panelizer skill and script safely.

## Workflow

1. Confirm the input `.kicad_pcb` path.
2. Confirm the requested matrix size.
3. Run inspect-only.
4. Review bbox, Edge.Cuts segments, Edge.Cuts circles, keepouts, safe segments, paired interval sources, paired candidate evaluation, paired top/bottom X positions, paired left/right Y positions, alignment checks, recommended tabs, intervals, and warnings.
5. Generate annotation PCB and KiKit JSON presets.
6. Run KiKit with `-p`.
7. Visually inspect the output in KiCad before fabrication.

## Inspect First

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 5 --cols 10 --framing railstb --inspect-only
```

Inspect-only does not write files. It is required before formal output unless the user explicitly asks for fast generation.

Pause for user confirmation if warnings mention openings, short edges, Edge.Cuts circle keepouts, mounting holes near edges, connector keepouts, reduced paired tab counts, missing paired intervals, or overlap/spacing risk.

Inspect-only must be used to verify automatic matrix tab alignment:

- `paired top/bottom X positions` lists the X coordinates shared by top and bottom tabs.
- `paired left/right Y positions` lists the Y coordinates shared by left and right tabs.
- `alignment checks` should show zero delta for each top/bottom X pair and each left/right Y pair.
- `paired interval sources` shows which overlapping safe intervals were used.
- `paired candidate evaluation` shows each candidate coordinate, source interval, clearance result, score, and selected/skipped reason.

## Generate Annotation PCB and Presets

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 5 --cols 10 --framing railstb
```

Expected output files:

- `panel_output/board_annotation_tabs.kicad_pcb`
- `panel_output/board_test_2x1.json`
- `panel_output/board_test_1x2.json`
- `panel_output/board_panel_5x10.json`

The original PCB is not modified.

## Framing

Use `--framing` to choose the KiKit frame style written into the preset:

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 2 --cols 2 --framing frame
```

Supported values:

- `railstb`: top/bottom rails, default for backward compatibility.
- `railslr`: left/right rails.
- `frame`: complete four-side frame.

A full frame is useful when the panel needs outside support on all sides, but it does not replace KiCad visual inspection.

## Run KiKit 1.8+

KiKit 1.8 uses `-p` for the preset file:

```powershell
kikit panelize -p panel_output\board_panel_5x10.json panel_output\board_annotation_tabs.kicad_pcb panel_output\board_kikit_panel_5x10.kicad_pcb
```

Small test panels are strongly recommended:

```powershell
kikit panelize -p panel_output\board_test_2x1.json panel_output\board_annotation_tabs.kicad_pcb panel_output\board_test_2x1.kicad_pcb
kikit panelize -p panel_output\board_test_1x2.json panel_output\board_annotation_tabs.kicad_pcb panel_output\board_test_1x2.kicad_pcb
```

## Real KiCad Footprint Format

The script inserts real KiCad footprint blocks:

```lisp
(footprint "kikit:Tab"
  ...
  (layer "F.Cu")
  (at <x> <y> <rotation>)
  ...
  (fp_text user "KIKIT: width: <width>mm" ... (layer "Dwgs.User"))
)
```

Do not use pseudo nodes such as `(kikit:Tab ...)`.

## Annotation Offset

`--annotation-offset` defaults to `0.5` mm. It moves the `kikit:Tab` footprint origin outside the board edge so KiKit sees the annotation on or outside the outline.

This is not the same as mousebite `cuts.offset`, which remains `-0.15mm` by default.

Offset direction:

- top: `y = edge_y - annotation_offset`
- bottom: `y = edge_y + annotation_offset`
- left: `x = edge_x - annotation_offset`
- right: `x = edge_x + annotation_offset`

## Edge.Cuts Parsing

The script parses complete KiCad blocks first:

- `gr_line`
- `gr_arc`
- `gr_circle`

Only blocks containing `(layer "Edge.Cuts")` are used as outline or keepout geometry. Do not infer board outline from `Dwgs.User`, `Eco1.User`, `F.SilkS`, or other drawing layers.

## Edge.Cuts Circle Keepouts

Edge.Cuts circles near a board edge are treated as tab keepouts. The keepout interval is projected onto the edge direction and subtracted from candidate straight segments before tabs are placed.

Default values:

- edge keepout distance: `1.0mm`
- keepout clearance: `0.5mm`

## Opposite-Edge Pairing

Automatic matrix panel tabs must be planned as opposite-edge pairs:

- Top and bottom tabs share the same X coordinates.
- Left and right tabs share the same Y coordinates.
- Top, bottom, left, and right must not independently choose unrelated tab points.
- For top/bottom, compute safe intervals on both edges and use their X-axis intersections.
- For left/right, compute safe intervals on both edges and use their Y-axis intersections.
- If the top edge is irregular and the bottom edge is full length, bottom follows the top safe X positions.
- If one side edge is irregular and the opposite side is full length, both side tabs use common safe Y positions.
- If there are not enough overlapping safe intervals, reduce the paired tab count and report the reason.
- If no safe paired point exists, emit a strong warning. Do not fall back to unaligned independent placement.

KiKit can successfully produce a panel even when the tab locations are mechanically poor. Always visually inspect the generated panel in KiCad, especially for irregular boards, connector recesses, and asymmetric outlines.

## Candidate Evaluation

Automatic placement evaluates multiple paired candidates instead of using only the first interval or the midpoint of an interval.

Candidate evaluation must preserve these invariants:

- Top/bottom candidates share one X coordinate.
- Left/right candidates share one Y coordinate.
- If a candidate fails feature clearance, the next paired candidate is tried.
- There is no unaligned fallback.

Scoring may consider connector clearance, internal Edge.Cuts opening/cutout risk, longer paired intervals, board-center preference, and extreme-edge penalties. Inspect-only prints selected and skipped reasons so the user can decide whether automatic placement is mechanically acceptable.

## Short Segments

For paired multi-segment edges:

- Prefer overlapping safe interval midpoints.
- Use paired interval intersections, not independent edge midpoints.
- Select standard or narrow width per paired interval.
- Do not ignore a narrow paired interval just because another paired interval fits standard width.

For one short paired safe interval:

1. Try the requested count with standard width.
2. Try the requested count with narrow width.
3. Reduce the tab count if spacing still does not fit.
4. Emit a strong warning.

Tab interval:

```text
[center - width / 2, center + width / 2]
```

Default spacing checks:

- end clearance: `0.5mm`
- minimum gap between tab intervals: `0.8mm`

## Manual Tab Plan

Use `--tab-plan` when automatic placement is not appropriate. Good cases include complex irregular boards, boards with proven production tab locations, connector-heavy edges, large cutouts, slots, mounting holes, or automatic results that are valid but mechanically undesirable. A manual tab plan is an engineer override; it does not mean the automatic algorithm must force the same location.

For long narrow irregular boards, if automatic connector avoidance moves side tabs away from the preferred production location, specify the preferred middle side connection manually and use `--framing frame` when a full four-side frame is required.

Use `--tab-plan` like this:

```json
{
  "tabs": [
    {"edge": "bottom", "x": 145.8, "width": 3.0},
    {"edge": "bottom", "x": 163.5, "width": 2.2},
    {"edge": "left", "y": 76.0, "width": 3.0}
  ]
}
```

## Verification Checklist

After generation, confirm:

- The source PCB hash or modified time is unchanged.
- The annotation PCB contains `footprint "kikit:Tab"`.
- The annotation PCB does not contain `(kikit:Tab ...)`.
- Old `footprint "PCM_kikit:Tab"` entries are gone.
- JSON contains `"tabs": {"type": "annotation"}`.
- `hspace` and `vspace` are unit strings such as `"2mm"`.
- Top, bottom, left, and right rotations are `270`, `90`, `0`, and `180`.
- Top and bottom tab X coordinates are exactly paired.
- Left and right tab Y coordinates are exactly paired.
- Inspect-only alignment checks report zero deltas.
- Inspect-only candidate evaluation explains selected/skipped tab positions.
- Tabs are not inside openings, short transition edges, rounded corners, holes, or connector keepouts.
- KiKit panelize succeeds and the generated panel is visually inspected in KiCad for aligned mousebite locations.
