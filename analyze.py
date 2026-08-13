"""Structural analysis of the extracted netlist: flop dependency graph, cones."""
import collections
import sys

from sim import Design


def build(d):
    src = {}
    for n, (prim, ins) in d.nodes.items():
        src[n] = ins
    qnodes = {f[1]: f for f in d.flops}
    return src, qnodes


def cone(d, start, stop_at):
    """backward cone from a node, stopping at flop Q nodes / primary inputs"""
    seen, front, leaves = set(), [start], set()
    while front:
        n = front.pop()
        if n in seen:
            continue
        seen.add(n)
        if n in stop_at or n not in d.nodes:
            leaves.add(n)
            continue
        front.extend(d.nodes[n][1])
    return seen, leaves


def main(path):
    d = Design(path)
    qnodes = {f[1]: f for f in d.flops}
    stop = set(qnodes) | {"$VPWR", "$VGND", "$VPB", "$VNB", "$FLOAT",
                          "net:clk", "net:rst_n", "net:enable", "net:I"}

    fname = {}
    for i, f in enumerate(d.flops):
        fname[f[1]] = "F%02d" % i
    print("flops")
    for f in d.flops:
        print("  %-5s %-9s q=%-12s inst=%s" % (fname[f[1]], f[0], f[1], f[5]))

    def label(n):
        if n in fname:
            return fname[n]
        if n.startswith("net:"):
            return n[4:]
        return n

    print("\nnext-state dependencies (D cone leaves)")
    deps = {}
    for f in d.flops:
        _, leaves = cone(d, f[2], stop)
        deps[f[1]] = leaves
        print("  %-5s <- %s" % (fname[f[1]], " ".join(sorted(label(l) for l in leaves))))

    print("\noutput cones")
    for name in ["net:success"] + ["net:O[%d]" % i for i in range(8)]:
        _, leaves = cone(d, name, stop)
        print("  %-12s <- %s" % (label(name), " ".join(sorted(label(l) for l in leaves))))

    print("\nfan-out: which flops consume each flop")
    consumers = collections.defaultdict(set)
    for f in d.flops:
        for l in deps[f[1]]:
            consumers[l].add(fname[f[1]])
    for name in ["net:success"] + ["net:O[%d]" % i for i in range(8)]:
        _, leaves = cone(d, name, stop)
        for l in leaves:
            consumers[l].add(label(name))
    for q in sorted(consumers, key=lambda x: label(x)):
        print("  %-8s -> %s" % (label(q), " ".join(sorted(consumers[q]))))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "puzzle_net.json")
