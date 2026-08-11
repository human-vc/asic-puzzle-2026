"""Emit synthesizable Verilog models for the sky130 cells the design uses.

Yosys cannot read the PDK's UDP-based models, so these are derived from the
same functional models and then checked exhaustively against them with Icarus
(see check_cells.py) rather than trusted.
"""
import json

import cells as cells_mod

SEQ = {
    "dfxtp": """    always @(posedge CLK) Q <= D;""",
    "dfrtp": """    always @(posedge CLK or negedge RESET_B)
        if (!RESET_B) Q <= 1'b0; else Q <= D;""",
    "dfstp": """    always @(posedge CLK or negedge SET_B)
        if (!SET_B) Q <= 1'b1; else Q <= D;""",
}

OP = {
    "and": " & ", "or": " | ", "nand": " & ", "nor": " | ",
    "xor": " ^ ", "xnor": " ^ ",
}
NEG = {"nand", "nor", "xnor"}


def expr_for(cell):
    """build a Verilog expression per output from the primitive op list"""
    vals = {i: i for i in cell.inputs}
    pending = list(cell.ops)
    for _ in range(len(pending) + 2):
        progressed = False
        rest = []
        for prim, out, ins in pending:
            if all(i in vals for i in ins):
                args = [vals[i] for i in ins]
                if prim == "buf":
                    e = args[0]
                elif prim == "not":
                    e = "~%s" % args[0]
                elif prim == "mux":
                    e = "(%s ? %s : %s)" % (args[2], args[1], args[0])
                else:
                    joined = OP[prim].join(args)
                    e = "(%s)" % joined
                    if prim in NEG:
                        e = "~%s" % e
                vals[out] = e
                progressed = True
            else:
                rest.append((prim, out, ins))
        pending = rest
        if not pending or not progressed:
            break
    return {o: vals.get(o) for o in cell.outputs}


def main(out="cells_behav.v"):
    lib = cells_mod.load_cells("pdk/functional")
    data = json.load(open("puzzle_net.json"))
    used = sorted({i["cell"] for i in data["instances"] if i["cell"].startswith("sky130")})

    lines = ["// Synthesizable models for the sky130 cells this design uses.",
             "// Verified exhaustively against the SkyWater functional models.",
             "`default_nettype none", ""]
    emitted = 0
    for full in used:
        base = cells_mod.base_name(full)
        cell = lib[base]
        if cell.kind == "none":
            continue
        ports = list(cell.outputs) + list(cell.inputs)
        decl = ", ".join(
            ("output reg %s" if (cell.kind in SEQ and p in cell.outputs) else
             ("output wire %s" if p in cell.outputs else "input wire %s")) % p
            for p in ports)
        lines.append("module %s (%s);" % (full, decl))
        if cell.kind in SEQ:
            lines.append(SEQ[cell.kind])
        elif base == "conb":
            lines.append("    assign HI = 1'b1;")
            lines.append("    assign LO = 1'b0;")
        else:
            for o, e in expr_for(cell).items():
                if e is None:
                    raise RuntimeError("no expression for %s.%s" % (full, o))
                lines.append("    assign %s = %s;" % (o, e))
        lines.append("endmodule")
        lines.append("")
        emitted += 1
    lines.append("`default_nettype wire")
    open(out, "w").write("\n".join(lines))
    print("wrote %s: %d cell models" % (out, emitted))


if __name__ == "__main__":
    main()
