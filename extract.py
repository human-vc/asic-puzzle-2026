"""GDS -> gate-level netlist for sky130_fd_sc_hd designs.

Uses KLayout's hierarchical netlist extractor over the interconnect stack only
(no device extraction): standard cells become subcircuits whose pins are named
from the li1/met label layers that survive in the GDS.
"""
import json
import sys

import klayout.db as db

STACK = [
    ("li1",  (67, 20), (67, 5)),
    ("met1", (68, 20), (68, 5)),
    ("met2", (69, 20), (69, 5)),
    ("met3", (70, 20), (70, 5)),
    ("met4", (71, 20), (71, 5)),
    ("met5", (72, 20), (72, 5)),
]
VIAS = [
    ("mcon", (67, 44)),
    ("via",  (68, 44)),
    ("via2", (69, 44)),
    ("via3", (70, 44)),
    ("via4", (71, 44)),
]
EXTRA_LABELS = [("nwell", (64, 20), (64, 5))]


def extract(gds_path):
    ly = db.Layout()
    ly.read(gds_path)
    top = ly.top_cell()

    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, top, []))
    l2n.threads = 4

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
    return l2n, l2n.netlist()


def dump(netlist, out_json):
    circuits = [c for c in netlist.each_circuit()]
    referenced = set()
    for c in circuits:
        for sc in c.each_subcircuit():
            referenced.add(sc.circuit_ref().name)
    tops = [c for c in circuits if c.name not in referenced]
    top = tops[0] if len(tops) == 1 else max(tops, key=lambda c: len(list(c.each_subcircuit())))

    nets = {}
    for n in top.each_net():
        nets[n.expanded_name()] = {
            "name": n.name or "",
            "pins": [],
        }

    insts = []
    for sc in top.each_subcircuit():
        ref = sc.circuit_ref()
        conns = {}
        for pin in ref.each_pin():
            net = sc.net_for_pin(pin.id())
            conns[pin.name() or ("p%d" % pin.id())] = net.expanded_name() if net else None
        insts.append({
            "name": sc.expanded_name(),
            "cell": ref.name,
            "conns": conns,
        })

    data = {"top": top.name, "instances": insts,
            "nets": sorted(nets.keys()),
            "ports": [p.name() for p in top.each_pin() if p.name()]}
    with open(out_json, "w") as f:
        json.dump(data, f, indent=1)
    return data


if __name__ == "__main__":
    gds, out = sys.argv[1], sys.argv[2]
    l2n, netlist = extract(gds)
    data = dump(netlist, out)
    print("top:", data["top"])
    print("instances:", len(data["instances"]))
    print("nets:", len(data["nets"]))
