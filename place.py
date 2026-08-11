"""Link extracted netlist instances to their physical placement.

For each standard-cell instance in the GDS, probe the net at its output pin and
match that to the netlist instance driving the same net. Produces a placement
map so the layout can be coloured by recovered function.
"""
import json

import klayout.db as db

import cells as cells_mod
from extract import STACK, VIAS


def build_l2n(gds="puzzle.gds"):
    ly = db.Layout()
    ly.read(gds)
    top = ly.top_cell()
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
    conductors, labels = {}, {}
    for name, (l, d), (ll, ld) in STACK:
        conductors[name] = l2n.make_polygon_layer(ly.layer(l, d), name)
        labels[name] = l2n.make_text_layer(ly.layer(ll, ld), name + "_lbl")
    vias = {n: l2n.make_polygon_layer(ly.layer(*ld), n) for n, ld in VIAS}
    for name in conductors:
        l2n.connect(conductors[name])
        l2n.connect(conductors[name], labels[name])
    order = [n for n, _, _ in STACK]
    for (vname, _), lower, upper in zip(VIAS, order, order[1:]):
        l2n.connect(vias[vname])
        l2n.connect(conductors[lower], vias[vname])
        l2n.connect(vias[vname], conductors[upper])
    l2n.extract_netlist()
    return ly, top, l2n, conductors


def pin_positions(ly):
    """cell master -> {pin label: (x, y) in cell coords}, from li1 labels"""
    li1_lbl = ly.layer(67, 5)
    out = {}
    for c in ly.each_cell():
        if not c.name.startswith("sky130"):
            continue
        d = {}
        for sh in c.shapes(li1_lbl).each():
            if sh.is_text():
                t = sh.text
                d.setdefault(t.string, (t.x, t.y))
        out[c.name] = d
    return out


def main():
    ly, top, l2n, conductors = build_l2n()
    lib = cells_mod.load_cells("pdk/functional")
    pins = pin_positions(ly)
    data = json.load(open("puzzle_net.json"))

    driver_of = {}
    for inst in data["instances"]:
        cn = inst["cell"]
        if not cn.startswith("sky130"):
            continue
        cell = lib[cells_mod.base_name(cn)]
        if cell.kind == "none":
            continue
        for o in cell.outputs:
            net = inst["conns"].get(o)
            if net:
                driver_of.setdefault((net, o), inst["name"])

    placed, missed = {}, 0
    for inst in top.each_inst():
        cn = inst.cell.name
        if not cn.startswith("sky130"):
            continue
        cell = lib[cells_mod.base_name(cn)]
        if cell.kind == "none":
            continue
        outs = [o for o in cell.outputs if o in pins.get(cn, {})]
        if not outs:
            missed += 1
            continue
        o = outs[0]
        px, py = pins[cn][o]
        p = inst.trans * db.Point(px, py)
        net = l2n.probe_net(conductors["li1"], db.DPoint(p.x * ly.dbu, p.y * ly.dbu))
        if net is None:
            missed += 1
            continue
        key = (net.expanded_name(), o)
        name = driver_of.get(key)
        if name is None:
            missed += 1
            continue
        bb = inst.bbox()
        placed[name] = {
            "cell": cn,
            "x": bb.left * ly.dbu, "y": bb.bottom * ly.dbu,
            "w": bb.width() * ly.dbu, "h": bb.height() * ly.dbu,
        }

    bb = top.bbox()
    out = {
        "die": {"x": bb.left * ly.dbu, "y": bb.bottom * ly.dbu,
                "w": bb.width() * ly.dbu, "h": bb.height() * ly.dbu},
        "placement": placed,
    }
    json.dump(out, open("placement.json", "w"), indent=1)
    print("placed %d instances, unmatched %d" % (len(placed), missed))


if __name__ == "__main__":
    main()
