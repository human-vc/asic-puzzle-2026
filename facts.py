"""Re-derive the numbers worth quoting, from the artifacts themselves.

Numbers this script cannot derive on its own are printed under a separate
heading naming the script that produced them, so the distinction is visible.
"""
import collections
import json
import re
import subprocess

import klayout.db as db

import cells as cells_mod
from recovered import region_letters


def main():
    out = []
    A = out.append

    ly = db.Layout()
    ly.read("puzzle.gds")
    top = ly.top_cell()
    bb = top.bbox()
    A(("die size", "%.0f x %.1f um" % (bb.width() * ly.dbu, bb.height() * ly.dbu)))
    A(("die y extent", "%.2f to %.0f um (extends below the cell rows)"
       % (bb.bottom * ly.dbu, bb.top * ly.dbu)))

    data = json.load(open("puzzle_net.json"))
    lib = cells_mod.load_cells("pdk/functional")
    logic = inert = 0
    kinds = collections.Counter()
    for i in data["instances"]:
        cn = i["cell"]
        if not cn.startswith("sky130"):
            continue
        cell = lib[cells_mod.base_name(cn)]
        if cell.kind == "none":
            inert += 1
        else:
            logic += 1
            if cell.kind in ("dfrtp", "dfxtp", "dfstp"):
                kinds[cell.kind] += 1
    A(("logic cells on the die", logic))
    A(("inert cells (tap/decap/diode)", inert))
    A(("flip-flops", "%d  (%s)" % (sum(kinds.values()),
                                   ", ".join("%d %s" % (v, k) for k, v in kinds.most_common()))))
    A(("distinct cell types", len({i["cell"] for i in data["instances"]
                                   if i["cell"].startswith("sky130")})))

    bits = open("solution_bits.txt").read().strip()
    A(("input bits", len(bits)))
    A(("stars in the solution", bits.count("1")))

    A(("regions", len(region_letters())))

    hc = open("hardcaml/starbattle.ml").read()
    A(("Hardcaml source lines", hc.count("\n") + 1))
    A(("Verilog reconstruction lines", open("puzzle_rtl.v").read().count("\n") + 1))

    def cellcount(p):
        c = collections.Counter()
        for m in re.finditer(r"^\s+(sky130_fd_sc_hd__\w+)\s+", open(p).read(), re.M):
            c[m.group(1)] += 1
        return c

    ar = {c.name: c.bbox().width() * ly.dbu * c.bbox().height() * ly.dbu
          for c in ly.each_cell() if c.name.startswith("sky130")}
    die_area = sum(ar.get(i["cell"], 0) for i in data["instances"]
                   if i["cell"].startswith("sky130")
                   and lib[cells_mod.base_name(i["cell"])].kind != "none")
    v = cellcount("puzzle_resynth.v")
    A(("die cell area", "%.0f um2" % die_area))
    A(("re-synthesized Verilog", "%d cells, %.0f um2" % (sum(v.values()),
                                                         sum(ar.get(k, 0) * n for k, n in v.items()))))
    A(("TT 1x1 tile", "160 x 100 um = 16,000 um2, ~1000 gates quoted"))
    A(("utilisation of one tile", "%.0f%%" % (100 * sum(ar.get(k, 0) * n for k, n in v.items()) / 16000)))

    egg = subprocess.run([".venv/bin/python", "easter_eggs.py"],
                         capture_output=True, text=True).stdout
    for line in egg.strip().splitlines():
        if line.strip().startswith("'"):
            A(("easter egg", line.strip()))

    quoted = [
        ("differential grids tested", "37,382 with 0 disagreements (diff_test.py)"),
        ("pin sites both extractors agree on", "5,094 / 741 nets (compare_extractions.py)"),
        ("formal claim", "success <=> Star Battle over all 2^121 inputs, UNSAT both ways (proof.py)"),
        ("RTL vs silicon", "145 cycles under the protocol, 122 with every input free (equiv.ys)"),
        ("power-up states checked", "16 of 16 give the same message"),
    ]

    w = max(len(str(k)) for k, _ in out + quoted)
    for k, val in out:
        print("%-*s  %s" % (w, k, val))
    print()
    for k, val in quoted:
        print("%-*s  %s" % (w, k, val))


if __name__ == "__main__":
    main()
