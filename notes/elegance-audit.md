> Code review from 2026-08-12, kept as written (it is critical of the code as
> it then stood). Findings 1-5, 10-12, 15, 17 and 18 have since been applied;
> findings 6, 7, 8, 9, 13, 14 and 16 have not. Line numbers refer to the
> pre-fix files.

## Findings, ranked by clarity gained

### 1. `recovered.py`'s "one source of truth" claim is false in four files
`recovered.py:1-8` and `TOOLCHAIN.md:7-11` both promise that every script imports its constants "so a correction cannot leave a stale copy behind". Four files keep private copies:

- `blocks.py:8-24` re-types **all eleven flop groups** by hand (`FLOP_BLOCKS`). It is not even a transcription: `"run/done flag": [7, 61]` silently merges `RUN_FLAG=[7]` and `TOGGLE=[61]`, and `"cell counter (mod 11)": [38, 45, 73, 84]` is sorted whereas `CELL_COUNTER=[38, 84, 45, 73]` is deliberately weight-ordered (1,2,4,8). A reader diffing the two files cannot tell which orderings are meaningful.
- `quiescence.py:14-15` re-declares `DONE = 7` / `IDX = [0, 1, 2, 91]` with comments restating `RUN_FLAG` and `OUT_INDEX`.
- `gen_rtl.py:9` and `gen_hardcaml.py:12` both hardcode `STRING = "(* TWO STARS *)"` while `recovered.MESSAGE` holds exactly that. `gen_rtl.py:2-5` claims "the region table and the output string are taken from what was recovered from the layout, so nothing is hand-transcribed" — the string on line 9 is hand-transcribed.

Change: in `blocks.py`, build `FLOP_BLOCKS` from the `recovered` names (`"run/done flag": RUN_FLAG + TOGGLE`, `"output generator": OUT_INDEX + OUT_LFSR`, `"verdict/output shared": [f for f, _ in TOTAL_COUNTER]`, etc.); import `RUN_FLAG`/`OUT_INDEX` in `quiescence.py`; import `MESSAGE` in both generators. This also makes `recovered.check()`'s partition invariant actually protect `blocks.py`, which today it does not.

### 2. `facts.py` says it re-derives every number; five of its rows are literals and one is a fake derivation
Docstring (`facts.py:1`): "Re-derive every number worth quoting, from the artifacts themselves." But `facts.py:81-85` hardcodes the differential-test count, the pin-site agreement, the formal claim, the cycle counts and the power-up count as strings. Worse, `facts.py:50-51`:

```python
reg = open("starbattle_check.py").read()
A(("regions", len(set(re.findall(r"^[A-K]$", reg, re.M)) or set("ABCDEFGHIJK"))))
```

`starbattle_check.py` contains no single-letter lines, so the regex returns the empty set on every run (verified) and the `or` fallback prints the hardcoded 11. It is a constant wearing a derivation costume, and it scrapes a *Python source file* for data that `recovered.region_letters()` returns directly.

Change: `A(("regions", len(region_letters())))` and drop the now-unused `re` scrape; move lines 81-85 under a clearly separated heading such as `"quoted from the runs above (not re-derived here)"` so the docstring's promise matches the table.

### 3. `quiescence.py`'s docstring asserts a result the script refutes
Lines 1-8 state as fact: "The machine freezes: once the run flag is set and the output index has saturated, no input other than reset can change any flip-flop. So ... verifying past that point covers all reachable behaviour rather than merely a window of it." Running it prints:

```
can any flop change after the machine has finished?  YES
   flops that move: [0, 1, 2, 4, 7, 14, 21, 68, 91]
does asserting reset always restore the reset state?  NO
```

`TOOLCHAIN.md:83` is honest about this ("fixed-point attempt"); the module is not. The reason is visible in the code — `state = {q: be.new() for q in order}` (line 24) quantifies over *arbitrary*, including unreachable, states — but nothing says so.

Change: rewrite the docstring to describe the experiment rather than a conclusion ("checks whether any flop can move from an arbitrary state that satisfies done ∧ index-saturated; the state is unconstrained, so unreachable states are included, and the answer is YES — this does not upgrade the bounded proof"), and add the one-line why at line 24. Nothing else needs touching.

### 4. `check_cells.py` writes to a hardcoded Claude-session scratch path
Lines 26, 80, 85, 88 all contain `/private/tmp/claude-501/-Users-jacobcrainic/6e326e8e-b652-4122-bdd7-c9edfdf33ec0/scratchpad/...`. On any other machine the script dies at line 26, and `TOOLCHAIN.md:96` advertises it as a reproduction step. Line 84 also does `__import__("glob").glob(...)` inline.

