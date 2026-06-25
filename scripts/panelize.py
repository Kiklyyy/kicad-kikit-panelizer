#!/usr/bin/env python3
"""
panelize.py — KiCad PCB tab annotator and KiKit preset generator.

Reads a .kicad_pcb, extracts Edge.Cuts boundary, detects edge features,
inserts real kikit:Tab footprints as text-level safe edits, and emits
KiKit JSON presets in annotation mode.

Never overwrites the original file.

Usage:
    python3 panelize.py <input.kicad_pcb> [--rows 5] [--cols 4] ...
"""

from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

NUMBER_RE = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'


# ─── Helpers ────────────────────────────────────────────────────────────────


def new_uuid() -> str:
    return str(uuid.uuid4())


def find_matching_close(text: str, open_pos: int) -> int:
    """Find the ')' matching the '(' at open_pos via bracket counting."""
    depth = 0
    i = open_pos
    in_string = False
    while i < len(text):
        c = text[i]
        if c == '"':
            in_string = not in_string
        elif not in_string:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


# ─── Data classes ───────────────────────────────────────────────────────────


@dataclass
class Point:
    x: float
    y: float
    def dist(self, o: 'Point') -> float:
        return math.hypot(self.x - o.x, self.y - o.y)


@dataclass
class LineSegment:
    p1: Point
    p2: Point
    kind: str = 'gr_line'
    mid: Optional[Point] = None
    def length(self) -> float:
        return self.p1.dist(self.p2)
    def midpoint(self) -> Point:
        return Point((self.p1.x + self.p2.x) / 2, (self.p1.y + self.p2.y) / 2)
    def is_horizontal(self, tol: float = 0.01) -> bool:
        return abs(self.p1.y - self.p2.y) < tol
    def is_vertical(self, tol: float = 0.01) -> bool:
        return abs(self.p1.x - self.p2.x) < tol


@dataclass
class EdgeFeature:
    kind: str
    center: Point
    radius: float = 0.0
    description: str = ''


@dataclass
class EdgeCircle:
    center: Point
    radius: float


@dataclass
class TabPlacement:
    x: float
    y: float
    width: float
    orientation: str   # 'vertical' or 'horizontal'
    edge: str          # 'top', 'bottom', 'left', 'right'
    narrow: bool = False
    anchor_x: float = 0.0
    anchor_y: float = 0.0
    interval_start: float = 0.0
    interval_end: float = 0.0
    annotation_offset: float = 0.5


# ─── Edge.Cuts extraction ──────────────────────────────────────────────────


def iter_kicad_blocks(pcb_text: str, name: str) -> List[str]:
    """Return complete KiCad s-expression blocks named `name`."""
    blocks: List[str] = []
    pat = re.compile(r'\(\s*' + re.escape(name) + r'\b')
    for m in pat.finditer(pcb_text):
        end = find_matching_close(pcb_text, m.start())
        if end != -1:
            blocks.append(pcb_text[m.start():end + 1])
    return blocks


def is_edge_cuts_block(block: str) -> bool:
    return re.search(r'\(layer\s+"?Edge\.Cuts"?\)', block) is not None


def extract_point(block: str, key: str) -> Optional[Point]:
    m = re.search(r'\(' + re.escape(key) + r'\s+(' + NUMBER_RE + r')\s+(' + NUMBER_RE + r')\)', block)
    if not m:
        return None
    return Point(float(m.group(1)), float(m.group(2)))


def extract_edge_cuts_segments(pcb_text: str) -> List[LineSegment]:
    segments: List[LineSegment] = []
    for block in iter_kicad_blocks(pcb_text, 'gr_line'):
        if not is_edge_cuts_block(block):
            continue
        start = extract_point(block, 'start')
        end = extract_point(block, 'end')
        if start and end:
            segments.append(LineSegment(start, end, kind='gr_line'))

    for block in iter_kicad_blocks(pcb_text, 'gr_arc'):
        if not is_edge_cuts_block(block):
            continue
        start = extract_point(block, 'start')
        mid = extract_point(block, 'mid')
        end = extract_point(block, 'end')
        if start and end:
            segments.append(LineSegment(start, end, kind='gr_arc', mid=mid))
    return segments


def extract_edge_cuts_circles(pcb_text: str) -> List[EdgeCircle]:
    circles: List[EdgeCircle] = []
    for block in iter_kicad_blocks(pcb_text, 'gr_circle'):
        if not is_edge_cuts_block(block):
            continue
        center = extract_point(block, 'center')
        end = extract_point(block, 'end')
        if center and end:
            circles.append(EdgeCircle(center=center, radius=center.dist(end)))
    return circles
