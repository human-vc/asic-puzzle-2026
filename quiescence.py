"""Two experiments about what the chip does once it has finished.

The hope was that the machine reaches a fixed point, which would upgrade the
bounded equivalence proof to a complete one. It does not, and this script is
the evidence: quantifying over ARBITRARY states that satisfy done and
index-saturated -- unreachable ones included -- five flops can still move, so
the argument does not close. Reachability invariants would be needed.

What it does establish: asserting reset restores the reset state for every flop
that has one, from any state and under any input.
"""
from pysat.solvers import Cadical153

from cnf import CnfBackend
from sim import Design

from recovered import RUN_FLAG, OUT_INDEX

DONE = RUN_FLAG[0]
IDX = OUT_INDEX


def main():
    d = Design("puzzle_net.json")
    be = CnfBackend()
    order = [f[1] for f in d.flops]

    # "finished and done emitting", but otherwise unconstrained: this includes
    # states the design can never reach, which is why the answer below is YES
    state = {q: be.new() for q in order}
    assume = [state[order[DONE]]] + [state[order[f]] for f in IDX]

    nxt, _v = d.step(be, state, {"rst_n": be.one, "enable": be.new(),
                                 "I": be.new(), "clk": be.zero})

    changed = []
    for q in order:
        a, b = state[q], nxt[q]
        changed.append(be.xor2(a, b))
    any_change = be.orn(changed)

    s = Cadical153(bootstrap_with=be.clauses)
    sat = s.solve(assumptions=assume + [any_change])
    print("vars=%d clauses=%d" % (be.nvars, len(be.clauses)))
    print("flops can move from an arbitrary finished state: %s" % ("yes" if sat else "no"))
    if sat:
        model = set(l for l in s.get_model() if l > 0)
        moved = [i for i, q in enumerate(order)
                 if (state[q] in model) != (nxt[q] in model)]
        print("  moving flops: %s" % moved[:12])
    s.delete()

    # and with reset asserted it must return to the reset state
    be2 = CnfBackend()
    st2 = {q: be2.new() for q in order}
    nx2, _ = d.step(be2, st2, {"rst_n": be2.zero, "enable": be2.new(),
                               "I": be2.new(), "clk": be2.zero})
    bad = []
    for kind, q, _dd, _c, _ctrl, _n in d.flops:
        want = be2.one if kind == "dfstp" else be2.zero
        bad.append(be2.xor2(nx2[q], want))
    s2 = Cadical153(bootstrap_with=be2.clauses)
    print("reset restores the reset state: %s"
          % ("no" if s2.solve(assumptions=[be2.orn(bad)]) else "yes"))
    s2.delete()


if __name__ == "__main__":
    main()
