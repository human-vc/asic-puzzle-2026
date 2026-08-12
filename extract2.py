"""Second, independent extraction of the interconnect connectivity.

Deliberately shares nothing with extract.py: gdstk instead of KLayout to parse
the GDS, exact polygon booleans instead of KLayout's connectivity engine, and a
hand-rolled union-find instead of LayoutToNetlist. Both extractions are then
asked the same question -- which pin sites are electrically common -- and the
two partitions are compared.
"""
import collections
import json
import math
import sys

import gdstk

LI1, MET1, MET2, MET3, MET4, MET5 = (67, 20), (68, 20), (69, 20), (70, 20), (71, 20), (72, 20)
MCON, VIA, VIA2, VIA3, VIA4 = (67, 44), (68, 44), (69, 44), (70, 44), (71, 44)
STACK = [LI1, MET1, MET2, MET3, MET4, MET5]
VIAS = [MCON, VIA, VIA2, VIA3, VIA4]
LI1_LABEL = (67, 5)


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        r = a
        while self.p.get(r, r) != r:
            r = self.p[r]
        while self.p.get(a, a) != a:
            self.p[a], a = r, self.p[a]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


class Index:
    """uniform grid over polygon bounding boxes"""

    def __init__(self, polys, cell=4.0):
        self.cell = cell
        self.buckets = collections.defaultdict(list)
        self.boxes = []
        for i, p in enumerate(polys):
            (x0, y0), (x1, y1) = p.bounding_box()
            self.boxes.append((x0, y0, x1, y1))
            for gx in range(int(x0 // cell), int(x1 // cell) + 1):
                for gy in range(int(y0 // cell), int(y1 // cell) + 1):
                    self.buckets[(gx, gy)].append(i)

    def candidates(self, box):
        x0, y0, x1, y1 = box
        out = set()
        for gx in range(int(x0 // self.cell), int(x1 // self.cell) + 1):
            for gy in range(int(y0 // self.cell), int(y1 // self.cell) + 1):
                out.update(self.buckets.get((gx, gy), ()))
        return [i for i in out
                if not (self.boxes[i][2] < x0 or self.boxes[i][0] > x1
                        or self.boxes[i][3] < y0 or self.boxes[i][1] > y1)]


def bbox_of(poly):
    (x0, y0), (x1, y1) = poly.bounding_box()
    return (x0, y0, x1, y1)


def main(gds="puzzle.gds"):
    lib = gdstk.read_gds(gds)
    top = [c for c in lib.cells if not any(
        r.cell is c for d in lib.cells for r in d.references)][0]
    print("top cell:", top.name)

    merged, index = {}, {}
    for layer in STACK:
        polys = top.get_polygons(layer=layer[0], datatype=layer[1], depth=None)
        m = gdstk.boolean(polys, [], "or", layer=layer[0], datatype=layer[1])
        merged[layer] = m
        index[layer] = Index(m)
        print("  layer %d/%d: %6d shapes -> %5d merged nets-in-layer"
              % (layer[0], layer[1], len(polys), len(m)))

    dsu = DSU()
    for layer in STACK:
        for i in range(len(merged[layer])):
            dsu.find((layer, i))

    for vlayer, lower, upper in zip(VIAS, STACK, STACK[1:]):
        vias = top.get_polygons(layer=vlayer[0], datatype=vlayer[1], depth=None)
        linked = 0
        for v in vias:
            vb = bbox_of(v)
            hits = {}
            for side in (lower, upper):
                found = None
                for ci in index[side].candidates(vb):
                    if gdstk.boolean([v], [merged[side][ci]], "and"):
                        found = ci
                        break
                hits[side] = found
            if hits[lower] is not None and hits[upper] is not None:
                dsu.union((lower, hits[lower]), (upper, hits[upper]))
                linked += 1
        print("  %d/%d: %5d vias, %5d linked both sides" % (vlayer[0], vlayer[1], len(vias), linked))

    sites = pin_sites(lib, top)
    print("pin sites found:", len(sites))

    li_index = index[LI1]
    out = {}
    unresolved = 0
    for (x, y, cellname, pin) in sites:
        eps = 0.001
        cand = li_index.candidates((x - eps, y - eps, x + eps, y + eps))
        hit = None
        for ci in cand:
            if gdstk.inside([(x, y)], merged[LI1][ci])[0]:
                hit = ci
                break
        if hit is None:
            unresolved += 1
            continue
        out[(round(x, 3), round(y, 3), pin)] = dsu.find((LI1, hit))
    print("resolved %d sites, unresolved %d" % (len(out), unresolved))

    groups = collections.defaultdict(list)
    for k, v in out.items():
        groups[v].append(k)
    print("distinct nets touching pins: %d" % len(groups))

    json.dump({"%.3f,%.3f,%s" % k: str(v) for k, v in out.items()},
              open("extract2_sites.json", "w"))
    return out


def pin_sites(lib, top):
    """global (x, y, cell, pin) for every li1 pin label of every placed cell"""
    masters = {c.name: c for c in lib.cells}
    sites = []
    for ref in top.references:
        name = ref.cell.name
        if not name.startswith("sky130"):
            continue
        m = masters[name]
        for lab in m.labels:
            if (lab.layer, lab.texttype) != LI1_LABEL:
                continue
            for origin in ref_origins(ref):
                x, y = transform_point(lab.origin, origin, ref.rotation,
                                       ref.x_reflection, ref.magnification)
                sites.append((x, y, name, lab.text))
    return sites


def ref_origins(ref):
    rep = ref.repetition
    if rep is None or rep.size in (0, None):
        return [ref.origin]
    return [(ref.origin[0] + dx, ref.origin[1] + dy) for dx, dy in rep.offsets]


def transform_point(p, origin, rotation, x_reflection, magnification):
    x, y = p
    mag = magnification or 1.0
    x, y = x * mag, y * mag
    if x_reflection:
        y = -y
    rot = rotation or 0.0
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        x, y = x * c - y * s, x * s + y * c
    return x + origin[0], y + origin[1]


if __name__ == "__main__":
    main(*sys.argv[1:])