def compute_bbox(segments: List[LineSegment]) -> Tuple[Point, Point]:
    if not segments:
        return Point(0, 0), Point(100, 100)
    xs, ys = [], []
    for s in segments:
        xs.extend([s.p1.x, s.p2.x])
        ys.extend([s.p1.y, s.p2.y])
        if s.mid:
            xs.append(s.mid.x)
            ys.append(s.mid.y)
    return Point(min(xs), min(ys)), Point(max(xs), max(ys))


def classify_edges(segments: List[LineSegment], bmin: Point, bmax: Point) -> dict:
    """KiCad Y-down: bmin.y=top, bmax.y=bottom, bmin.x=left, bmax.x=right."""
    tol = 0.5
    edges: dict = {'top': [], 'bottom': [], 'left': [], 'right': [], 'other': []}
    for s in segments:
        if s.is_horizontal():
            y = (s.p1.y + s.p2.y) / 2
            if abs(y - bmin.y) < tol:
                edges['top'].append(s)
            elif abs(y - bmax.y) < tol:
                edges['bottom'].append(s)
            else:
                edges['other'].append(s)
        elif s.is_vertical():
            x = (s.p1.x + s.p2.x) / 2
            if abs(x - bmin.x) < tol:
                edges['left'].append(s)
            elif abs(x - bmax.x) < tol:
                edges['right'].append(s)
            else:
                edges['other'].append(s)
        else:
            edges['other'].append(s)
    return edges


# ─── Edge feature detection ─────────────────────────────────────────────────


def detect_edge_features(pcb_text: str, bmin: Point, bmax: Point) -> List[EdgeFeature]:
    features: List[EdgeFeature] = []
    margin = 3.0
    fp_pat = re.compile(r'\(footprint\s+"([^"]+)"', re.IGNORECASE)
    at_pat = re.compile(r'\(at\s+(' + NUMBER_RE + r')\s+(' + NUMBER_RE + r')(?:\s+' + NUMBER_RE + r')?\)')
    npth_pat = re.compile(r'\(pad\s+\S+\s+np_thru_hole\b')
    size_pat = re.compile(r'\(size\s+([\d.+-e]+)\s+([\d.+-e]+)\)')

    already_classified = set()  # track footprint start positions

    for m in fp_pat.finditer(pcb_text):
        fp_name = m.group(1)
        fp_start = m.start()
        paren = pcb_text.rfind('(', 0, fp_start + 1)
        if paren == -1:
            continue
        fp_end = find_matching_close(pcb_text, paren)
        if fp_end == -1:
            continue
        fp_text = pcb_text[paren:fp_end + 1]

        at_m = at_pat.search(fp_text)
        if not at_m:
            continue
        cx, cy = float(at_m.group(1)), float(at_m.group(2))
        center = Point(cx, cy)

        near = (center.x < bmin.x + margin or center.x > bmax.x - margin or
                center.y < bmin.y + margin or center.y > bmax.y - margin)
        if not near:
            continue

        fp_lower = fp_name.lower()
        kind = ''
        desc = ''
        if any(k in fp_lower for k in ['mounting', 'mount', 'mhole', 'standoff']):
            kind, desc = 'mounting_hole', f'Mounting hole: {fp_name}'
        elif any(k in fp_lower for k in ['usb', 'typec', 'type-c', 'usbc']):
            kind, desc = 'connector', f'USB connector: {fp_name}'
        elif any(k in fp_lower for k in ['conn', 'header', 'jst', 'fpc', 'ffc']):
            kind, desc = 'connector', f'Connector: {fp_name}'
        elif any(k in fp_lower for k in ['slot', 'cutout']):
            kind, desc = 'slot', f'Slot/cutout: {fp_name}'
        elif any(k in fp_lower for k in ['gold', 'finger', 'edge_connector']):
            kind, desc = 'goldfinger', f'Gold finger: {fp_name}'

        if kind:
            features.append(EdgeFeature(kind=kind, center=center, description=desc))
            already_classified.add(paren)
        elif npth_pat.search(fp_text):
            # Unnamed footprint with NPTH pad — treat as mounting hole
            sm = size_pat.search(fp_text)
            r = float(sm.group(1)) / 2 if sm else 1.0
            features.append(EdgeFeature(
                kind='mounting_hole', center=center, radius=r,
                description=f'NPTH at ({center.x:.1f}, {center.y:.1f})'))
            already_classified.add(paren)

    return features


# ─── Tab placement ──────────────────────────────────────────────────────────


def detect_edge_opening_risk(edges: dict) -> bool:
    outer_split = any(len([s for s in edges[name] if s.length() > 1.0]) > 1
                      for name in ('top', 'bottom', 'left', 'right'))
    arcs_or_internal_edges = any(s.kind == 'gr_arc' for ss in edges.values() for s in ss)
    return outer_split or arcs_or_internal_edges or bool(edges.get('other'))


