"""Check the prose artifacts against the verified numbers.

Several figures in this project were corrected more than once. This scans the
documents for values that have since been retired, so a stale number cannot
survive in a file nobody reopened.
"""
import glob
import re
import sys

# value that must no longer appear -> what replaced it, and why
RETIRED = [
    (r"\b203 of 208\b|\b203/208\b|203 of the 208",
     "hint-box overlap is 207 of 208 (hint_box.py measures the box in layout.png)"),
    (r"\b450 cells\b|6,379|6379 um2",
     "Hardcaml synthesises to 363 cells / 5,892 um2 through synth_hardcaml.ys"),
    (r"within one cell of|converge to within one cell",
     "the two reconstructions do NOT converge: 451 vs 363 cells"),
    (r"five flops can still move|five flops could still move",
     "nine flops move from an arbitrary finished state, and neither success-latch flop is among them"),
    (r"arbitrary ~?20-star stream|not the solution grid",
     "the solution grid IS the counterexample, and forced: 121 UNSAT runs plus the control"),
    (r"27\.5 ?s\b|26\.51 ?s\b",
     "quote var/clause counts, not wall-clock"),
    (r"15-entry table|93 f5\.",
     "the mask table has 16 entries: ... f5 8f, plus 6a at the saturated index"),
]

# things that should be present somewhere, as a spot-check that corrections landed
EXPECTED = [
    ("207 of 208", "hint-box overlap"),
    ("363", "Hardcaml cell count"),
    ("forced", "the counterexample is forced, not lucky"),
]

DOCS = ["WRITEUP-SCAFFOLD.md", "TOOLCHAIN.md", "figures_template.html", "figures.html"]


def main():
    docs = [d for d in DOCS if glob.glob(d)]
    problems = 0
    for path in docs:
        text = open(path, errors="replace").read()
        for pattern, fix in RETIRED:
            for m in re.finditer(pattern, text):
                line = text.count("\n", 0, m.start()) + 1
                print("%s:%d  retired value %r" % (path, line, m.group(0)))
                print("      -> %s" % fix)
                problems += 1
    scaffold = open("WRITEUP-SCAFFOLD.md", errors="replace").read() if glob.glob("WRITEUP-SCAFFOLD.md") else ""
    for needle, what in EXPECTED:
        if needle not in scaffold:
            print("WRITEUP-SCAFFOLD.md  missing %s (%r)" % (what, needle))
            problems += 1
    print("documents checked: %d" % len(docs))
    print("stale or missing: %d" % problems)
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
