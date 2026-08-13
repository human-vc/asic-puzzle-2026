# Toolchain

Commands and what each one produces, so the results here can be reproduced or
re-derived from `puzzle.gds` alone. This file documents *how to run* the tools;
the account of how the puzzle was solved lives elsewhere.

## One source of truth

`recovered.py` holds everything recovered from the layout: the region map, the
message, and which flip-flop belongs to which block. Every other script imports
from it, so a correction cannot leave a stale copy behind somewhere else.

```sh
.venv/bin/python recovered.py
```

That checks the structure against itself: the thirteen flop groups must
partition all 92 flip-flops with none missing and none claimed twice, and the
regions must cover all 121 cells. The check fails loudly if a block is
mislabelled.

## Prerequisites

```sh
python3 -m venv .venv && .venv/bin/pip install klayout gdstk numpy python-sat pillow
brew install icarus-verilog yosys          # simulation, synthesis, equivalence
brew install opam && opam install hardcaml # optional: the Hardcaml version
```

```sh
tools/fetch_pdk.sh
```

That populates `pdk/functional/` and `pdk/verilog/` with the SkyWater cell models
from `google/skywater-pdk-libs-sky130_fd_sc_hd`. Nothing downstream of the
extraction runs without them, and they are not in the repo.

## 1. Layout to netlist

```sh
.venv/bin/python extract.py puzzle.gds puzzle_net.json
```

KLayout `LayoutToNetlist` over the interconnect stack only (li1, mcon, met1-5,
vias) with no device extraction. The cells keep their names and pin labels, so
the gate netlist falls out directly. 728 logic cells, 92 flip-flops.

```sh
.venv/bin/python extract.py control
```

The control: the same extraction on `warmup/04_final.gds` must reproduce the cell
histogram of the warm-up netlist Jane Street ships. 18 cell types, 230 instances,
identical on both sides. It is the only check of the method against a ground
truth rather than against itself.

## 2. Checking the extraction

```sh
.venv/bin/python compare_extractions.py   # second extractor, shares no code
.venv/bin/python netlist_check.py         # one driver per net, undriven / unloaded
```

`extract2.py` uses gdstk instead of KLayout, exact polygon booleans instead of
KLayout's connectivity engine, and its own union-find. Both are asked which of
the 5,094 pin sites are electrically common; the partitions must be identical.

## 3. Understanding it

```sh
.venv/bin/python analyze.py puzzle_net.json   # flop dependency graph, cones
.venv/bin/python trace.py flops               # cycle-by-cycle flop trace
.venv/bin/python regions.py                   # region map, by one-hot probing
.venv/bin/python place.py && .venv/bin/python blocks.py   # blocks on the die
.venv/bin/python trace.py window 64 75        # the history window, as text
.venv/bin/python hint_box.py                  # floorplan vs their hint image
.venv/bin/python output_gen.py                # decode the message, then try to break it
.venv/bin/python redundancy.py                # which flops the verdict depends on
```

`regions.py` feeds a single star at each of the 121 cells in turn and records
which region accumulator moves, recovering the hard-wired region map.

`trace.py window` streams a grid with one adjacency violation and prints the
twelve history taps as rows, so a star travelling down the line reads as a
diagonal.

`hint_box.py` measures the boxed region in the shipped `layout.png` against the
die outline in the same image, then counts how much of the independently
derived floorplan lands inside it.

`output_gen.py` recovers the mask table by subtracting the permuted LFSR from
each emitted byte, then attacks the reading: single-bit flips must be XOR-linear
at every index, and randomising either the LFSR or the index must destroy the
message.

## 4. Solving

```sh
.venv/bin/python solve.py            # unroll 122 cycles to CNF, solve
.venv/bin/python trace.py verify solution_bits.txt 20
.venv/bin/python starbattle_check.py # independent Star Battle solver
```

## 5. Proving

