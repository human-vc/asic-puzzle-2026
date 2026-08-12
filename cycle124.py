"""Reproduce the reconstruction bug that simulation could not catch.

The first reconstruction asserted the verdict on the same edge that consumed the
last bit. The silicon registers it one cycle later. This script rebuilds that
version of the RTL, pins the input stream to the puzzle's own solution grid, and
runs the miter at a range of unroll depths.

The solution grid is the stimulus every simulation had already passed on, and it
is a counterexample: the miter is clean through depth 123 and fails at 124.
Bisecting the depth is what turns "the reconstruction is wrong somewhere" into a
cycle number.
"""
import os
import re
import subprocess
import sys
import tempfile

ANCHOR = "                ok_q  <= ok;"
DEPTHS = (123, 124)


def immediate_version(src):
    """assert the verdict combinationally, the way the first attempt did"""
    if ANCHOR not in src:
        raise SystemExit("anchor not found in puzzle_rtl.v; the RTL has moved")
    return src.replace(ANCHOR, ANCHOR + "\n                success_q <= ok;")


def script_for(depth, rtl_path, bits):
    base = open("equiv.ys").read()
    base = base.replace("read_verilog -sv puzzle_rtl.v",
                        "read_verilog -sv %s" % rtl_path)
    sets = " ".join("-set-at %d in_I %s" % (3 + k, b)
                    for k, b in enumerate(bits) if 3 + k <= depth)
    base = re.sub(r"sat -seq \d+", "sat -seq %d" % depth, base)
    return base.replace("-verify", sets + " -verify")


def main():
    tmp = tempfile.mkdtemp(prefix="cycle124-")
    rtl = os.path.join(tmp, "puzzle_rtl_immediate.v")
    open(rtl, "w").write(immediate_version(open("puzzle_rtl.v").read()))
    bits = open("solution_bits.txt").read().strip()

    print("input pinned to the solution grid (%d bits, %d stars)"
          % (len(bits), bits.count("1")))
    print("reset holds timesteps 1-2, so cell k arrives at timestep 3+k")
    print()
    for depth in DEPTHS:
        path = os.path.join(tmp, "eq_%d.ys" % depth)
        open(path, "w").write(script_for(depth, rtl, bits))
        out = subprocess.run(["yosys", path], capture_output=True, text=True).stdout
        proved = "SAT proof finished - no model found" in out
        print("  unroll depth %3d: %s" % (depth, "equivalent" if proved else
                                          "COUNTEREXAMPLE"))
    print()
    print("the silicon registers the verdict one cycle after the last bit;")
    print("the first reconstruction asserted it on the same edge")


if __name__ == "__main__":
    sys.exit(main())
