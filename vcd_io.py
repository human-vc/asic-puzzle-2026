"""Minimal VCD reader/writer for the puzzle's port set."""
import re

PORTS = ["clk", "rst_n", "enable", "I"]


def read_vcd(path):
    ids, cur, changes = {}, {}, []
    time = 0
    for line in open(path):
        line = line.strip()
        m = re.match(r"\$var\s+\w+\s+\d+\s+(\S+)\s+([^\s\[]+)", line)
        if m:
            ids[m.group(1)] = m.group(2)
            continue
        if line.startswith("#"):
            time = int(line[1:])
            continue
        if not line or line[0] in "$":
            continue
        if line[0] in "01xzXZ" and len(line) > 1:
            val, sym = line[0], line[1:]
        elif line[0] == "b":
            val, sym = line.split()[0][1:], line.split()[1]
        else:
            continue
        name = ids.get(sym)
        if name in PORTS:
            v = 1 if val == "1" else 0
            if cur.get(name) != v:
                cur[name] = v
                changes.append((time, name, v))
    return changes


def sampled_inputs(changes):
    """values of rst_n/enable/I sampled at each clk rising edge"""
    state = {p: 0 for p in PORTS}
    out = []
    by_time = {}
    for t, n, v in changes:
        by_time.setdefault(t, []).append((n, v))
    for t in sorted(by_time):
        pre = dict(state)
        for n, v in by_time[t]:
            state[n] = v
        if pre["clk"] == 0 and state["clk"] == 1:
            out.append((t, pre["rst_n"], pre["enable"], pre["I"]))
    return out


def write_vcd(path, rows, period=10000):
    """rows: list of dicts with clk-cycle input/output values"""
    syms = {"clk": "!", "rst_n": '"', "enable": "#", "I": "$", "O": "%", "success": "&"}
    with open(path, "w") as f:
        f.write("$timescale 1ps $end\n")
        for name in ["clk", "rst_n", "enable", "I"]:
            f.write("$scope module puzzle $end\n$var reg 1 %s %s $end\n$upscope $end\n"
                    % (syms[name], name))
        f.write("$scope module puzzle $end\n$var wire 8 %s O [7:0] $end\n$upscope $end\n"
                % syms["O"])
        f.write("$scope module puzzle $end\n$var wire 1 %s success $end\n$upscope $end\n"
                % syms["success"])
        f.write("$enddefinitions $end\n")
        t = 0
        last = {}
        for row in rows:
            for half in (0, 1):
                vals = dict(row)
                vals["clk"] = half
                for name in ["clk", "rst_n", "enable", "I", "success"]:
                    if last.get(name) != vals[name]:
                        f.write("#%d\n%d%s\n" % (t, vals[name], syms[name]))
                        last[name] = vals[name]
                if last.get("O") != vals["O"]:
                    f.write("#%d\nb%s %s\n" % (t, format(vals["O"], "b"), syms["O"]))
                    last["O"] = vals["O"]
                t += period // 2