def segment_report(segments: List[LineSegment], edges: dict) -> List[dict]:
    edge_lookup = {}
    for edge, ss in edges.items():
        for s in ss:
            edge_lookup[id(s)] = edge
    rows = []
    for s in segments:
        item = {
            'kind': s.kind,
            'edge': edge_lookup.get(id(s), 'unknown'),
            'start': [round(s.p1.x, 3), round(s.p1.y, 3)],
            'end': [round(s.p2.x, 3), round(s.p2.y, 3)],
            'length': round(s.length(), 3),
        }
        if s.mid:
            item['mid'] = [round(s.mid.x, 3), round(s.mid.y, 3)]
        rows.append(item)
    return rows


def compute_tab_placements(
    segments: List[LineSegment],
    features: List[EdgeFeature],
    bmin: Point, bmax: Point,
    tab_top: int = 2, tab_bot: int = 2,
    tab_left: int = 1, tab_right: int = 1,
    tab_width: float = 3.0, narrow_width: float = 1.8,
    feat_margin: float = 3.0,
    circles: Optional[List[EdgeCircle]] = None,
    annotation_offset: float = 0.5,
    edge_keepout_distance: float = 1.0,
    keepout_clearance: float = 0.5,
    end_clearance: float = 0.5,
    min_tab_gap: float = 0.8,
) -> Tuple[List[TabPlacement], List[str], dict]:
    edges = classify_edges(segments, bmin, bmax)
    circles = circles or []
    placements: List[TabPlacement] = []
    warnings: List[str] = []
    debug = {'edge_circles': [], 'circle_keepouts': [], 'safe_segments': []}

    for c in circles:
        debug['edge_circles'].append({'center': [round(c.center.x, 3), round(c.center.y, 3)], 'radius': round(c.radius, 3)})

    def is_clear(x: float, y: float, hw: float) -> Tuple[bool, str]:
        for f in features:
            d = math.hypot(x - f.center.x, y - f.center.y)
            md = feat_margin + f.radius + hw
            if d < md:
                return False, (f'Tab anchor at ({x:.1f},{y:.1f}) near {f.description} '
                               f'({f.center.x:.1f},{f.center.y:.1f}) {d:.1f}<{md:.1f}mm')
        return True, ''

    def sorted_edge_segments(edge_segs: List[LineSegment], horiz: bool) -> List[LineSegment]:
        return sorted(edge_segs, key=lambda s: min(s.p1.x, s.p2.x) if horiz else min(s.p1.y, s.p2.y))

    def edge_offset_point(edge: str, ax: float, ay: float) -> Tuple[float, float]:
        if edge == 'top': return ax, ay - annotation_offset
        if edge == 'bottom': return ax, ay + annotation_offset
        if edge == 'left': return ax - annotation_offset, ay
        if edge == 'right': return ax + annotation_offset, ay
        return ax, ay

    def make_tab(edge: str, ax: float, ay: float, width: float, interval: Tuple[float, float], horiz: bool) -> TabPlacement:
        fx, fy = edge_offset_point(edge, ax, ay)
        return TabPlacement(x=round(fx, 3), y=round(fy, 3), width=width,
                            orientation='vertical' if horiz else 'horizontal', edge=edge,
                            narrow=(width != tab_width), anchor_x=round(ax, 3), anchor_y=round(ay, 3),
                            interval_start=round(interval[0], 3), interval_end=round(interval[1], 3),
                            annotation_offset=annotation_offset)

    def safe_segments(edge_segs: List[LineSegment], edge: str, horiz: bool) -> List[LineSegment]:
        safe: List[LineSegment] = []
        for s in sorted_edge_segments(edge_segs, horiz):
            axis_lo = min(s.p1.x, s.p2.x) if horiz else min(s.p1.y, s.p2.y)
            axis_hi = max(s.p1.x, s.p2.x) if horiz else max(s.p1.y, s.p2.y)
            const = (s.p1.y + s.p2.y) / 2 if horiz else (s.p1.x + s.p2.x) / 2
            intervals = [(axis_lo, axis_hi)]
            for c in circles:
                distance_to_edge = abs(c.center.y - const) if horiz else abs(c.center.x - const)
                if distance_to_edge > c.radius + edge_keepout_distance:
                    continue
                ko_lo = (c.center.x if horiz else c.center.y) - c.radius - keepout_clearance
                ko_hi = (c.center.x if horiz else c.center.y) + c.radius + keepout_clearance
                if ko_hi <= axis_lo or ko_lo >= axis_hi:
                    continue
                debug['circle_keepouts'].append({'edge': edge, 'circle_center': [round(c.center.x, 3), round(c.center.y, 3)],
                                                 'radius': round(c.radius, 3), 'interval': [round(max(axis_lo, ko_lo), 3), round(min(axis_hi, ko_hi), 3)]})
                next_intervals = []
                for lo, hi in intervals:
                    if ko_hi <= lo or ko_lo >= hi:
                        next_intervals.append((lo, hi)); continue
                    if ko_lo > lo:
                        next_intervals.append((lo, max(lo, ko_lo)))
                    if ko_hi < hi:
                        next_intervals.append((min(hi, ko_hi), hi))
                intervals = [(lo, hi) for lo, hi in next_intervals if hi - lo > 0.001]
            for lo, hi in intervals:
                ss = LineSegment(Point(lo, const), Point(hi, const), kind='safe') if horiz else LineSegment(Point(const, lo), Point(const, hi), kind='safe')
                safe.append(ss)
                debug['safe_segments'].append({'edge': edge, 'start': [round(ss.p1.x, 3), round(ss.p1.y, 3)],
                                               'end': [round(ss.p2.x, 3), round(ss.p2.y, 3)], 'length': round(ss.length(), 3)})
        return safe

    def segment_axis(s: LineSegment, horiz: bool) -> Tuple[float, float, float]:
        lo = min(s.p1.x, s.p2.x) if horiz else min(s.p1.y, s.p2.y)
        hi = max(s.p1.x, s.p2.x) if horiz else max(s.p1.y, s.p2.y)
        const = (s.p1.y + s.p2.y) / 2 if horiz else (s.p1.x + s.p2.x) / 2
        return lo, hi, const

    def tab_points_on_segment(s: LineSegment, count: int, width: float, horiz: bool) -> Optional[List[Tuple[float, float, Tuple[float, float]]]]:
        lo, hi, const = segment_axis(s, horiz)
        length = hi - lo
        required = count * width + (count - 1) * min_tab_gap + 2 * end_clearance
        if count <= 0 or length + 1e-9 < required:
            return None
        usable_lo = lo + end_clearance + width / 2
        usable_hi = hi - end_clearance - width / 2
        coords = [(usable_lo + usable_hi) / 2] if count == 1 else [usable_lo + i * (usable_hi - usable_lo) / (count - 1) for i in range(count)]
        result = []
        for coord in coords:
            ax, ay = (coord, const) if horiz else (const, coord)
            result.append((ax, ay, (coord - width / 2, coord + width / 2)))
        return result

    def one_tab_on_segment(s: LineSegment, edge: str, horiz: bool) -> Optional[TabPlacement]:
        for width in (tab_width, narrow_width):
            pts = tab_points_on_segment(s, 1, width, horiz)
            if not pts:
                continue
            ax, ay, interval = pts[0]
            ok, msg = is_clear(ax, ay, width / 2)
            if ok:
                return make_tab(edge, ax, ay, width, interval, horiz)
            warnings.append(f'{msg} - skipped')
        return None

    def place(edge_segs: List[LineSegment], edge: str, count: int, horiz: bool):
        if not edge_segs:
            warnings.append(f'No {edge} edge segments found'); return
        safe = safe_segments(edge_segs, edge, horiz)
        usable = [s for s in safe if s.length() >= narrow_width + 2 * end_clearance]
        if not usable:
            warnings.append(f'STRONG WARNING: {edge} edge has no safe segment long enough for a {narrow_width}mm tab after keepouts'); return
        if len(safe) != len(edge_segs) or any(s.length() < e.length() - 0.001 for s in safe for e in edge_segs if (s.is_horizontal() == e.is_horizontal())):
            warnings.append(f'{edge} edge safe segments adjusted after Edge.Cuts circle keepout subtraction')
        ordered = sorted_edge_segments(usable, horiz)
        if len(ordered) > 1:
            if count > len(ordered):
                warnings.append(f'STRONG WARNING: Reduced tab count from {count} to {len(ordered)} on {edge}; one tab per safe segment')
            chosen = [ordered[0]] if count == 1 else [ordered[0], ordered[-1]]
            for s in chosen[:count]:
                tab = one_tab_on_segment(s, edge, horiz)
                if tab: placements.append(tab)
                else: warnings.append(f'STRONG WARNING: {edge} safe segment {s.length():.2f}mm too short after spacing checks')
            return
        s = ordered[0]
        original_count = count
        selected_pts = None
        selected_width = tab_width
        for width in (tab_width, narrow_width):
            selected_pts = tab_points_on_segment(s, count, width, horiz)
            selected_width = width
            if selected_pts: break
        if not selected_pts and count > 1:
            warnings.append(f'STRONG WARNING: Reduced tab count from {original_count} to 1 because segment is too short or keepout blocked on {edge}')
            count = 1
            for width in (tab_width, narrow_width):
                selected_pts = tab_points_on_segment(s, count, width, horiz)
                selected_width = width
                if selected_pts: break
        if not selected_pts:
            warnings.append(f'STRONG WARNING: {edge} edge segment {s.length():.2f}mm cannot fit even one narrow tab'); return
        if selected_width != tab_width:
            warnings.append(f'{edge} edge uses narrow tabs ({selected_width}mm) after spacing checks')
        for ax, ay, interval in selected_pts:
            ok, msg = is_clear(ax, ay, selected_width / 2)
            if not ok:
                warnings.append(f'{msg} - skipped'); continue
            placements.append(make_tab(edge, ax, ay, selected_width, interval, horiz))

    place(edges['top'], 'top', tab_top, True)
    place(edges['bottom'], 'bottom', tab_bot, True)
    place(edges['left'], 'left', tab_left, False)
    place(edges['right'], 'right', tab_right, False)
    return placements, warnings, debug