Change: one `tmp = tempfile.mkdtemp()` at the top of `main()` and `os.path.join(tmp, ...)` at the four sites; hoist `import glob` to the module header.

### 5. Six files re-derive the region grid that `recovered.py` already exposes
`recovered.py` defines `region_grid()`, `region_letters()`, `regions()`, `forward_neighbours()`. Only `gen_figures.py` uses `region_grid`, only `diff_test.py` uses `forward_neighbours`, and `regions()`/`region_letters()` have no callers at all. Meanwhile:

- `GRID = [REGIONS[r * N:(r + 1) * N] for r in range(N)]` appears verbatim in `diff_test.py:15`, `export_trace.py:18`, `proof.py:43`, `starbattle_check.py:25`, `gen_rtl.py:13`, `gen_hardcaml.py:18`.
- `sorted({ch for row in grid for ch in row})` appears in `gen_rtl.py:14`, `gen_hardcaml.py:19`, `export_trace.py:19`.
- The letter→cells map is rebuilt in `proof.py:46-49`, `starbattle_check.py:26-29`, `export_trace.py:20-21`.
- `N = 11` is redeclared in `proof.py:16`, `export_trace.py:16`, `diff_test.py:13`, `gen_rtl.py:8`, `gen_hardcaml.py:11`, though `starbattle_check.py:7` already shows the right move (`from recovered import N`).

Change: `from recovered import N, region_grid, region_letters, regions` in those six files and delete the local re-derivations. Related one-liner in `recovered.py:62`: define `REGION_CELLS = [ch for row in region_grid() for ch in row]` instead of `REGION_MAP.split()`, so the `assert len(rows) == N` shape check in `region_grid` runs for every importer instead of only when someone calls the function.

### 6. `sim.py` flops are a bare 6-tuple, positionally indexed in eight files, and the comment describes five fields
`sim.py:51` says `# (kind, q_node, d_node, clk_node, ctrl_node)`; line 93 appends a 6-tuple ending in `iname`. Consumers read `f[1]` (7 files), `f[2]` (`analyze.py:54`, `blocks.py:42`), `f[5]` (`analyze.py:42`, `blocks.py:66`), and unpack with placeholder noise like `for kind, q, _dd, _c, _ctrl, _n in d.flops` (`quiescence.py:54`, `solve.py:17`). Nothing tells a reader that `f[5]` is the instance name except counting commas in a comment that is already wrong.

Change: `Flop = NamedTuple("Flop", [("kind", str), ("q", str), ("d", str), ("clk", str), ("ctrl", Optional[str]), ("inst", str)])`; the tuple stays a tuple so all existing indexing and unpacking keeps working, and new reads become `f.q` / `f.inst`. While there, add `Design.q_nodes` returning `[f.q for f in self.flops]`, which replaces the identical `order = [f[1] for f in d.flops]` line in `regions.py:19`, `quiescence.py:21`, `trace.py:12`, `export_trace.py:107`.

### 7. `sim.py` offers two incompatible ways to advance time, one of which quietly requires `BitBackend`
The module docstring promises the same design "can be run bit-parallel ... or symbolically". True of `step()` (line 184), which goes through backend methods only. Not true of `clock_edge()`/`cycle()` (lines 161-206), which use raw Python `~`, `&` and `be.mask` (lines 171-179) and therefore blow up on `CnfBackend`. The two also differ in mutation contract with no note: `cycle` mutates `state` and returns it; `step` is pure and returns `(new_state, values)`.

Change: one sentence in the class or module docstring — "`step()` is backend-agnostic; `clock_edge()`/`cycle()` model the real two-edge protocol with int bit-vectors and are `BitBackend`-only" — plus a note on `cycle` that it mutates in place. No code motion needed.

### 8. `sim.py` keeps write-only state and never-called methods
`self.consts` (line 55, written 59-60, never read), `self.drivers` (line 56, written 94) whose comment says "net -> node id driving it" but which stores `("FLOP", [])`, and the local `POWER` dict (line 58) whose values are never used — only `in POWER` membership is. `outputs()` (208) and `stats()` (212) have no callers in the repo. In a file advertised as already de-linted, these read as leftovers a reader will try to make sense of.

Change: delete `consts`/`drivers` and their writes; make `POWER` a set (or reuse `cells.POWER_PINS`, which is exactly this set already); keep or drop `outputs`/`stats` deliberately, but if kept, say they are for interactive use.

