# Blocks for the writeup

Tables, ledgers and raw tool output, ready to paste. Every number here came out
of a run, not a note. Regenerate with the commands named beside each block.
The prose around them is yours.

---

## §B  Summary table

| | |
|---|---|
| What it is | 11x11 two-star Star Battle checker |
| Input | 121 bits on `I`, row-major, one per clock while `enable` is high |
| Verdict | `success` one cycle after the last bit |
| Accepted grids | exactly one |
| Payload | 15 bytes on `O[7:0]`, `(* TWO STARS *)`, an OCaml comment |
| Die | 200 x 352.7 um |
| Logic cells | 728 (plus 890 tap/decap/diode) |
| Flip-flops | 92 = 84 dfrtp + 4 dfxtp + 4 dfstp |
| Cell types | 69 instantiated, 66 with logic |
| Nets | 741 touching pins, across 5,094 pin sites |

## §B  Confidence ledger

| Claim | How established | Bound |
|---|---|---|
| `success` is exactly the Star Battle predicate | miter, both directions UNSAT | all 2^121 input streams |
| Only one grid is accepted | same miter + independent solver | all 2^121 |
| Region map (which cell is in which region) | experiment: one-hot probe, 121 cells | exhaustive over cells |
| Accumulators are 2-bit saturating | experiment: calibrated, not assumed | 0..3 per group |
| Row tally is one-hot and resets per row | experiment: read mid-stream | — |
| Total-star counter is load-bearing | experiment: corrupt it mid-run, `success` dies | one mutation |
| `O = permute(LFSR) xor mask(index)` | experiment: single-bit flips XOR-linear at every index | all 16 indices |
| Message invariant to un-reset flops | exhaustive: all 16 power-up states | complete |
| Message invariant to floating net `$1447` | forced to each value; not in `success` cone | complete for `success` |
| Block boundaries on the die | inferred from cone membership, tested against their hint | 207/208 |
| Reconstruction == silicon | bounded miter | 145 cycles protocol, 122 free |
| Extraction is correct | two code-disjoint extractors agree | 5,094 sites |
| Cell behaviour | exhaustive vs PDK models | every input vector, 63 cells |

## §M  Back to hardware

| | on the die | Verilog | Hardcaml |
|---|---:|---:|---:|
| logic cells | 728 | 451 | 363 |
| flip-flops | 92 | 75 | 75 |
| cell area | 10,758 um2 | 6,816 um2 | 5,892 um2 |
| source lines | -- | 168 | 108 |
| proved vs silicon | -- | 145 cycles | 145 cycles |

Miter sizes, which reproduce exactly where wall-clock does not:
Verilog 3,100,406 vars / 8,531,120 clauses; Hardcaml 1,831,366 / 4,842,030.

Tiny Tapeout: 451 cells / 6,816 um2 against a 160 x 100 um tile = 16,000 um2,
so 43% utilisation. Not an OpenLane result.

## §K  The mask table

The gates hold these, not the text. `O = permute(LFSR) xor mask(index)`.

```
index  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14   15
mask  4d ad fb 83 13 79 1c b5 79 63 c7 68 93 f5 8f   6a
char   (  *     T  W  O     S  T  A  R  S     *  )   --
```

Permutation, one LFSR flop to one output bit:
F03->O0, F04->O5, F05->O2, F21->O4, F22->O6, F44->O3, F77->O1, F90->O7.

---

# Raw output

## §E  two extractions agree
```
distinct nets: mine=741  klayout=741
partitions identical: yes
largest nets by pin count: [(((70, 20), 389), 172), (((70, 20), 265), 128), (((70, 20), 267), 62), (((70, 20), 298), 60), (((71, 20), 19), 56)]
```

## §E  cell models vs the PDK
```
combinational cells: 63   sequential cells: 3
TOTAL MISMATCHES: 0
```

## §I  the equivalence proof
```
netlist unrolled 122 cycles (0.1s)
spec built; total vars=16504 clauses=56074
  chip accepts but spec rejects    : UNSAT  (0.0s)
  spec accepts but chip rejects    : UNSAT  (0.0s)
satisfying grids for the spec: 1 (unique)
```

## §I  differential test
```
solution           n=1       disagreements=0    accepted-by-chip=1
  1-bit flips        n=121     disagreements=0    accepted-by-chip=0
  2-bit flips        n=7260    disagreements=0    accepted-by-chip=0
  random 2-per-row   n=20000   disagreements=0    accepted-by-chip=0
  uniform random     n=5000    disagreements=0    accepted-by-chip=0
  random 22 stars    n=5000    disagreements=0    accepted-by-chip=0

total grids tested: 37382   disagreements: 0   accepted by chip: 1
```

## §H  the answer
```
success right after last bit: 0
success one cycle later:      1

O[7:0] for the next 24 cycles:
hex: 28 2a 20 54 57 4f 20 53 54 41 52 53 20 2a 29 00 00 00 00 00 00 00 00 00
asc: (* TWO STARS *).........
```

## §J  cycle 124
```
input pinned to the solution grid (121 bits, 22 stars), reset released at timestep 3

  unroll depth 123: equivalent
  unroll depth 124: COUNTEREXAMPLE

the silicon registers the verdict one cycle after the last bit;
the first reconstruction asserted it on the same edge
```
Uniqueness (`cycle124.py forced`, ~16 min at JOBS=3):
```
control, whole grid pinned: COUNTEREXAMPLE
121 miters, bit i forced off-solution and the other 120 free, 3 at a time
  equivalent: 121
```

## §L  their hint box as a test
```
die outline scale: 0.32415 um/px in x, 0.32362 um/px in y  (agree to 0.16%)
their box, in die coordinates: x 148.5 - 190.0 um,  y 80.6 - 262.1 um

cells we attribute to the 'output generator' block: 208
  of those, wholly inside their box: 207
    outside: $296 at (77.09, 48.72)
  its flip-flops inside their box: 12 of 12
  flip-flops from any other block inside their box: 0 []
  non-shared cells from other blocks inside their box: 0
```

## §N  easter eggs
```
morse below the die:   'PER ARENAM AD ASTRA'
hidden in the stimulus: 'The night sky awaits  '
```

## §B  the structural invariant
```
flop groups: 13, covering 92 of 92 flops
  duplicates: none
  unaccounted: none
regions: 11, sizes summing to 121
message: '(* TWO STARS *)' (15 bytes)
OK
```

## §M  round trip
```
on the die re-synthesized
logic cells                         728          451
  of which flip-flops                92           75
cell area (um2)                   10758         6816
distinct cell types                  66           48
inert cells (tap/decap/diode)        890          n/a
```

---

# Figure captions

- `figures/puzzle.svg` -- the recovered regions and the one accepted grid. 11 regions, all 4-connected; two stars per row, column and region; none touching.
- `figures/floorplan.svg` -- every gate assigned to a block by cone membership, placed by probing the net at its output pin. Grey is all other logic. Die 200 x 352.7 um.
- `figures/morse.svg` -- the 36 anonymised placeholder cells, drawn to scale, in the single row below the cell array.
