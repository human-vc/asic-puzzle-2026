| # | Check | Status | Key observation |
|---|-------|--------|-----------------|
| 1 | `recovered.py` | PASS | `OK`; 13 flop groups covering 92/92 flops, no duplicates/unaccounted; **11 regions summing to 121**; message `'(* TWO STARS *)'` (15 bytes) |
| 2 | `netlist_check.py` | **FAIL (prints `RESULT: PROBLEMS FOUND`)** | **728 logic cells**, 890 inert, 719 driven nets, 0 multiply-driven, 0 floating cell inputs, 6 driven-but-unloaded (all `conb_1`), **1 undriven net used as an input: `$1447`** — this is the sole trigger of the failure verdict |
| 3 | `compare_extractions.py` | PASS | `PARTITIONS ARE IDENTICAL`; 5095 pin sites found, **5094 resolved and probed in both**, **741 nets** in each (`mine=741 klayout=741`), 0 unresolved |
| 4 | `starbattle_check.py` | PASS | **11 regions**, contiguous(4-conn)=True, exactly **1** Star Battle solution (cap 5), `matches the grid the chip accepts: True` |
| 5 | `proof.py` | PASS | Both directions **UNSAT** (0.0s each); 122-cycle unroll, 16504 vars / 56074 clauses; spec has exactly **1** satisfying grid |
| 6 | `verify.py solution_bits.txt 40` | PASS | success=0 right after last bit, **1** one cycle later; ASCII `(* TWO STARS *)` then zeros |
| 7 | `diff_test.py` | PASS | **total grids tested: 37382, disagreements: 0, accepted by chip: 1** (solution 1/0/1; 1-bit 121/0/0; 2-bit 7260/0/0; 2-per-row 20000/0/0; uniform 5000/0/0; 22-star 5000/0/0) |
| 8 | `easter_eggs.py` | PASS | morse `'PER ARENAM AD ASTRA'`; hidden stimulus text `'The night sky awaits  '` (two trailing spaces) |
| 9 | `facts.py` | PASS | 728 logic cells, 890 inert, 92 flops (84 dfrtp/4 dfxtp/4 dfstp), 121 input bits, **22 stars**, 11 regions, 5094 sites / 741 nets, 37,382 grids 0 disagreements, 200 x 352.7 um die |
| 10 | yosys `/tmp/e.ys` (Verilog vs silicon) | PASS | `SAT proof finished - no model found: SUCCESS!` then `VERILOG_PROVED`; 3,100,406 vars / 8,531,120 clauses, 145 time steps, 27.5s |
| 11 | `yosys -q equiv_hardcaml.ys` | PASS | `HARDCAML_PROVED`; verbose rerun shows `SAT proof finished - no model found: SUCCESS!`, 1,831,366 vars / 4,842,030 clauses |
| 12 | iverilog/vvp Tiny Tapeout tb | PASS | `uio_oe = 00000001`, `success = 1`, `message (15 bytes) = "(* TWO STARS *)"`, `$finish at 1446000` |

Discrepancies against the expected values

- Every expected number matches exactly: 728 logic cells, 92 flip-flops, 121 input bits, 22 stars (independently recounted from `solution_bits.txt`: len 121, 22 ones), 11 regions, 5094 pin sites agreeing, 741 nets, 37382 grids with 0 disagreements, `(* TWO STARS *)`, `PER ARENAM AD ASTRA`, `The night sky awaits`.
- Two cosmetic notes, not value mismatches: the hidden text prints as `'The night sky awaits  '` with two trailing spaces, and `netlist_check.py`'s "driven nets: 719" is a different metric from the 741 (it counts only nets with a driving output pin, excluding the four input ports and the power rails; `compare_extractions.py` and `undriven_check.py` both report 741 nets touching pins).

The one real failure, and what it does and does not mean

`netlist_check.py` is the only script that reports a problem, and its `ok` verdict at /Users/jacobcrainic/asic-puzzle-2026/netlist_check.py:60 is `not multi and not undriven and not floating_inputs`. `multi` and `floating_inputs` are both empty; the verdict flips solely on `undriven = ['$1447']`. Net `$1447` has no driving output pin anywhere in the netlist and fans out to exactly two pins:

```
$279  sky130_fd_sc_hd__a31oi_2  A1 -> $1447
$1781 sky130_fd_sc_hd__a311o_2  A1 -> $1447
```

(plus four via shapes). It appears in the reconstructed netlist as an undriven `wire n_1447;` at /Users/jacobcrainic/asic-puzzle-2026/puzzle_extracted.v:88, used at lines 935 and 1313.

This is pre-existing, not a regression: `git status` is clean at commit `76d0fd9`, so the committed script has always printed `PROBLEMS FOUND`. `undriven_check.py` independently lists 7 undriven nets, six of which are the expected `clk`, `rst_n`, `enable`, `I`, `VPWR`, `VGND`; `$1447` is the seventh.

I checked whether this undermines the solution, since /Users/jacobcrainic/asic-puzzle-2026/sim.py:145 silently defaults unknown nets to zero (`values.get(i, be.zero)`), meaning `proof.py` and `diff_test.py` implicitly assume `$1447 = 0`. Re-running the gate-level differential test with the net forced to each value gives 0 disagreements and 1 accepted grid both ways, and re-running the full `proof.py` equivalence with `$1447` as a free SAT variable still returns UNSAT in both directions. The net is functionally dead; the `success <=> Star Battle` claim holds regardless of what it settles to. Nothing was modified — those were scratch scripts run against the unchanged sources.