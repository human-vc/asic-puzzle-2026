"""Using the independent extraction, find every electrical net that has no
driving cell output on it. Cross-checks the netlist's undriven/dangling nets."""
import collections

import gdstk

import cells as cells_mod
import extract2


def main():
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
