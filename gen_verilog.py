"""Emit a Verilog netlist from the extracted GDS netlist, for simulation with
the official SkyWater cell models under an independent simulator."""
import json
import re
import sys

import cells as cells_mod

POWER = {"VPWR", "VGND", "VPB", "VNB"}
PORTS_IN = ["clk", "rst_n", "enable", "I"]


def vname(net):
    if net in ("VPWR",):
        return "1'b1"
    if net in ("VGND",):
        return "1'b0"
    if net in PORTS_IN or net == "success":
        return net
    m = re.match(r"^O\[(\d)\]$", net)
    if m:
        return "O[%s]" % m.group(1)
    return "n" + re.sub(r"[^0-9A-Za-z_]", "_", net)


def main(netjson="puzzle_net.json", out="puzzle_extracted.v"):
    data = json.load(open(netjson))
    lib = cells_mod.load_cells("pdk/functional")

    used_nets, body = set(), []
    for inst in data["instances"]:
        cn = inst["cell"]
        if not cn.startswith("sky130"):
            continue
        cell = lib[cells_mod.base_name(cn)]
        if cell.kind == "none":
            continue
        conns = []
        for pin in list(cell.outputs) + list(cell.inputs):
            if pin in POWER:
                continue
            net = inst["conns"].get(pin)
            if net is None:
                conns.append(".%s()" % pin)
                continue
            used_nets.add(net)
            conns.append(".%s(%s)" % (pin, vname(net)))
        body.append("  %s %s (%s);" % (cn, "u_" + re.sub(r"\W", "_", inst["name"]),
                                       ", ".join(conns)))

    wires = sorted(n for n in used_nets
                   if n not in POWER and n not in PORTS_IN and n != "success"
                   and not re.match(r"^O\[\d\]$", n))

    with open(out, "w") as f:
        f.write("// Generated from puzzle.gds by extract.py + gen_verilog.py\n")
        f.write("`default_nettype none\n\nmodule puzzle (\n")
        f.write("  input wire clk,\n  input wire rst_n,\n  input wire enable,\n")
        f.write("  input wire I,\n  output wire [7:0] O,\n  output wire success\n);\n\n")
        for w in wires:
            f.write("  wire %s;\n" % vname(w))
        f.write("\n")
        f.write("\n".join(body))
        f.write("\n\nendmodule\n`default_nettype wire\n")
    print("wrote %s: %d cells, %d wires" % (out, len(body), len(wires)))

    with open("pdk/verilog/sky130_cells.v", "w") as f:
        f.write("// includes every sized cell model used by the design\n")
        for cn in sorted({i["cell"] for i in data["instances"] if i["cell"].startswith("sky130")}):
            base = cells_mod.base_name(cn)
            if lib[base].kind == "none":
                continue
            f.write('`include "cells/%s/%s.v"\n' % (base, cn))
    print("wrote pdk/verilog/sky130_cells.v")


if __name__ == "__main__":
    main(*sys.argv[1:])
