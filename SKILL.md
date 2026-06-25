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
python scripts/panelize.py <input.kicad_pcb> --rows <ROWS> --cols <COLS> --inspect-only
```

Inspect-only does not write files. It reports board bbox, Edge.Cuts segments, Edge.Cuts circles, circle keepouts, safe segments, recommended tabs, tab intervals, annotation offset results, and warnings.

Do not skip inspect-only unless the user explicitly asks for fast generation. If warnings mention openings, short edges, holes near edges, connector keepouts, reduced tab counts, or spacing risks, pause and confirm with the user before formal output.

4. Generate annotation PCB and presets only after inspect-only looks reasonable:

```bash
python scripts/panelize.py <input.kicad_pcb> --rows <ROWS> --cols <COLS>
```

5. Run KiKit 1.8+ with `-p`:

```bash
kikit panelize -p <preset.json> <annotation_pcb.kicad_pcb> <output_panel.kicad_pcb>
```

For production work, run small `2x1` and `1x2` tests and visually inspect the result in KiCad before a full panel.

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
- On multi-segment edges, prefer safe segment midpoints instead of merging all segments into one span.
- On short single segments, try standard tabs, then narrow tabs, then reduce tab count with a strong warning.

## Output Checks

After generation, verify:

- The annotation PCB exists and contains `footprint "kikit:Tab"`.
- The annotation PCB does not contain pseudo `(kikit:Tab ...)` nodes.
- Old `footprint "PCM_kikit:Tab"` blocks are gone.
- Presets contain `"tabs": {"type": "annotation"}`.
- `hspace` and `vspace` are unit strings.
- Top, bottom, left, and right tab rotations are correct.
- The original PCB hash or modification time did not change.
