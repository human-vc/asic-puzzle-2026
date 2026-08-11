"""Tseitin CNF backend: run the gate-level design symbolically into a SAT formula."""

TRUE = 1   # reserved variable, asserted true


class CnfBackend:
    def __init__(self):
        self.nvars = 1
        self.clauses = [[TRUE]]
        self.one = TRUE
        self.zero = -TRUE
        self.cache = {}

    def new(self):
        self.nvars += 1
        return self.nvars

    def _const(self, lit):
        if lit == self.one:
            return 1
        if lit == self.zero:
            return 0
        return None

    def not_(self, a):
        return -a

    def andn(self, xs):
        lits = []
        for x in xs:
            c = self._const(x)
            if c == 0:
                return self.zero
            if c == 1:
                continue
            lits.append(x)
        lits = sorted(set(lits))
        if not lits:
            return self.one
        if len(lits) == 1:
            return lits[0]
        for a in lits:
            if -a in lits:
                return self.zero
        key = ("and", tuple(lits))
        if key in self.cache:
            return self.cache[key]
        y = self.new()
        for a in lits:
            self.clauses.append([-y, a])
        self.clauses.append([y] + [-a for a in lits])
        self.cache[key] = y
        return y

    def orn(self, xs):
        return -self.andn([-x for x in xs])

    def xor2(self, a, b):
        ca, cb = self._const(a), self._const(b)
        if ca is not None:
            return b if ca == 0 else -b
        if cb is not None:
            return a if cb == 0 else -a
        if a == b:
            return self.zero
        if a == -b:
            return self.one
        key = ("xor", tuple(sorted((abs(a), abs(b)))))
        sign = (1 if a > 0 else -1) * (1 if b > 0 else -1)
        if key in self.cache:
            y = self.cache[key]
        else:
            x, z = abs(a), abs(b)
            y = self.new()
            self.clauses += [[-y, x, z], [-y, -x, -z], [y, -x, z], [y, x, -z]]
            self.cache[key] = y
        return y if sign > 0 else -y

    def xorn(self, xs):
        r = self.zero
        for x in xs:
            r = self.xor2(r, x)
        return r

    def mux(self, a0, a1, s):
        cs = self._const(s)
        if cs is not None:
            return a1 if cs == 1 else a0
        if a0 == a1:
            return a0
        return self.orn([self.andn([a1, s]), self.andn([a0, -s])])