def placements_from_tab_plan(tab_plan: dict, bmin: Point, bmax: Point,
                             tab_width: float = 3.0, annotation_offset: float = 0.5) -> List[TabPlacement]:
    rows = tab_plan if isinstance(tab_plan, list) else tab_plan.get('tabs', [])
    placements: List[TabPlacement] = []
    for i, item in enumerate(rows):
        edge = item.get('edge')
        if edge not in ('top', 'bottom', 'left', 'right'):
            raise ValueError(f'tab-plan entry {i} has invalid edge: {edge!r}')
        width = float(item.get('width', tab_width))
        if edge in ('top', 'bottom'):
            if 'x' not in item:
                raise ValueError(f'tab-plan entry {i} on {edge} requires x')
            ax = float(item['x'])
            ay = float(item.get('y', bmin.y if edge == 'top' else bmax.y))
            orientation = 'vertical'
            interval = (ax - width / 2, ax + width / 2)
            fx, fy = (ax, ay - annotation_offset) if edge == 'top' else (ax, ay + annotation_offset)
        else:
            if 'y' not in item:
                raise ValueError(f'tab-plan entry {i} on {edge} requires y')
            ax = float(item.get('x', bmin.x if edge == 'left' else bmax.x))
            ay = float(item['y'])
            orientation = 'horizontal'
            interval = (ay - width / 2, ay + width / 2)
            fx, fy = (ax - annotation_offset, ay) if edge == 'left' else (ax + annotation_offset, ay)
        placements.append(TabPlacement(x=round(fx, 3), y=round(fy, 3), width=width,
                                       orientation=orientation, edge=edge,
                                       narrow=(width != tab_width), anchor_x=round(ax, 3),
                                       anchor_y=round(ay, 3), interval_start=round(interval[0], 3),
                                       interval_end=round(interval[1], 3), annotation_offset=annotation_offset))
    return placements

