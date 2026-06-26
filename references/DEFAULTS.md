# Defaults and Edge-Case Rules

Use this reference when a parameter value or placement rule is needed.

## Default Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| Drill | `0.4mm` | Mousebite drill diameter |
| Spacing | `0.7mm` | Center-to-center mousebite hole spacing |
| Cuts offset | `-0.15mm` | Shifts the mousebite row slightly toward the tab/web side to help keep the finished board edge cleaner. Do not make the negative offset too large, or the holes may no longer bite enough into the board edge. |
| Prolong | `0.6mm` | Extension of the mousebite cut beyond the hole row |
| Annotation offset | `0.5mm` | Moves the `kikit:Tab` footprint origin outside the board edge. This is separate from mousebite `cuts.offset`. |
| Standard tab width | `3.0mm` | Used when the safe segment is long enough |
| Narrow tab width | `1.8mm` | Default narrow width; use `1.5mm` to `2.2mm` for tight safe segments |
| End clearance | `0.5mm` | Minimum clearance from a safe segment end |
| Minimum tab gap | `0.8mm` | Minimum gap between tab intervals on the same segment |
| Edge circle keepout distance | `1.0mm` | A near-edge Edge.Cuts circle becomes a keepout when within radius plus this distance of the edge |
| Keepout clearance | `0.5mm` | Extra clearance around a circle keepout interval |
| Top edge tabs | `2` | Per row-to-row connection when paired top/bottom safe X intervals allow |
| Bottom edge tabs | `2` | Uses the same X coordinates as top tabs |
| Left edge tabs | `1` | Per column-to-column connection when paired left/right safe Y intervals allow |
| Right edge tabs | `1` | Uses the same Y coordinates as left tabs |
| H/V spacing | `2mm` | JSON length values must include units |

## Coordinate System

KiCad uses a Y-down coordinate system:

- `bbox_min.y` is the top edge.
- `bbox_max.y` is the bottom edge.
- `bbox_min.x` is the left edge.
- `bbox_max.x` is the right edge.

Tab rotations:

- top: `270`
- bottom: `90`
- left: `0`
- right: `180`

Annotation footprint origin offset:

- top: `y = edge_y - annotation_offset`
- bottom: `y = edge_y + annotation_offset`
- left: `x = edge_x - annotation_offset`
- right: `x = edge_x + annotation_offset`

## Placement Rules

- Do not overwrite the source PCB.
- Remove existing `footprint "kikit:Tab"` and `footprint "PCM_kikit:Tab"` before inserting new ones.
- Insert real `footprint "kikit:Tab"` footprints, never pseudo `(kikit:Tab ...)` nodes.
- Use KiKit annotation mode in JSON: `"tabs": {"type": "annotation"}`.
- Parse complete `gr_line`, `gr_arc`, and `gr_circle` blocks first, then filter each block for `(layer "Edge.Cuts")`.
- Ignore non-Edge.Cuts layers such as `Dwgs.User`, `Eco1.User`, and `F.SilkS` for board outline geometry.
- Treat near-edge Edge.Cuts `gr_circle` holes as keepouts.
- Place tabs on safe straight segments, not inside notches, slots, rounded transitions, mounting holes, or connector keepouts.
- Use opposite-edge pairing for automatic matrix panel tabs.
- Top and bottom must share one set of X coordinates. Left and right must share one set of Y coordinates.
- Do not let top, bottom, left, and right independently choose unrelated tab points.
- For top/bottom, intersect top safe intervals with bottom safe intervals on the X axis, then choose paired X coordinates from those intersections.
- For left/right, intersect left safe intervals with right safe intervals on the Y axis, then choose paired Y coordinates from those intersections.
- If one edge is irregular and the opposite edge is full length, the full edge follows the irregular edge's safe paired coordinates.
- If there are fewer overlapping intervals than requested tabs, reduce the paired tab count and emit a warning.
- If no safe paired point exists, emit a strong warning and do not use an unaligned independent-placement fallback.
- On one short paired interval, try the requested count with standard width, then narrow width, then reduce count with a strong warning.

## Edge.Cuts Circle Keepouts

For horizontal top/bottom segments:

```text
if abs(circle_center_y - edge_y) <= radius + edge_keepout_distance:
    subtract [circle_center_x - radius - keepout_clearance,
              circle_center_x + radius + keepout_clearance]
```

For vertical left/right segments:

```text
if abs(circle_center_x - edge_x) <= radius + edge_keepout_distance:
    subtract [circle_center_y - radius - keepout_clearance,
              circle_center_y + radius + keepout_clearance]
```

## Risk Checklist

Before generation, inspect and report:

- Edge openings, slots, Type-C or USB recesses.
- Edge.Cuts circles near a board edge.
- Mounting holes close to a tab candidate.
- Board-edge connectors, gold fingers, or keepout-sensitive components.
- Safe segments shorter than the requested tab count and width allow.
- Paired top/bottom X positions and whether each pair has zero delta.
- Paired left/right Y positions and whether each pair has zero delta.
- Paired interval sources used to choose tab positions.
- Reduced tab count or narrow tabs.
- Any strong warning from inspect-only.
- KiKit panelize success is not enough by itself; visually inspect that mousebites and tabs line up mechanically in KiCad.

## User Confirmation Template

Use this when inspect-only reports a real placement risk:

```text
I detected a board-edge risk: <feature or warning>.
Default behavior is mousebite panelization with annotation tabs, 0.5mm annotation offset, and KiKit annotation-mode presets.
Please confirm whether to continue with the recommended tab placements or provide a manual --tab-plan.
```
