"""Assign every gate to a recovered functional block, and report where each
block physically sits on the die."""
import json

from analyze import cone
from sim import Design

FLOP_BLOCKS = {
    "cell counter (mod 11)": [38, 45, 73, 84],
    "row counter": [9, 14, 58, 64],
    "run/done flag": [7, 61],
    "input delay line": [13, 20, 71, 46, 29, 52, 15, 50, 8, 65, 74, 62],
    "adjacency check": [28],
    "column accumulators": [11, 24, 18, 30, 27, 80, 31, 72, 33, 76, 36, 42,
                            37, 59, 39, 67, 40, 57, 43, 78, 79, 85],
    "row accumulator": [68, 88, 81],
    "region accumulators": [6, 55, 10, 25, 17, 47, 19, 82, 23, 87, 26, 70,
                            32, 63, 41, 66, 48, 53, 49, 75, 56, 69],
    "success latch": [35, 60],
    # Feeds O only. This is the block the puzzle's own hint image boxes off.
    "output generator": [0, 1, 2, 3, 4, 5, 21, 22, 44, 77, 90, 91],
    # Feeds both the verdict and the output byte, and sits outside that box.
    "verdict/output shared": [12, 16, 83, 86, 89, 34, 51, 54],
}
ORDER = list(FLOP_BLOCKS)


def assign(d):
    qnodes = {f[1]: i for i, f in enumerate(d.flops)}
    stop = set(qnodes) | {"$VPWR", "$VGND", "$VPB", "$VNB", "$FLOAT",
                          "net:clk", "net:rst_n", "net:enable", "net:I"}
    block_of_flop = {}
    for b, idxs in FLOP_BLOCKS.items():
        for i in idxs:
            block_of_flop[i] = b

    node_blocks = {}
    for i, f in enumerate(d.flops):
        b = block_of_flop.get(i)
        if b is None:
            continue
        seen, _ = cone(d, f[2], stop)
        for n in seen:
            if n in d.nodes:
                node_blocks.setdefault(n, set()).add(b)
    succ_cone, _ = cone(d, "net:success", stop)
    for n in succ_cone:
        if n in d.nodes:
            node_blocks.setdefault(n, set()).add("success latch")
    # Logic in the O cone that also feeds success belongs to the checker, not to
    # the output generator -- which is exactly where the puzzle's hint draws it.
    for k in range(8):
        seen, _ = cone(d, "net:O[%d]" % k, stop)
        for n in seen:
            if n in d.nodes and n not in succ_cone:
                node_blocks.setdefault(n, set()).add("output generator")
    return block_of_flop, node_blocks


def instance_blocks(d, block_of_flop, node_blocks):
    """map netlist instance name -> block label"""
    out = {}
    for i, f in enumerate(d.flops):
        b = block_of_flop.get(i)
        if b:
            out[f[5]] = b
    # a gate's own internal nodes are named "<instance>/<signal>"
    driver = {}
    for n, blocks in node_blocks.items():
        if "/" in n:
            driver.setdefault(n.split("/")[0], set()).update(blocks)
    for inst in d.data["instances"]:
        if inst["name"] in out:
            continue
        blocks = set()
        for pin, net in inst["conns"].items():
            key = "net:" + net if net else None
            if key and key in node_blocks:
                blocks |= node_blocks[key]
        blocks |= driver.get(inst["name"], set())
        if blocks:
            out[inst["name"]] = sorted(blocks)[0] if len(blocks) == 1 else "shared"
    return out


def main():
    d = Design("puzzle_net.json")
    bf, nb = assign(d)
    inst_block = instance_blocks(d, bf, nb)
    place = json.load(open("placement.json"))

    rows = []
    for name, info in place["placement"].items():
        b = inst_block.get(name, "unassigned")
        rows.append(dict(info, block=b, name=name))
    json.dump({"die": place["die"], "cells": rows}, open("blocks.json", "w"))

    import collections
    stat = collections.defaultdict(lambda: [0, 1e9, -1e9, 1e9, -1e9])
    for r in rows:
        s = stat[r["block"]]
        s[0] += 1
        s[1] = min(s[1], r["x"])
        s[2] = max(s[2], r["x"] + r["w"])
        s[3] = min(s[3], r["y"])
        s[4] = max(s[4], r["y"] + r["h"])
    print("%-24s %5s  %-18s %-18s" % ("block", "cells", "x range (um)", "y range (um)"))
    for b in ORDER + ["shared", "unassigned"]:
        if b not in stat:
            continue
        n, x0, x1, y0, y1 = stat[b]
        print("%-24s %5d  %6.1f - %6.1f   %6.1f - %6.1f" % (b, n, x0, x1, y0, y1))


if __name__ == "__main__":
    main()