### 9. `blocks.py` bounding-box accumulator is unreadable
`blocks.py:99-106` uses `defaultdict(lambda: [0, 1e9, -1e9, 1e9, -1e9])` and then `s[0] += 1; s[1] = min(s[1], r["x"])` … through `s[4]`, unpacked 6 lines later as `n, x0, x1, y0, y1`. Positional slots plus sentinel infinities where the data is already in memory.

Change: group first, measure second — `by_block = defaultdict(list)` then `x0 = min(r["x"] for r in rs)`, `x1 = max(r["x"] + r["w"] for r in rs)`, etc. Same numbers, no sentinels. Also `blocks.py:82`: `sorted(blocks)[0] if len(blocks) == 1 else "shared"` reads as a tie-break but the branch is a singleton set; `next(iter(blocks))` says what it means.

### 10. `gen_figures.py` silently drops one recovered block from the floorplan
`ORDER` (lines 22-24) lists ten panels; `blocks.json` contains eleven real blocks plus `shared`/`unassigned`. The missing one is `"run/done flag"` (3 cells) — omitted with no comment, while the obviously-deliberate omissions (`shared`, `unassigned`) are also uncommented, so a reader cannot tell intent from accident. `ORDER` is also a hand-copy of `blocks.ORDER`. Separately, line 57 hardcodes "die 200 × 353 µm" into the caption while `die["w"]`/`die["h"]` (200.0, 352.72) are loaded three lines above.

Change: `from blocks import ORDER as BLOCK_ORDER` and derive the panel list from it with an explicit `EXCLUDE = {"shared", "unassigned"}` (or add the eleventh panel — the grid already reflows at `cols=5`); format the caption from `die["w"]`/`die["h"]`.

### 11. `export_trace.py` renames imports into a collision
Lines 10-14 split the `recovered` import into two statements and rename everything, producing `CELL_COUNTER as COL_CTR` sitting beside `COLUMN_ACCUM as COLUMN_GROUPS`. "COL_CTR" is the *cell-within-row* counter; "COLUMN_GROUPS" are the eleven per-column tallies. Two unrelated registers now both look like "col".

Change: one import statement, original names (`CELL_COUNTER`, `ROW_COUNTER`, `REGION_ACCUM`, `COLUMN_ACCUM`, `ROW_ACCUM`).

### 12. One register has four names across the repo
`recovered.CELL_COUNTER` ("position within a row") is `col` in `gen_rtl.py:64`, `col_w` in the Hardcaml, `COL_CTR` in `export_trace.py`, `"cell counter (mod 11)"` in `blocks.py`. The two generated artifacts even disagree in their headers: `gen_rtl.py:32` says "a mod-11 cell counter and a mod-11 row counter"; `gen_hardcaml.py:37` (and `hardcaml/starbattle.ml:8`) says "a mod-11 **column** counter". Same sentence, same generator pair, different noun — and "column" already means the eleven column tallies.

Change: pick one word (the layout-neutral "cell counter" is the one `recovered.py` uses) and make the two generated docstrings identical.

### 13. `export_trace.py` verifies one group-to-hardware mapping and assumes the other
`column_of_group()` (81-97) *measures* which physical column each accumulator group tracks and raises if the answer is not unique. Twelve lines later, `calibrate(d, order, REGION_GROUPS, lambda gi: CELLS_OF[LETTERS[gi]])` (line 110) *assumes* region-accumulator group `gi` is the `gi`-th letter alphabetically. That assumption is sound because `regions.py:54` assigned letters in group order, but nothing at the point of use says so, and the asymmetry with the column path invites the reader to think something is missing.

Change: one comment at line 110 — "region group i is letter i by construction: `regions.py` names groups in accumulator order, so no probe is needed here."

