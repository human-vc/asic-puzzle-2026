"""Gate-level simulator for netlists extracted by extract.py.

Values are opaque objects handled by a backend, so the same compiled design can
be run bit-parallel (Python ints = many candidate inputs at once) or symbolically.
Zero-delay semantics: settle combinational logic, sample D before each clock
edge, apply flops, re-settle.
"""
import json

import cells as cells_mod


class BitBackend:
    """N-way parallel simulation; each value is an int used as a bit vector."""

    def __init__(self, width=64):
        self.width = width
        self.mask = (1 << width) - 1
        self.zero = 0
        self.one = self.mask

    def not_(self, a):
        return ~a & self.mask

    def andn(self, xs):
        r = self.mask
        for x in xs:
            r &= x
        return r

    def orn(self, xs):
        r = 0
        for x in xs:
            r |= x
        return r

    def xorn(self, xs):
        r = 0
        for x in xs:
            r ^= x
        return r

    def mux(self, a0, a1, s):
        return (a1 & s) | (a0 & ~s & self.mask)


class Design:
    def __init__(self, netlist_json, pdk_dir="pdk/functional"):
        data = json.load(open(netlist_json))
        self.lib = cells_mod.load_cells(pdk_dir)
        self.data = data

        self.nodes = {}
        self.flops = []
        self.consts = {}
        self.drivers = {}

        POWER = {"VPWR": 1, "VGND": 0, "VPB": 1, "VNB": 0}
        self.consts["VPWR"] = 1
        self.consts["VGND"] = 0

        for inst in data["instances"]:
            cn = inst["cell"]
            if not cn.startswith("sky130"):
                continue
            base = cells_mod.base_name(cn)
            cell = self.lib[base]
            if cell.kind == "none":
                continue
            iname = inst["name"]
            conns = inst["conns"]

            def sig(local):
                """map a cell-internal signal name to a global node id"""
                if local in POWER:
                    return "$" + local
                if local in cell.inputs or local in cell.outputs:
                    net = conns.get(local)
                    if net is None:
                        return "$FLOAT"
                    return "net:" + net
                return "%s/%s" % (iname, local)

            if cell.kind in ("dfxtp", "dfrtp", "dfstp"):
                q = sig("Q")
                d = sig("D")
                clk = sig("CLK")
                ctrl = None
                if cell.kind == "dfrtp":
                    ctrl = sig("RESET_B")
                elif cell.kind == "dfstp":
                    ctrl = sig("SET_B")
                self.flops.append((cell.kind, q, d, clk, ctrl, iname))
                self.drivers[q] = ("FLOP", [])
                continue

            for prim, out, ins in cell.ops:
                o = sig(out)
                self.nodes[o] = (prim, [sig(i) for i in ins])

        self.const_nodes = {"$VPWR": 1, "$VGND": 0, "$VPB": 1, "$VNB": 0, "$FLOAT": 0}
        self.ports = {}
        for p in ("clk", "rst_n", "enable", "I", "success"):
            self.ports[p] = "net:" + p
        self.obits = ["net:O[%d]" % i for i in range(8)]

        self._topo()

    def _topo(self):
        flop_q = {f[1] for f in self.flops}
        order, state = [], {}
        nodes = self.nodes

        for n in list(nodes):
            if n in state:
                continue
            stack = [(n, False)]
            while stack:
                cur, done = stack.pop()
                if done:
                    state[cur] = 2
                    order.append(cur)
                    continue
                if state.get(cur):
                    continue
                if cur not in nodes or cur in flop_q:
                    state[cur] = 2
                    continue
                state[cur] = 1
                stack.append((cur, True))
                for i in nodes[cur][1]:
                    if state.get(i) != 2 and i in nodes and i not in flop_q:
                        if state.get(i) == 1:
                            raise RuntimeError("combinational loop at %s" % i)
                        stack.append((i, False))
        self.order = order

    def new_state(self, be):
        return {f[1]: be.zero for f in self.flops}

    def settle(self, be, values):
        nodes, ev = self.nodes, cells_mod.EVAL
        for n in self.order:
            prim, ins = nodes[n]
            values[n] = ev[prim](be, [values.get(i, be.zero) for i in ins])
        return values

    def base_values(self, be, state, inputs):
        """inputs must already be backend words (be.one / be.zero / packed lanes),
        not Python 0/1 -- at width > 1 a bare 1 would drive lane 0 only"""
        v = dict(self.const_nodes)
        v = {k: (be.one if val else be.zero) for k, val in v.items()}
        v.update(state)
        for name, val in inputs.items():
            v["net:" + name] = val
        return v

    def eval_at(self, be, state, inputs):
        v = self.base_values(be, state, inputs)
        self.settle(be, v)
        return v

    def clock_edge(self, be, state, inputs_low, inputs_high):
        """One clock transition: settle at pre-edge inputs, sample D, apply, re-settle."""
        pre = self.eval_at(be, state, inputs_low)
        post_inputs = inputs_high
        post = self.eval_at(be, state, post_inputs)

        new = {}
        for kind, q, d, clk, ctrl, _ in self.flops:
            cl_old = pre.get(clk, be.zero)
            cl_new = post.get(clk, be.zero)
            rose = ~cl_old & cl_new & be.mask
            cur = state[q]
            nxt = (pre.get(d, be.zero) & rose) | (cur & ~rose & be.mask)
            if kind == "dfrtp":
                rst_n = post.get(ctrl, be.one)
                nxt = nxt & rst_n
            elif kind == "dfstp":
                set_n = post.get(ctrl, be.one)
                nxt = nxt | (~set_n & be.mask)
            new[q] = nxt
        state.update(new)
        return state

    def step(self, be, state, inputs):
        """Next state as a pure function of state+inputs (clock tree is ungated,
        non-inverting, and drives nothing else, so every flop samples together)."""
        v = self.eval_at(be, state, inputs)
        new = {}
        for kind, q, d, clk, ctrl, _ in self.flops:
            nx = v.get(d, be.zero)
            if kind == "dfrtp":
                nx = be.andn([nx, v.get(ctrl, be.one)])
            elif kind == "dfstp":
                nx = be.orn([nx, be.not_(v.get(ctrl, be.one))])
            new[q] = nx
        return new, v

    def cycle(self, be, state, inputs):
        """Full clk cycle: rising edge then falling edge, with clk held in inputs."""
        low = dict(inputs)
        low["clk"] = be.zero
        high = dict(inputs)
        high["clk"] = be.one
        self.clock_edge(be, state, low, high)
        self.clock_edge(be, state, high, low)
        return state

    def outputs(self, be, state, inputs):
        v = self.eval_at(be, state, dict(inputs, clk=be.zero))
        return v

    def stats(self):
        return "nodes=%d flops=%d" % (len(self.nodes), len(self.flops))
