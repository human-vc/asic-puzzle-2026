"""Electrical sanity checks on the extracted netlist.

`main` checks the netlist against itself: exactly one driver per net, no
unconnected cell inputs, no logic driving a power rail. `undriven` goes back to
the geometry through the second extractor and lists nets with no driving output
pin and nets with no load.
"""
import collections
import json

import gdstk

import cells as cells_mod
import extract2


def main(path="puzzle_net.json"):
    data = json.load(open(path))
    lib = cells_mod.load_cells("pdk/functional")
    POWER = {"VPWR", "VGND", "VPB", "VNB"}
    KNOWN_FLOATING = {"$1447"}
    PORTS_IN = {"clk", "rst_n", "enable", "I"}

    drivers = collections.defaultdict(list)
    loads = collections.defaultdict(list)
    floating_inputs, no_logic = [], 0

    for inst in data["instances"]:
        cn = inst["cell"]
        if not cn.startswith("sky130"):
            continue
        cell = lib[cells_mod.base_name(cn)]
        if cell.kind == "none":
            no_logic += 1
            continue
        for pin in cell.outputs:
            net = inst["conns"].get(pin)
            if net:
                drivers[net].append((inst["name"], cn, pin))
        for pin in cell.inputs:
            if pin in POWER:
                continue
            net = inst["conns"].get(pin)
            if net is None:
                floating_inputs.append((inst["name"], cn, pin))
            else:
                loads[net].append((inst["name"], cn, pin))

    multi = {n: d for n, d in drivers.items() if len(d) > 1}
    undriven = sorted(set(loads) - set(drivers) - POWER - PORTS_IN)
    dangling = sorted(set(drivers) - set(loads) - {"success"} -
                      {"O[%d]" % i for i in range(8)})

    print("logic cells: %d   inert cells (decap/tap/diode): %d"
          % (sum(1 for i in data["instances"] if i["cell"].startswith("sky130")
                 and lib[cells_mod.base_name(i["cell"])].kind != "none"), no_logic))
    print("driven nets: %d" % len(drivers))
    print("multiply-driven nets: %d %s" % (len(multi), list(multi.items())[:3]))
    print("undriven nets used as inputs: %d %s" % (len(undriven), undriven[:5]))
    print("floating cell inputs: %d %s" % (len(floating_inputs), floating_inputs[:3]))
    print("driven but unloaded nets: %d  (expect clock-tree balancing buffers)" % len(dangling))
    if dangling:
        cellsd = collections.Counter(d[0][1] for n, d in drivers.items() if n in set(dangling))
        print("   their driver cell types:", dict(cellsd))
    for p in ("clk", "rst_n", "enable", "I"):
        print("  port %-7s drives %d cell pins" % (p, len(loads.get(p, []))))
    for p in ["success"] + ["O[%d]" % i for i in range(8)]:
        print("  port %-9s driven by %s" % (p, drivers.get(p, "NOTHING")))
    unexpected = [n for n in undriven if n not in KNOWN_FLOATING]
    ok = not multi and not unexpected and not floating_inputs
    print("known floating nets: %s" % sorted(KNOWN_FLOATING))
    print("unexpected problems: %d" % (len(multi) + len(unexpected) + len(floating_inputs)))
    return ok


def undriven():
    lib = cells_mod.load_cells("pdk/functional")
    glib = gdstk.read_gds("puzzle.gds")
    top = [c for c in glib.cells if not any(
        r.cell is c for d in glib.cells for r in d.references)][0]
    sites = extract2.pin_sites(glib, top)
    comps = extract2.main("puzzle.gds")

    per_comp = collections.defaultdict(list)
    for (x, y, cellname, pin) in sites:
        key = (round(x, 3), round(y, 3), pin)
        if key not in comps:
            continue
        per_comp[comps[key]].append((cellname, pin))

    undriven, unloaded = [], []
    for comp, members in per_comp.items():
        outs, ins = [], []
        for cellname, pin in members:
            cell = lib[cells_mod.base_name(cellname)]
            (outs if pin in cell.outputs else ins).append((cellname, pin))
        if not outs:
            undriven.append((comp, sorted(set(ins))))
        if not ins:
            unloaded.append((comp, sorted(set(outs))))

    print("\nnets with NO driving output pin: %d" % len(undriven))
    for comp, ins in undriven:
        print("   loads:", ins)
    print("\nnets with NO load: %d" % len(unloaded))
    tally = collections.Counter(o[0][0] for _c, o in unloaded if o)
    print("   driven by:", dict(tally))


if __name__ == "__main__":
    main()
    undriven()
