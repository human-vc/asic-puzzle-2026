"""Reproduce the reconstruction bug that simulation could not catch, and show
that the puzzle's own solution grid is the only thing the miter can return.

The first reconstruction asserted the verdict on the same edge that consumed the
last bit. The silicon registers it one cycle later.

Two experiments, both against that rebuilt RTL:

  depths  -- pin the input to the solution grid and bisect the unroll depth.
             Clean through 123, counterexample at 124.

  forced  -- pin bit i off-solution and leave the other 120 free, for each of
             the 121 positions. Every one is UNSAT, so no counterexample
             differs from the solution anywhere; with the control (whole grid
             pinned) failing, the solution grid is the unique counterexample.
             Slow: 121 miters, a few minutes at the default job count.

Both pin the operating protocol. That matters: `equiv.ys` constrains `rst_n`
only at timesteps 1 and 2, leaving it free afterwards, so a solver may hold the
design in reset and present the same grid later in the trace. Pinning `rst_n`
high from timestep 3 fixes cell k at timestep 3+k.
"""
import os
import re
import subprocess
import sys
import tempfile

ANCHOR = "                ok_q  <= ok;"
ARMED = ("        end else if (armed) begin\n"
         "            armed     <= 1'b0;\n"
         "            success_q <= ok_q;\n"
         "        end")
DEPTH = 145
JOBS = int(os.environ.get("JOBS", "3"))


def immediate_version(src):
    """assert the verdict on the finishing edge, with no registered stage"""
    if ANCHOR not in src or ARMED not in src:
        raise SystemExit("puzzle_rtl.v has moved; the anchors no longer match")
    src = src.replace(ANCHOR, ANCHOR + "\n                success_q <= ok;")
    return src.replace(ARMED, ARMED.replace("\n            success_q <= ok_q;", ""))


def script(rtl, depth, isets):
    base = open("equiv.ys").read()
    base = base.replace("read_verilog -sv puzzle_rtl.v", "read_verilog -sv %s" % rtl)
    base = re.sub(r"sat -seq \d+", "sat -seq %d" % depth, base)
    rst = " ".join("-set-at %d in_rst_n 1" % t for t in range(3, depth + 1))
    return base.replace("-verify", "%s %s -verify" % (rst, isets))


def pin_all(bits, depth):
    return " ".join("-set-at %d in_I %s" % (3 + k, b)
                    for k, b in enumerate(bits) if 3 + k <= depth)


def run(path):
    out = subprocess.run(["yosys", path], capture_output=True, text=True).stdout
    if "no model found" in out:
        return "equivalent"
    if "model found: FAIL" in out:
        return "COUNTEREXAMPLE"
    raise SystemExit("yosys did not reach a verdict for %s" % path)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "depths"
    tmp = tempfile.mkdtemp(prefix="cycle124-")
    rtl = os.path.join(tmp, "puzzle_rtl_immediate.v")
    open(rtl, "w").write(immediate_version(open("puzzle_rtl.v").read()))
    bits = open("solution_bits.txt").read().strip()
    print("input pinned to the solution grid (%d bits, %d stars), reset released"
          " at timestep 3" % (len(bits), bits.count("1")))

    if mode == "depths":
        print()
        for depth in (123, 124):
            p = os.path.join(tmp, "d%d.ys" % depth)
            open(p, "w").write(script(rtl, depth, pin_all(bits, depth)))
            print("  unroll depth %3d: %s" % (depth, run(p)))
        print()
        print("the silicon registers the verdict one cycle after the last bit;")
        print("the first reconstruction asserted it on the same edge")
        return

    if mode != "forced":
        raise SystemExit("usage: cycle124.py [depths|forced]")

    ctl = os.path.join(tmp, "control.ys")
    open(ctl, "w").write(script(rtl, DEPTH, pin_all(bits, DEPTH)))
    print()
    print("control, whole grid pinned: %s" % run(ctl))

    paths = []
    for i, b in enumerate(bits):
        p = os.path.join(tmp, "bit%03d.ys" % i)
        open(p, "w").write(script(rtl, DEPTH, "-set-at %d in_I %d" % (3 + i, 1 - int(b))))
        paths.append(p)

    print("%d miters, bit i forced off-solution and the other %d free, %d at a time"
          % (len(paths), len(bits) - 1, JOBS))
    verdicts = {}
    running = []
    for p in paths + [None] * JOBS:
        if p is not None:
            running.append((p, subprocess.Popen(["yosys", p], stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, text=True)))
        while len(running) >= JOBS or (p is None and running):
            q, proc = running.pop(0)
            out = proc.communicate()[0]
            v = ("equivalent" if "no model found" in out else
                 "COUNTEREXAMPLE" if "model found: FAIL" in out else "ERROR")
            verdicts[q] = v
            if p is None and not running:
                break

    tally = {}
    for v in verdicts.values():
        tally[v] = tally.get(v, 0) + 1
    print("  " + ", ".join("%s: %d" % kv for kv in sorted(tally.items())))
    if tally.get("equivalent") == len(paths):
        print()
        print("no counterexample differs from the solution at any position, so the")
        print("solution grid is the unique counterexample at this unroll depth")


if __name__ == "__main__":
    main()
