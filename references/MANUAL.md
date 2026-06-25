# Operating Manual

This manual describes how to use the KiCad KiKit Panelizer skill and script safely.

## Workflow

1. Confirm the input `.kicad_pcb` path.
2. Confirm the requested matrix size.
3. Run inspect-only.
4. Review bbox, Edge.Cuts segments, Edge.Cuts circles, keepouts, safe segments, recommended tabs, intervals, and warnings.
5. Generate annotation PCB and KiKit JSON presets.
6. Run KiKit with `-p`.
7. Visually inspect the output in KiCad before fabrication.

## Inspect First

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 5 --cols 10 --inspect-only
```

Inspect-only does not write files. It is required before formal output unless the user explicitly asks for fast generation.

Pause for user confirmation if warnings mention openings, short edges, Edge.Cuts circle keepouts, mounting holes near edges, connector keepouts, reduced tab counts, or overlap/spacing risk.

## Generate Annotation PCB and Presets

```powershell
python scripts/panelize.py path\to\board.kicad_pcb --rows 5 --cols 10
```

Expected output files:

- `panel_output/board_annotation_tabs.kicad_pcb`
- `panel_output/board_test_2x1.json`
- `panel_output/board_test_1x2.json`
- `panel_output/board_panel_5x10.json`

The original PCB is not modified.

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

## Short Segments

For multi-segment edges:

- Prefer safe segment midpoints.
- Use at most one automatic tab per safe segment.
- Select standard or narrow width per segment.
- Do not ignore a narrow-safe segment just because another segment fits standard width.

For one short safe segment:

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

Use `--tab-plan` when automatic placement is not appropriate:

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
- Tabs are not inside openings, short transition edges, rounded corners, holes, or connector keepouts.
