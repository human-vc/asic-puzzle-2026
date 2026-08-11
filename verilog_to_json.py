"""Parse a yosys-written sky130 gate netlist into the same JSON shape that
extract.py produces, so the reconstructed RTL can be pushed through the very
same simulator, SAT unroller and equivalence proof as the silicon."""
import json
import re
import sys

INST = re.compile(
    r"(sky130_fd_sc_hd__\w+)\s+(\S+)\s*\(\s*((?:\.\w+\([^)]*\)\s*,?\s*)+)\)\s*;", re.M)
CONN = re.compile(r"\.(\w+)\(([^)]*)\)")


def netname(tok):
    tok = tok.strip()
    if tok in ("1'b1", "1'h1"):
        return "VPWR"
    if tok in ("1'b0", "1'h0"):
        return "VGND"
    if not tok:
        return None
    return tok.replace("\\", "").replace(" ", "")


def main(src="puzzle_resynth.v", out="resynth_net.json"):
    text = open(src).read()
    insts, n = [], 0
    for m in INST.finditer(text):
        cell, name, body = m.group(1), m.group(2), m.group(3)
        conns = {}
        for pin, net in CONN.findall(body):
            nn = netname(net)
            if nn:
                conns[pin] = nn
        conns.setdefault("VPWR", "VPWR")
        conns.setdefault("VGND", "VGND")
        insts.append({"name": name.replace("\\", ""), "cell": cell, "conns": conns})
        n += 1
    # yosys emits constant / pass-through outputs as assigns; model each as a
    # buffer so the netlist stays uniform for the simulator.
    for m in re.finditer(r"^\s*assign\s+([^=]+?)\s*=\s*([^;]+?)\s*;", text, re.M):
        lhs, rhs = netname(m.group(1)), netname(m.group(2))
        if not lhs or not rhs:
            continue
        n += 1
        insts.append({"name": "assign%d" % n, "cell": "sky130_fd_sc_hd__buf_2",
                      "conns": {"A": rhs, "X": lhs, "VPWR": "VPWR", "VGND": "VGND"}})

    nets = sorted({v for i in insts for v in i["conns"].values()})
    json.dump({"top": "puzzle_rtl", "instances": insts, "nets": nets, "ports": []},
              open(out, "w"))
    print("parsed %d cells, %d nets -> %s" % (n, len(nets), out))


if __name__ == "__main__":
    main(*sys.argv[1:])