```sh
.venv/bin/python proof.py       # success <=> Star Battle, all 2^121 inputs
.venv/bin/python diff_test.py   # 37,382 grids, gate netlist vs spec
.venv/bin/python quiescence.py  # reset behaviour; fixed-point attempt
```

### What did not close

Bounded equivalence is the strongest claim the writeup makes, and these are the
two reasons it stays bounded.

k-induction did not converge. The extracted design and the rebuild encode the
same state differently, one-hot in the row accumulator against binary in the
tallies, so the induction step admits state pairs that agree on every output and
disagree on the encoding. A fixed-point argument over "the stream has finished"
fails for the same reason: an arbitrary finished state includes assignments no
real run can reach. Under that unconstrained experiment nine flip-flops can still
move, though neither success-latch flop is among them.

One net, `$1447`, has no driver and feeds two gates in the output path. Icarus
assigns unknown nets zero, so `diff_test.py` was rerun with the net forced to
each value: zero disagreements and one accepted grid both ways. `proof.py` also
stays UNSAT in both directions when `$1447` is given a fresh SAT variable every
cycle, which covers an adversarial driver rather than a constant one. The net
sits outside the `success` cone, so the uncertainty is confined to `O[1]` and
`O[4]`.

## 6. Independent simulation

```sh
.venv/bin/python gen_verilog.py
incs=(-Ipdk/verilog); for d in pdk/verilog/cells/*/; do incs+=(-I$d); done
iverilog -g2012 -DFUNCTIONAL $incs -o tb.vvp \
    pdk/verilog/sky130_cells.v puzzle_extracted.v tb_puzzle.v && vvp tb.vvp
```

```sh
.venv/bin/python check_cells.py   # cell models vs the PDK, exhaustively
```

## 7. Back to hardware

```sh
.venv/bin/python gen_rtl.py       # readable Verilog reconstruction
yosys equiv.ys                    # bounded miter, 145 cycles under the protocol
.venv/bin/python gen_liberty.py   # Liberty: PDK functions, areas from the die
yosys -q synth.ys                 # re-synthesize onto that cell set
.venv/bin/python roundtrip.py     # compare against the real die
.venv/bin/python cycle124.py      # reproduce the verdict-timing bug, by depth
.venv/bin/python cycle124.py forced   # 121 miters; slow, JOBS=3 by default
```

Hardcaml version:

```sh
eval $(opam env --switch=jsasic)
.venv/bin/python gen_hardcaml.py
cd hardcaml && dune exec ./main.exe            # simulate
dune exec ./main.exe verilog > ../starbattle_hardcaml.v
cd .. && yosys equiv_hardcaml.ys               # prove against the silicon
yosys -q synth_hardcaml.ys                     # same round trip as synth.ys
```

Tiny Tapeout:

```sh
iverilog -g2012 -o tt.vvp tinytapeout/src/project.v \
    tinytapeout/src/puzzle_rtl.v tinytapeout/test/tb_tt.v && vvp tt.vvp
```

## 8. Easter eggs

```sh
.venv/bin/python easter_eggs.py
```

Recovers the Morse spelled by the placeholder cells below the cell array, and
the text hidden in the stimulus of `example_inputs.vcd`.

## The rendered page

```sh
.venv/bin/python render.py docs/index.html WRITEUP.md
```

`render.py` inlines every figure and the animation into a single self-contained
HTML file, so `docs/index.html` needs no network at all. GitHub Pages serves it
from the `docs/` folder.

## Figure pack

```sh
.venv/bin/python gen_figures.py      # puzzle, floorplan, morse
.venv/bin/python gen_datapath.py     # block diagram, counts from blocks.json
.venv/bin/python gen_animation.py    # the accepted grid streaming, as a GIF
```

```sh
.venv/bin/python export_trace.py
.venv/bin/python -c "open('figures.html','w').write(
    open('figures_template.html').read().replace('__DATA__', open('figure_data.json').read()))"
```
