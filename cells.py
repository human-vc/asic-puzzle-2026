"""sky130_fd_sc_hd cell semantics, parsed from the PDK functional models."""
import glob
import os
import re

PRIMS = ("and", "or", "nand", "nor", "xor", "xnor", "buf", "not")
PRIM_RE = re.compile(r"^\s*(%s)\s+(\w+)\s*\(([^;]*?)\)\s*;" % "|".join(PRIMS), re.M)
PORT_RE = re.compile(r"^\s*(input|output)\s+(?:wire\s+)?(\w+)\s*;", re.M)

SEQUENTIAL = {"dfxtp", "dfrtp", "dfstp"}
NO_LOGIC = {"decap", "tapvpwrvgnd", "diode", "fill", "tap", "fillcap"}
POWER_PINS = {"VPWR", "VGND", "VPB", "VNB"}


class Cell:
    def __init__(self, base, inputs, outputs, ops, kind="comb"):
        self.base = base
        self.inputs = inputs
        self.outputs = outputs
        self.ops = ops
        self.kind = kind

    def __repr__(self):
        return "Cell(%s %s->%s %s)" % (self.base, self.inputs, self.outputs, self.kind)


def _body(text):
    i = text.find("`celldefine")
    j = text.find("`endcelldefine")
    return text[i:j]


def parse_model(path):
    base = os.path.basename(path)[:-2]
    text = _body(open(path).read())
    ports = PORT_RE.findall(text)
    inputs = [n for d, n in ports if d == "input" and n not in POWER_PINS]
    outputs = [n for d, n in ports if d == "output"]
    ops = []
    for prim, _name, args in PRIM_RE.findall(text):
        a = [x.strip() for x in args.split(",")]
        ops.append((prim, a[0], a[1:]))

    kind = "comb"
    if base in SEQUENTIAL:
        kind = base
    elif base == "mux2":
        ops.append(("mux", "mux_2to10_out_X", ["A0", "A1", "S"]))
    elif base == "conb":
        ops = [("const1", "HI", []), ("const0", "LO", [])]
    elif base in NO_LOGIC:
        inputs, outputs, ops = [], [], []
        kind = "none"
    return Cell(base, inputs, outputs, ops, kind)


def load_cells(pdk_dir):
    cells = {}
    for p in sorted(glob.glob(os.path.join(pdk_dir, "*.v"))):
        c = parse_model(p)
        cells[c.base] = c
    for b in NO_LOGIC:
        cells.setdefault(b, Cell(b, [], [], [], "none"))
    return cells


def base_name(cellname):
    """sky130_fd_sc_hd__nand2_2 -> nand2 ; handles drive-strength suffix."""
    b = cellname.split("__", 1)[1]
    return re.sub(r"_\d+$", "", b)


EVAL = {
    "and":  lambda be, xs: be.andn(xs),
    "or":   lambda be, xs: be.orn(xs),
    "nand": lambda be, xs: be.not_(be.andn(xs)),
    "nor":  lambda be, xs: be.not_(be.orn(xs)),
    "xor":  lambda be, xs: be.xorn(xs),
    "xnor": lambda be, xs: be.not_(be.xorn(xs)),
    "buf":  lambda be, xs: xs[0],
    "not":  lambda be, xs: be.not_(xs[0]),
    "mux":  lambda be, xs: be.mux(xs[0], xs[1], xs[2]),
    "const1": lambda be, xs: be.one,
    "const0": lambda be, xs: be.zero,
}


if __name__ == "__main__":
    import sys
    cells = load_cells(sys.argv[1] if len(sys.argv) > 1 else "pdk/functional")
    print("parsed %d cells" % len(cells))
    for name, c in sorted(cells.items()):
        print("  %-12s in=%-40s out=%-12s kind=%-6s ops=%d" % (
            name, ",".join(c.inputs), ",".join(c.outputs), c.kind, len(c.ops)))
