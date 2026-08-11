"""Exhaustively check the synthesizable cell models against the SkyWater
functional models: every input vector for each combinational cell, and a
directed clock/reset/set sequence for the flip-flops."""
import json
import re
import subprocess

import cells as cells_mod

SEQ_SEQUENCE = [
    # (CLK, D, CTRL)  -- CTRL is RESET_B or SET_B; dfxtp ignores it
    (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
    (0, 1, 1), (1, 1, 1), (0, 0, 1), (1, 0, 1),
    (0, 1, 1), (1, 1, 1), (0, 1, 0), (1, 1, 0),
    (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1),
]


def main():
    lib = cells_mod.load_cells("pdk/functional")
    data = json.load(open("puzzle_net.json"))
    used = sorted({i["cell"] for i in data["instances"] if i["cell"].startswith("sky130")})

    src = open("cells_behav.v").read()
    src = re.sub(r"\bmodule sky130", "module chk_sky130", src)
    open("/private/tmp/claude-501/-Users-jacobcrainic/6e326e8e-b652-4122-bdd7-c9edfdf33ec0/scratchpad/check_models.v", "w").write(src)

    body, decls, ncomb, nseq = [], [], 0, 0
    for full in used:
        base = cells_mod.base_name(full)
        cell = lib[base]
        if cell.kind == "none":
            continue
        tag = full.replace("sky130_fd_sc_hd__", "")
        ins, outs = list(cell.inputs), list(cell.outputs)
        n = max(len(ins), 1)
        decls.append("  reg [%d:0] v_%s;" % (n - 1, tag))
        for o in outs:
            decls.append("  wire r_%s_%s, c_%s_%s;" % (tag, o, tag, o))
        conn = ", ".join([".%s(r_%s_%s)" % (o, tag, o) for o in outs] +
                         [".%s(v_%s[%d])" % (p, tag, i) for i, p in enumerate(ins)])
        connc = ", ".join([".%s(c_%s_%s)" % (o, tag, o) for o in outs] +
                          [".%s(v_%s[%d])" % (p, tag, i) for i, p in enumerate(ins)])
        decls.append("  %s ref_%s (%s);" % (full, tag, conn))
        decls.append("  chk_%s chk_%s (%s);" % (full, tag, connc))

        cmp_expr = " || ".join("(r_%s_%s !== c_%s_%s)" % (tag, o, tag, o) for o in outs)
        if cell.kind in ("dfxtp", "dfrtp", "dfstp"):
            nseq += 1
            clk_i = ins.index("CLK")
            d_i = ins.index("D")
            ctrl = [p for p in ins if p in ("RESET_B", "SET_B")]
            ctrl_i = ins.index(ctrl[0]) if ctrl else None
            steps = []
            for (c, d, r) in SEQ_SEQUENCE:
                bits = ["0"] * n
                bits[clk_i] = str(c)
                bits[d_i] = str(d)
                if ctrl_i is not None:
                    bits[ctrl_i] = str(r)
                steps.append("    v_%s = %d'b%s; #2;\n    if (%s) begin errors=errors+1;"
                             " $display(\"MISMATCH %s seq\"); end"
                             % (tag, n, "".join(reversed(bits)), cmp_expr, tag))
            body.append("\n".join(steps))
        else:
            ncomb += 1
            body.append(
                "    for (k = 0; k < %d; k = k + 1) begin\n"
                "      v_%s = k[%d:0]; #2;\n"
                "      if (%s) begin errors = errors + 1;"
                " $display(\"MISMATCH %s vec %%0d\", k); end\n"
                "    end" % (1 << len(ins) if ins else 1, tag, n - 1, cmp_expr, tag))

    tb = ("`timescale 1ns/1ps\nmodule tb_cells;\n  integer k; integer errors = 0;\n"
          + "\n".join(decls)
          + "\n  initial begin\n" + "\n".join(body)
          + "\n    $display(\"combinational cells: %0d   sequential cells: %0d\", "
          + "%d, %d);\n" % (ncomb, nseq)
          + "    $display(\"TOTAL MISMATCHES: %0d\", errors);\n    $finish;\n  end\nendmodule\n")
    tbpath = "/private/tmp/claude-501/-Users-jacobcrainic/6e326e8e-b652-4122-bdd7-c9edfdf33ec0/scratchpad/tb_cells.v"
    open(tbpath, "w").write(tb)

    incs = ["-Ipdk/verilog"] + ["-I" + d for d in
                                sorted(__import__("glob").glob("pdk/verilog/cells/*/"))]
    out = "/private/tmp/claude-501/-Users-jacobcrainic/6e326e8e-b652-4122-bdd7-c9edfdf33ec0/scratchpad/cells.vvp"
    cmd = ["iverilog", "-g2012", "-DFUNCTIONAL"] + incs + [
        "-o", out, "pdk/verilog/sky130_cells.v",
        "/private/tmp/claude-501/-Users-jacobcrainic/6e326e8e-b652-4122-bdd7-c9edfdf33ec0/scratchpad/check_models.v", tbpath]
    r = subprocess.run(cmd, capture_output=True, text=True)
    errs = [l for l in r.stderr.splitlines() if "UNIT_DELAY" not in l]
    if errs:
        print("\n".join(errs[:15]))
    if r.returncode:
        raise SystemExit("compile failed")
    print(subprocess.run(["vvp", out], capture_output=True, text=True).stdout)


if __name__ == "__main__":
    main()
