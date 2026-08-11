"""Compare the re-synthesized reconstruction against the cells on the real die."""
import collections
import json
import re

import klayout.db as db

import cells as cells_mod


def die_cells():
    data = json.load(open("puzzle_net.json"))
    lib = cells_mod.load_cells("pdk/functional")
    logic, inert = collections.Counter(), collections.Counter()
    for i in data["instances"]:
        cn = i["cell"]
        if not cn.startswith("sky130"):
            continue
        (inert if lib[cells_mod.base_name(cn)].kind == "none" else logic)[cn] += 1
    return logic, inert


def resynth_cells(path="puzzle_resynth.v"):
    c = collections.Counter()
    for m in re.finditer(r"^\s+(sky130_fd_sc_hd__\w+)\s+", open(path).read(), re.M):
        c[m.group(1)] += 1
    return c


def areas():
    ly = db.Layout()
    ly.read("puzzle.gds")
    return {c.name: c.bbox().width() * ly.dbu * c.bbox().height() * ly.dbu
            for c in ly.each_cell() if c.name.startswith("sky130")}


def main():
    logic, inert = die_cells()
    re_c = resynth_cells()
    ar = areas()

    def flops(counter):
        return sum(n for c, n in counter.items()
                   if cells_mod.base_name(c) in ("dfrtp", "dfxtp", "dfstp"))

    def area_of(counter):
        return sum(ar.get(c, 0) * n for c, n in counter.items())

    print("%-28s %10s %12s" % ("", "on the die", "re-synthesized"))
    print("%-28s %10d %12d" % ("logic cells", sum(logic.values()), sum(re_c.values())))
    print("%-28s %10d %12d" % ("  of which flip-flops", flops(logic), flops(re_c)))
    print("%-28s %10.0f %12.0f" % ("cell area (um2)", area_of(logic), area_of(re_c)))
    print("%-28s %10d %12s" % ("distinct cell types", len(logic), len(re_c)))
    print("%-28s %10d %12s" % ("inert cells (tap/decap/diode)", sum(inert.values()), "n/a"))

    print("\nlargest differences by cell type:")
    keys = set(logic) | set(re_c)
    diffs = sorted(keys, key=lambda k: (-abs(logic.get(k, 0) - re_c.get(k, 0)), k))
    print("  %-34s %6s %6s" % ("cell", "die", "resyn"))
    for k in diffs[:12]:
        print("  %-34s %6d %6d" % (k, logic.get(k, 0), re_c.get(k, 0)))


if __name__ == "__main__":
    main()
