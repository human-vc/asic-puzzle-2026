"""Compare the two independent connectivity extractions.

extract2.py (gdstk + exact polygon booleans + union-find) and extract.py
(KLayout LayoutToNetlist) are asked which pin sites are electrically common.
Equality of the two partitions is the check.
"""
import collections

import klayout.db as db

import extract2
from extract import STACK, VIAS


def build_l2n_flat(gds="puzzle.gds"):
    """Same KLayout extraction, but on a flattened layout so every net is a
    top-level net with a unique identity (hierarchical probes return the cell
    master's internal net, which cannot distinguish instances)."""
    ly = db.Layout()
    ly.read(gds)
    top = ly.top_cell()
    top.flatten(-1, True)

    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
    conductors = {}
    for name, (l, d), _lbl in STACK:
        conductors[name] = l2n.make_polygon_layer(ly.layer(l, d), name)
    vias = {n: l2n.make_polygon_layer(ly.layer(*ld), n) for n, ld in VIAS}
    for name in conductors:
        l2n.connect(conductors[name])
    order = [n for n, _, _ in STACK]
    for (vname, _), lower, upper in zip(VIAS, order, order[1:]):
        l2n.connect(vias[vname])
        l2n.connect(conductors[lower], vias[vname])
        l2n.connect(vias[vname], conductors[upper])
    l2n.extract_netlist()
    return ly, top, l2n, conductors


def main():
    mine = extract2.main("puzzle.gds")
    ly, top, l2n, conductors = build_l2n_flat("puzzle.gds")

    theirs, missing = {}, 0
    for (x, y, pin), comp in mine.items():
        net = l2n.probe_net(conductors["li1"], db.DPoint(x, y))
        if net is None:
            missing += 1
            continue
        theirs[(x, y, pin)] = net.expanded_name()

    print("\nsites probed in both extractions: %d (klayout found no net at %d)"
          % (len(theirs), missing))

    a2b, b2a = {}, {}
    conflicts = []
    for k, a in mine.items():
        if k not in theirs:
            continue
        b = theirs[k]
        if a2b.setdefault(a, b) != b or b2a.setdefault(b, a) != a:
            conflicts.append((k, a, b, a2b.get(a), b2a.get(b)))

    print("distinct nets: mine=%d  klayout=%d" % (len(a2b), len(b2a)))
    if conflicts:
        print("PARTITIONS DISAGREE at %d sites; first few:" % len(conflicts))
        for c in conflicts[:5]:
            print("   ", c)
    else:
        print("PARTITIONS ARE IDENTICAL -- the two extractions agree on every site.")

    sizes_a = collections.Counter()
    for k, a in mine.items():
        if k in theirs:
            sizes_a[a] += 1
    print("largest nets by pin count:", sizes_a.most_common(5))
    return not conflicts


if __name__ == "__main__":
    ok = main()
    raise SystemExit(0 if ok else 1)