### 14. `cells.py` splices a mux back in via an unexplained magic net name
`cells.py:48`: `ops.append(("mux", "mux_2to10_out_X", ["A0", "A1", "S"]))`. That string is the internal wire in the PDK model (`sky130_fd_sc_hd__mux2` instantiates `sky130_fd_sc_hd__udp_mux_2to1 mux_2to10 (mux_2to10_out_X, A0, A1, S)` and then `buf buf0 (X, mux_2to10_out_X)`). `PRIM_RE` skips UDP instances, so re-driving that exact net lets the already-parsed `buf0` carry the value to `X`. Nothing in the file says any of this, and it is the one place where a typo would silently produce a mux that drives nothing. The `conb` branch below it *replaces* `ops` while the `mux2` branch *appends*, another difference with no stated reason (`conb`'s outputs come from `pullup`/`pulldown`, also not gate primitives).

Change: two comment lines stating why the name is what it is and why one branch appends while the other replaces. Optionally assert the target name appears in the parsed ops so a PDK rename fails loudly.

Minor, same file: `_body()` (27-30) returns `text[i:j]` without checking `find()` for `-1`; a model without `` `celldefine `` yields an empty body and thus a silently port-less, op-less cell rather than an error.

### 15. `proof.py` inlines logic that `recovered.py` exports, and prints a conclusion its loop cannot support
- Lines 60-63 re-inline the forward-neighbour offsets `((0,1),(1,-1),(1,0),(1,1))` that `recovered.forward_neighbours` exists to own (and that `diff_test.py:17` already imports); lines 46-49 rebuild `recovered.regions()`.
- Lines 101-106: `while s.solve() and n < 3:` then, unconditionally, `print("satisfying grids for the spec: %d (so the accepted input is unique)" % n)`. If the cap were ever hit the line would read "3 ... so the accepted input is unique". The parenthetical is a claim about `n == 1` printed regardless of `n`, and `3` is an unnamed cap.

Change: use `forward_neighbours(r * N + c)` in the neighbour loop and `regions()` for the region terms; name the cap (`MAX_MODELS = 3`) and make the sentence match what was found ("unique" only when `n == 1`, otherwise "at least %d").

### 16. The KLayout stack setup is written three times
`extract.extract()` (35-51), `place.build_l2n()` (19-33) and `compare_extractions.build_l2n_flat()` (24-36) contain the same fifteen lines of `make_polygon_layer` / `connect` / via-zip. They already share `STACK` and `VIAS` via imports, so the constants are centralised but the loop that consumes them is not. The three differ only in `l2n.threads = 4`, whether label layers are attached, and whether the top cell is flattened first.

Change: one `connect_stack(l2n, ly, with_labels=True)` in `extract.py` returning `(conductors, labels)`; the other two call it. Roughly 30 lines disappear and the "second extractor shares no code" claim in `extract2.py` stays true, since `extract2.py` is not involved.

### 17. Function-local imports scattered through otherwise tidy modules
`gen_figures.py:96` (`import math` inside a doubly-nested loop), `gen_figures.py:137` (`import os` inside `write`), `blocks.py:98` (`import collections` mid-`main`), `extract2.py:132` (`import json` mid-`main`), `extract2.py:165` (`import math` inside `transform_point`), `check_cells.py:84` (`__import__("glob")`). Every one of these modules already has a clean import block at the top; the strays make a reader wonder whether an import is conditional or expensive.

Change: hoist all six.

### 18. Two conventions for passing values into the simulator
`diff_test.py`, `regions.py`, `export_trace.py` correctly pass backend words (`be.one`, `be.zero`, packed lanes). `verify.py:15,18,22` and `trace.py:19,23,26` pass raw `0`/`1`. Both happen to work only because those two files use `BitBackend(1)`; at any other width `"rst_n": 1` would assert reset in lane 0 alone. The interface has no guard and no note.

Change: use `be.one`/`be.zero` in `verify.py` and `trace.py` (identical behaviour at width 1) so the repo shows one convention, and add a line to `Design.base_values` saying inputs must already be backend words.

## Already good, leave alone

- `recovered.check()` (`recovered.py:119-140`) is the right invariant expressed the right way: the flop groups must partition all 92 flops, and the failure mode it protects against is named in the docstring rather than restated from the code. It just needs `blocks.py` to stop bypassing it (finding 1).
- `extract2.py`'s header explains *why* it duplicates work ("Deliberately shares nothing with extract.py") and names each substitution — this is the model the rest of the repo should follow.
- `compare_extractions.build_l2n_flat`'s docstring (17-20) explains why flattening is necessary rather than what the code does. Same for `recovered.forward_neighbours` (87-91) and `export_trace.calibrate_row` (63-65).
- `gen_rtl.py`'s emitted Verilog is genuinely readable, and its comments (`// The silicon registers the verdict one cycle after the last bit…`, lines 116-117) explain silicon behaviour the RTL alone would not justify. The `bump` function and the `hist` tap comments are exactly right.
- `cnf.py`'s constant folding and structural hashing (`andn`, `xor2`) are compact and correct, and the sign-normalising cache key in `xor2` is the standard idiom rather than a clever one.
- `diff_test.py`'s spec is deliberately an independent reimplementation of the predicate rather than a call into shared code; that redundancy is the point of the file and should not be factored away (only the neighbour offsets are already correctly imported).