def load_tab_plan(value: Optional[str]) -> Optional[dict]:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        with open(value, 'r', encoding='utf-8') as f:
            return json.load(f)


def tab_rotation(tab: TabPlacement) -> int:
    return {'top': 270, 'bottom': 90, 'left': 0, 'right': 180}.get(tab.edge, 0)


def build_tab_footprint(tab: TabPlacement, num: int) -> str:
    """Build a real KiCad footprint block for a kikit:Tab annotation."""
    uid = new_uuid()
    pad_uid = new_uuid()
    fp_txt_uid = new_uuid()
    w = f'{tab.width:.1f}' if tab.width != int(tab.width) else str(int(tab.width))
    return (
        f'(footprint "kikit:Tab"\n'
        f'    (layer "F.Cu")\n'
        f'    (uuid "{uid}")\n'
        f'    (at {tab.x} {tab.y} {tab_rotation(tab)})\n'
        f'    (attr board_only exclude_from_pos_files exclude_from_bom)\n'
        f'    (fp_text reference "KIKIT{num:02d}" (at 0 -2) (layer "F.SilkS")\n'
        f'      (uuid "{fp_txt_uid}")\n'
        f'      (effects (font (size 1 1) (thickness 0.15)))\n'
        f'    )\n'
        f'    (fp_text user "KIKIT: width: {w}mm" (at 0 2) (layer "Dwgs.User")\n'
        f'      (uuid "{new_uuid()}")\n'
        f'      (effects (font (size 0.8 0.8) (thickness 0.12)))\n'
        f'    )\n'
        f'    (pad "" smd rect (at 0 0) (size {tab.width} 0.5) (layers "F.Cu")\n'
        f'      (uuid "{pad_uid}")\n'
        f'    )\n'
        f'  )'
    )


