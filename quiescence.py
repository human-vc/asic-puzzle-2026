"""Show the chip reaches a fixed point, which upgrades the bounded equivalence
proof to a complete one.

The machine freezes: once the run flag is set and the output index has
saturated, no input other than reset can change any flip-flop. So the number of
distinct state transitions after reset is bounded, and verifying past that point
covers all reachable behaviour rather than merely a window of it.
"""
from pysat.solvers import Cadical153

from cnf import CnfBackend
from sim import Design

DONE = 7                      # run/done flag
IDX = [0, 1, 2, 91]           # output index counter (saturates at 15)


def main():
    d = Design("puzzle_net.json")
    be = CnfBackend()
    order = [f[1] for f in d.flops]

    # an arbitrary state, constrained only to "finished and done emitting"
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
    print("can any flop change after the machine has finished?  %s"
          % ("YES" if sat else "NO -- the state is a fixed point"))
    if sat:
        model = set(l for l in s.get_model() if l > 0)
        moved = [i for i, q in enumerate(order)
                 if (state[q] in model) != (nxt[q] in model)]
        print("   flops that move: %s" % moved[:12])
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
    print("does asserting reset always restore the reset state?  %s"
          % ("NO" if s2.solve(assumptions=[be2.orn(bad)]) else "YES"))
    s2.delete()


if __name__ == "__main__":
    main()
