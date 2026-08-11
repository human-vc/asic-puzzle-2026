"""Export a cycle-by-cycle trace of the chip solving its own puzzle, plus the
floorplan geometry, as JSON for the figure pack.

The region/column accumulators are 2-bit; their bit encoding is calibrated
empirically (feed n stars into one region, read the pair) rather than assumed.
"""
import json

from sim import Design, BitBackend
from recovered import REGION_CELLS as REGIONS

from recovered import (REGION_ACCUM as REGION_GROUPS, COLUMN_ACCUM as COLUMN_GROUPS,
                       ROW_ACCUM as ROW_GROUP, CELL_COUNTER as COL_CTR,
                       ROW_COUNTER as ROW_CTR)

N = 11

GRID = [REGIONS[r * N:(r + 1) * N] for r in range(N)]
LETTERS = sorted({ch for row in GRID for ch in row})
CELLS_OF = {ch: [r * N + c for r in range(N) for c in range(N) if GRID[r][c] == ch]
            for ch in LETTERS}


def run_stream(d, be, bits_lanes, cycles):
    st = d.new_state(be)
    for _ in range(2):
        d.cycle(be, st, {"rst_n": be.zero, "enable": be.zero, "I": be.zero})
    snaps = []
    for c in range(cycles):
        lane = bits_lanes[c] if c < len(bits_lanes) else be.zero
        v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one, "I": lane, "clk": be.zero})
        snaps.append((dict(st), v))
        d.cycle(be, st, {"rst_n": be.one, "enable": be.one, "I": lane})
    v = d.eval_at(be, st, {"rst_n": be.one, "enable": be.one, "I": be.zero, "clk": be.zero})
    snaps.append((dict(st), v))
    return st, snaps


def calibrate(d, order, groups, cells_for):
    """per-group pattern -> count, learned by feeding n stars into that group.
    The accumulators saturate, so 3 means "3 or more"."""
    be = BitBackend(64)
    lanes = [0] * (N * N)
    plans = []
    for gi in range(len(groups)):
        for n in range(4):
            plans.append((gi, n, cells_for(gi)[:n]))
    for lane, (_gi, _n, cells) in enumerate(plans):
        for k in cells:
            lanes[k] |= 1 << lane
    st, _ = run_stream(d, be, lanes, N * N)
    tables = [dict() for _ in groups]
    for lane, (gi, n, _cells) in enumerate(plans):
        pat = tuple((st[order[f]] >> lane) & 1 for f in groups[gi])
        prev = tables[gi].get(pat)
        if prev is not None and prev != n:
            raise RuntimeError("ambiguous encoding for group %d: %s" % (gi, pat))
        tables[gi][pat] = n
    return tables


def calibrate_row(d, order):
    """The row accumulator resets on the same edge that consumes a row's last
    cell, so read it one cycle earlier with the stars confined to columns 0-9."""
    be = BitBackend(8)
    lanes = [0] * (N * N)
    for n in range(4):
        for c in list(range(0, N - 1, 2))[:n]:
            lanes[c] |= 1 << n
    _st, snaps = run_stream(d, be, lanes, N * N)
    state = snaps[N - 1][0]
    table = {}
    for n in range(4):
        pat = tuple((state[order[f]] >> n) & 1 for f in ROW_GROUP)
        if table.get(pat, n) != n:
            raise RuntimeError("ambiguous row encoding at n=%d" % n)
        table[pat] = n
    return table


def column_of_group(d, order):
    """which physical column each column-accumulator group tracks"""
    be = BitBackend(N)
    lanes = [0] * (N * N)
    for c in range(N):
        lanes[0 * N + c] |= 1 << c
    st, _ = run_stream(d, be, lanes, N * N)
    mapping = {}
    for gi, g in enumerate(COLUMN_GROUPS):
        acc = 0
        for f in g:
            acc |= st[order[f]]
        hits = [c for c in range(N) if (acc >> c) & 1]
        if len(hits) != 1:
            raise RuntimeError("column group %d responds to %s" % (gi, hits))
        mapping[gi] = hits[0]
    return mapping


def decode_group(table, state, order, group):
    pat = tuple((state[order[f]] & 1) for f in group)
    return table.get(pat, 3)


def main():
    d = Design("puzzle_net.json")
    order = [f[1] for f in d.flops]
    bits = [int(c) for c in open("solution_bits.txt").read().strip()]

    reg_tables = calibrate(d, order, REGION_GROUPS, lambda gi: CELLS_OF[LETTERS[gi]])
    row_table = calibrate_row(d, order)
    print("row accumulator (one-hot, resets each row):",
          {"".join(map(str, k)): v for k, v in sorted(row_table.items(), key=lambda x: x[1])})
    colmap = column_of_group(d, order)
    col_tables = calibrate(d, order, COLUMN_GROUPS,
                           lambda gi: [r * N + colmap[gi] for r in range(N)])
    print("accumulators calibrated: %d region + %d column, saturating at 3"
          % (len(reg_tables), len(col_tables)))
    print("column-group -> column:", [colmap[i] for i in range(N)])

    be = BitBackend(1)
    lanes = [1 if b else 0 for b in bits]
    st, snaps = run_stream(d, be, lanes, N * N + 20)

    def num(state, idxs):
        return sum(((state[order[f]] & 1) << i) for i, f in enumerate(idxs))

    frames = []
    for c, (state, v) in enumerate(snaps):
        regs = [decode_group(reg_tables[i], state, order, g)
                for i, g in enumerate(REGION_GROUPS)]
        cols = [0] * N
        for i, g in enumerate(COLUMN_GROUPS):
            cols[colmap[i]] = decode_group(col_tables[i], state, order, g)
        frames.append({
            "cell": num(state, COL_CTR),
            "row": num(state, ROW_CTR),
            "regions": regs,
            "columns": cols,
            "rowacc": decode_group(row_table, state, order, ROW_GROUP),
            "success": v["net:success"] & 1,
            "O": sum(((v["net:O[%d]" % k] & 1) << k) for k in range(8)),
        })

    out = {
        "bits": bits,
        "regions": ["".join(GRID[r]) for r in range(N)],
        "letters": LETTERS,
        "frames": frames,
    }

    bl = json.load(open("blocks.json"))
    panels = {}
    for cell in bl["cells"]:
        panels.setdefault(cell["block"], []).append(
            [round(cell["x"], 2), round(cell["y"], 2), round(cell["w"], 2), round(cell["h"], 2)])
    out["die"] = bl["die"]
    out["panels"] = panels
    json.dump(out, open("figure_data.json", "w"))
    print("frames: %d   panels: %d   wrote figure_data.json"
          % (len(frames), len(panels)))
    print("region tallies at end:", frames[-1]["regions"])
    print("column tallies at end:", frames[-1]["columns"])
    print("string:", "".join(chr(f["O"]) for f in frames if f["success"] and f["O"]))


if __name__ == "__main__":
    main()