def remove_old_tab_footprints(pcb_text: str) -> Tuple[str, int]:
    """Remove footprint "kikit:Tab" and footprint "PCM_kikit:Tab" blocks."""
    count = 0
    parts = []
    i = 0
    pat = re.compile(r'\(\s*footprint\s+"(?:PCM_kikit:Tab|kikit:Tab)"')
    while i < len(pcb_text):
        m = pat.search(pcb_text, i)
        if not m:
            parts.append(pcb_text[i:])
            break
        op = pcb_text.rfind('(', 0, m.start() + 1)
        if op == -1:
            parts.append(pcb_text[i:m.start() + 1])
            i = m.start() + 1
            continue
        cl = find_matching_close(pcb_text, op)
        if cl == -1:
            parts.append(pcb_text[i:m.start() + 1])
            i = m.start() + 1
            continue
        end = cl + 1
        while end < len(pcb_text) and pcb_text[end] in ' \t':
            end += 1
        if end < len(pcb_text) and pcb_text[end] == '\n':
            end += 1
        parts.append(pcb_text[i:op])
        count += 1
        i = end
    return ''.join(parts), count


def insert_tab_footprints(pcb_text: str, placements: List[TabPlacement]) -> str:
    """Insert real kikit:Tab footprints before the last top-level ')'."""
    if not placements:
        return pcb_text
    stripped = pcb_text.rstrip()
    lp = stripped.rfind(')')
    if lp == -1:
        return stripped + '\n' + '\n'.join(build_tab_footprint(t, i + 1) for i, t in enumerate(placements)) + '\n'
    blocks = '\n'.join(build_tab_footprint(t, i + 1) for i, t in enumerate(placements))
    return stripped[:lp] + '\n' + blocks + '\n' + stripped[lp:]


# ─── KiKit JSON preset (annotation mode) ────────────────────────────────────


def generate_kikit_preset(rows: int, cols: int,
                          drill: float = 0.4, spacing: float = 0.7,
                          offset: float = -0.15, prolong: float = 0.6,
                          frame_width: float = 5.0,
                          hspace: float = 2.0, vspace: float = 2.0) -> dict:
    return {
        "layout": {"rows": rows, "cols": cols, "hspace": f"{hspace:g}mm", "vspace": f"{vspace:g}mm"},
        "tabs": {"type": "annotation"},
        "cuts": {"type": "mousebites", "drill": f"{drill}mm", "spacing": f"{spacing}mm",
                 "offset": f"{offset}mm", "prolong": f"{prolong}mm"},
        "framing": {"type": "railstb", "width": f"{frame_width}mm", "cuts": "both"},
        "tooling": {"type": "3hole", "hoffset": "2.5mm", "voffset": "2.5mm", "size": "3.2mm"},
        "post": {"millradius": "0.5mm"},
    }


# ─── Main orchestration ─────────────────────────────────────────────────────


def result_base(input_path: str, rows: int, cols: int, bmin: Point, bmax: Point,
                segments: List[LineSegment], edges: dict, features: List[EdgeFeature],
                placements: List[TabPlacement], warnings: List[str],
                edge_opening_risk: bool, inspect_only: bool = False,
                placement_debug: Optional[dict] = None) -> dict:
    return {
        'input': input_path,
        'board_bbox': {
            'min': [round(bmin.x, 3), round(bmin.y, 3)],
            'max': [round(bmax.x, 3), round(bmax.y, 3)],
        },
        'board_size': {'width': round(bmax.x - bmin.x, 2), 'height': round(bmax.y - bmin.y, 2)},
        'edge_segments': segment_report(segments, edges),
        'edge_circles': (placement_debug or {}).get('edge_circles', []),
        'circle_keepouts': (placement_debug or {}).get('circle_keepouts', []),
        'safe_segments': (placement_debug or {}).get('safe_segments', []),
        'edge_opening_risk': edge_opening_risk,
        'features_detected': [{'kind': f.kind, 'description': f.description,
                               'center': [f.center.x, f.center.y]} for f in features],
        'placements': [{'x': p.x, 'y': p.y, 'width': p.width,
                        'anchor_x': p.anchor_x, 'anchor_y': p.anchor_y,
                        'interval': [p.interval_start, p.interval_end],
                        'annotation_offset': p.annotation_offset,
                        'orientation': p.orientation, 'edge': p.edge,
                        'rotation': tab_rotation(p), 'narrow': p.narrow} for p in placements],
        'warnings': warnings,
        'panel_layout': f'{rows}x{cols}',
        'inspect_only': inspect_only,
    }


def process_pcb(
    input_path: str,
    rows: int = 5, cols: int = 4,
    tab_top: int = 2, tab_bot: int = 2,
    tab_left: int = 1, tab_right: int = 1,
    tab_width: float = 3.0, narrow_width: float = 1.8,
    drill: float = 0.4, spacing: float = 0.7,
    offset: float = -0.15, prolong: float = 0.6,
    output_dir: Optional[str] = None,
    prefix: Optional[str] = None,
    inspect_only: bool = False,
    tab_plan: Optional[dict] = None,
    annotation_offset: float = 0.5,
) -> dict:
    input_path = os.path.abspath(input_path)
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f'Input file not found: {input_path}')

    basename = prefix or Path(input_path).stem
    out_dir = output_dir or os.path.join(os.path.dirname(input_path), 'panel_output')

    with open(input_path, 'r', encoding='utf-8') as f:
        pcb_text = f.read()

    segments = extract_edge_cuts_segments(pcb_text)
    circles = extract_edge_cuts_circles(pcb_text)
    placement_debug = {'edge_circles': [], 'circle_keepouts': [], 'safe_segments': []}
    if not segments:
        return {
            'input': input_path,
            'error': 'No Edge.Cuts segments found.',
            'warnings': [],
            'placements': [],
            'edge_segments': [],
            'edge_circles': [],
            'circle_keepouts': [],
            'safe_segments': [],
            'edge_opening_risk': False,
            'inspect_only': inspect_only,
            'panel_layout': f'{rows}x{cols}',
        }

    bmin, bmax = compute_bbox(segments)
    edges = classify_edges(segments, bmin, bmax)
    edge_opening_risk = detect_edge_opening_risk(edges)
    features = detect_edge_features(pcb_text, bmin, bmax)
    warnings: List[str] = []
    if edge_opening_risk:
        warnings.append('Detected edge notch/opening risk; verify tab positions visually')

    if tab_plan is not None:
        placements = placements_from_tab_plan(tab_plan, bmin, bmax, tab_width=tab_width, annotation_offset=annotation_offset)
        warnings.append('Using manual tab plan; automatic tab placement skipped')
    else:
        placements, placement_warnings, placement_debug = compute_tab_placements(
            segments, features, bmin, bmax,
            tab_top=tab_top, tab_bot=tab_bot,
            tab_left=tab_left, tab_right=tab_right,
            tab_width=tab_width, narrow_width=narrow_width,
            circles=circles, annotation_offset=annotation_offset)
        warnings.extend(placement_warnings)

    if not placements:
        warnings.append('WARNING: No valid tab positions found.')

    base = result_base(input_path, rows, cols, bmin, bmax, segments, edges, features,
                       placements, warnings, edge_opening_risk, inspect_only=inspect_only,
                       placement_debug=placement_debug)
    base['output_dir'] = out_dir
    if inspect_only:
        return base

    os.makedirs(out_dir, exist_ok=True)
    cleaned, removed = remove_old_tab_footprints(pcb_text)
    if removed:
        warnings.append(f'Removed {removed} old kikit:Tab footprint(s)')
    annotated = insert_tab_footprints(cleaned, placements)

    ann_path = os.path.join(out_dir, f'{basename}_annotation_tabs.kicad_pcb')
    with open(ann_path, 'w', encoding='utf-8') as f:
        f.write(annotated)

    def write_json(name: str, preset: dict) -> str:
        p = os.path.join(out_dir, name)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(preset, f, indent=2)
        return p

    full = generate_kikit_preset(rows, cols, drill=drill, spacing=spacing, offset=offset, prolong=prolong)
    fj = write_json(f'{basename}_panel_{rows}x{cols}.json', full)
    t21 = generate_kikit_preset(2, 1, drill=drill, spacing=spacing, offset=offset, prolong=prolong)
    t21j = write_json(f'{basename}_test_2x1.json', t21)
    t12 = generate_kikit_preset(1, 2, drill=drill, spacing=spacing, offset=offset, prolong=prolong)
    t12j = write_json(f'{basename}_test_1x2.json', t12)

    base.update({
        'annotated_pcb': ann_path,
        'preset_full': fj,
        'preset_test_2x1': t21j,
        'preset_test_1x2': t12j,
    })
    return base


# ?????? CLI ????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????


def print_report(r: dict) -> None:
    print('=' * 60)
    print('KiCad KiKit Panelization Report')
    print('=' * 60)
    print(f'Input:       {r["input"]}')
    if r.get('error'):
        print(f'ERROR: {r["error"]}')
        print('=' * 60)
        return

    print(f'Board bbox:  min={r["board_bbox"]["min"]} max={r["board_bbox"]["max"]}')
    print(f'Board size:  {r["board_size"]["width"]} x {r["board_size"]["height"]} mm')
    print(f'Panel:       {r["panel_layout"]}')
    print(f'Opening risk:{" yes" if r["edge_opening_risk"] else " no"}')
    if r.get('inspect_only'):
        print('Mode:        inspect-only (no files written)')
    print()

    if r.get('inspect_only'):
        print(f'Edge.Cuts segments ({len(r["edge_segments"])}):')
        for s in r['edge_segments']:
            mid = f' mid={s["mid"]}' if 'mid' in s else ''
            print(f'  - {s["edge"]:6s} {s["kind"]:7s} start={s["start"]} end={s["end"]}{mid} len={s["length"]}mm')
        print()

        print(f'Edge.Cuts circles ({len(r.get("edge_circles", []))}):')
        for c in r.get('edge_circles', []):
            print(f'  - center={c["center"]} radius={c["radius"]}mm')
        print()

        print(f'Circle keepout intervals ({len(r.get("circle_keepouts", []))}):')
        for k in r.get('circle_keepouts', []):
            print(f'  - {k["edge"]:6s} circle={k["circle_center"]} r={k["radius"]} interval={k["interval"]}')
        print()

        print(f'Safe segments after keepout ({len(r.get("safe_segments", []))}):')
        for s in r.get('safe_segments', []):
            print(f'  - {s["edge"]:6s} start={s["start"]} end={s["end"]} len={s["length"]}mm')
        print()

    if r.get('features_detected'):
        print('Edge features:')
        for f in r['features_detected']:
            print(f'  - {f["description"]} at ({f["center"][0]:.1f}, {f["center"][1]:.1f})')
        print()

    print(f'Tabs ({len(r["placements"])}):')
    for p in r['placements']:
        tag = ' [NARROW]' if p['narrow'] else ''
        print(f'  {p["edge"]:6s} anchor=({p["anchor_x"]:7.1f}, {p["anchor_y"]:7.1f}) '
              f'footprint=({p["x"]:7.1f}, {p["y"]:7.1f}) w={p["width"]}mm '
              f'rot={p["rotation"]} interval={p["interval"]} offset={p["annotation_offset"]}mm '
              f'{p["orientation"]}{tag}')
    print()

    if r['warnings']:
        print('Warnings:')
        for w in r['warnings']:
            prefix = '  !! ' if 'STRONG WARNING' in w else '  ! '
            print(f'{prefix}{w}')
        print()

    if r.get('inspect_only'):
        print('=' * 60)
        return

    print('Output:')
    print(f'  PCB:      {r["annotated_pcb"]}')
    print(f'  Preset:   {r["preset_full"]}')
    print(f'  Test 2x1: {r["preset_test_2x1"]}')
    print(f'  Test 1x2: {r["preset_test_1x2"]}')
    print()
    print('All presets use annotation mode.')
    print()
    print('KiKit commands:')
    print(f'  kikit panelize -p {r["preset_full"]} {r["annotated_pcb"]} panel_full.kicad_pcb')
    print(f'  kikit panelize -p {r["preset_test_2x1"]} {r["annotated_pcb"]} test_2x1.kicad_pcb')
    print(f'  kikit panelize -p {r["preset_test_1x2"]} {r["annotated_pcb"]} test_1x2.kicad_pcb')
    print('=' * 60)


def main():
    ap = argparse.ArgumentParser(description='KiCad PCB tab annotator + KiKit preset generator')
    ap.add_argument('input', help='Input .kicad_pcb file')
    ap.add_argument('--rows', type=int, default=5)
    ap.add_argument('--cols', type=int, default=4)
    ap.add_argument('--tab-top', type=int, default=2)
    ap.add_argument('--tab-bot', type=int, default=2)
    ap.add_argument('--tab-left', type=int, default=1)
    ap.add_argument('--tab-right', type=int, default=1)
    ap.add_argument('--tab-width', type=float, default=3.0)
    ap.add_argument('--narrow-width', type=float, default=1.8)
    ap.add_argument('--drill', type=float, default=0.4)
    ap.add_argument('--spacing', type=float, default=0.7)
    ap.add_argument('--offset', type=float, default=-0.15)
    ap.add_argument('--prolong', type=float, default=0.6)
    ap.add_argument('--output-dir', type=str, default=None)
    ap.add_argument('--prefix', type=str, default=None)
    ap.add_argument('--inspect-only', action='store_true', help='Only print detection results; do not write PCB or JSON files')
    ap.add_argument('--tab-plan', type=str, default=None, help='Manual tab plan JSON string or path to a JSON file')
    ap.add_argument('--annotation-offset', type=float, default=0.5, help='Move kikit:Tab footprint origin outside the board edge by this many mm')
    args = ap.parse_args()

    r = process_pcb(
        input_path=args.input, rows=args.rows, cols=args.cols,
        tab_top=args.tab_top, tab_bot=args.tab_bot,
        tab_left=args.tab_left, tab_right=args.tab_right,
        tab_width=args.tab_width, narrow_width=args.narrow_width,
        drill=args.drill, spacing=args.spacing,
        offset=args.offset, prolong=args.prolong,
        output_dir=args.output_dir, prefix=args.prefix,
        inspect_only=args.inspect_only,
        tab_plan=load_tab_plan(args.tab_plan),
        annotation_offset=args.annotation_offset)

    print_report(r)
    if r.get('error'):
        sys.exit(1)


if __name__ == '__main__':
    main()
