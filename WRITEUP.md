# The chip that never stores the puzzle

Behind the 728 logic cells in Jane Street's ASIC puzzle sits an 11 by 11 two-star Star Battle checker that reads one bit per cycle, never stores the full grid, accepts exactly one arrangement, and releases `(* TWO STARS *)` only after that arrangement has passed every constraint. Recovering the accepted grid was the immediate objective, but a grid that happens to work says little about whether the circuit has been understood, so I carried the reconstruction further: two independent extractions agree on every resolved pin, an unrolled miter proves that `success` is exactly the Star Battle predicate over the complete 121-bit input window, and separate Verilog and Hardcaml implementations match the extracted silicon under the operating protocol. Together, those results expose a compact streaming architecture whose most interesting choices become visible only after the gates have been turned back into a machine.

![Recovered regions and the unique accepted grid](figures/puzzle.svg)

*The recovered region map and the only accepted grid. Every region is 4-connected; each row, column, and region contains two stars; no two stars touch.*

## What the chip is

| Property | Recovered result |
|---|---|
| Input | 121 bits on `I`, row-major, one per enabled clock |
| Verdict | `success`, one cycle after the final bit |
| Accepted grids | Exactly one |
| Payload | 15 bytes on `O[7:0]`: `(* TWO STARS *)` |
| Die | 200 by 352.7 µm |
| Logic | 728 cells, including 92 flip-flops, beside 890 inert fill, tap, decap, and diode cells |
| Extraction | 741 nets touching 5,094 resolved pin sites |

Several kinds of evidence support those rows, and keeping them separate matters. Here, 121 one-hot experiments establish the region map, logic cones and physical placement identify the block boundaries, bounded miters establish equivalence, and an independent Star Battle solver confirms the uniqueness found through the recovered predicate. Throughout this report, an exhaustive result carries its bound in the same sentence, while a structural interpretation remains an interpretation even when later measurements support it.

## From layout to logic

Getting a netlist out of the supplied GDS was straightforward because the standard-cell master names, the pin labels on `li1`, and the top-level port labels on `met3` survived the layout flow. KLayout's connectivity engine could therefore recover the interconnect without geometric cell recognition. Although “nothing is labeled” still describes the difficult part of the puzzle, the missing labels concern function rather than cell identity: the layout gives up its gates readily and says almost nothing about why they are connected that way.

That distinction is useful because it makes extraction a premise to test, not a feat to exaggerate. Running the same method on the warm-up GDS reproduced its shipped netlist histogram exactly, with 18 cell types and 230 instances on both sides. For the main design, I then wrote a second extractor around `gdstk`, exact polygon booleans, and a separate union-find implementation. Across all 5,094 pin sites they could probe, both paths found the same 741 electrical partitions:

```text
pin sites found: 5095
resolved 5094 sites, unresolved 0
distinct nets touching pins: 741

sites probed in both extractions: 5094 (klayout found no net at 0)
distinct nets: mine=741  klayout=741
partitions identical: yes
```

Because extraction establishes connectivity rather than behaviour, the cell library received its own check. Of the 66 instantiated cells that carry behaviour, 63 combinational ones matched the SkyWater PDK over every input vector, while the three sequential ones completed a directed 16-step clock, reset, and set sequence without a mismatch. Readers can rerun that entire path from `puzzle.gds`; [TOOLCHAIN.md](TOOLCHAIN.md) contains the commands, dependencies, and the one known floating net discussed later.

## A one-pass Star Battle checker

Once the nets were trustworthy, the arithmetic exposed the architecture before individual cones did: 121 puzzle bits enter the circuit, yet only 92 flip-flops exist, and 12 of those belong to the output generator, leaving too little state to buffer the grid internally. Instead, each arriving bit updates a collection of small counters and passes into a 12-stage history line, allowing the checker to decide every rule as a stream.

Adjacency shows the economy of that approach most clearly. A new star needs to be compared with only four earlier positions: the cell immediately to its left and the three cells above it. Four remaining neighbours arrive later and perform the reciprocal check themselves. Row-edge masking removes false neighbours across line boundaries, leaving the complete adjacency test in seven standard cells. In the trace below, the star at row 5, column 9 moves through the delay line until a second star arrives directly below it at row 6, column 9; the violation latches on the following edge.

```text
stars at cell 64 (r5c9) and cell 75 (r6c9)

cycle         63 64 65 66 67 68 69 70 71 72 73 74 75 76 77
row            5  5  5  6  6  6  6  6  6  6  6  6  6  6  7
col            8  9 10  0  1  2  3  4  5  6  7  8  9 10  0
              --------------------------------------------
I              .  1  .  .  .  .  .  .  .  .  .  .  1  .  .
tap  1         .  .  1  .  .  .  .  .  .  .  .  .  .  1  .
tap  2         .  .  .  1  .  .  .  .  .  .  .  .  .  .  1
tap  3         .  .  .  .  1  .  .  .  .  .  .  .  .  .  .
tap  4         .  .  .  .  .  1  .  .  .  .  .  .  .  .  .
tap  5         .  .  .  .  .  .  1  .  .  .  .  .  .  .  .
tap  6         .  .  .  .  .  .  .  1  .  .  .  .  .  .  .
tap  7         .  .  .  .  .  .  .  .  1  .  .  .  .  .  .
tap  8         .  .  .  .  .  .  .  .  .  1  .  .  .  .  .
tap  9         .  .  .  .  .  .  .  .  .  .  1  .  .  .  .
tap 10         .  .  .  .  .  .  .  .  .  .  .  1  .  .  .
tap 11         .  .  .  .  .  .  .  .  .  .  .  .  1  .  .
tap 12         .  .  .  .  .  .  .  .  .  .  .  .  .  1  .
              --------------------------------------------
adjacency      .  .  .  .  .  .  .  .  .  .  .  .  .  1  1
```

Counting follows the same narrow logic because, once every row, column, and region must contain exactly two stars, none of the tallies needs to distinguish four from five; two-bit saturation at three preserves every decision the final comparator can make. A row tally resets at each boundary, eleven column tallies persist for the full stream, and eleven region tallies follow the hard-wired map. Those choices explain the physical proportions of the circuit: 59 cells serve the column accumulators, 206 serve the regions, 9 serve the current row, and only 7 enforce adjacency.

Similar-looking accumulator cones made the region wiring easy to misread, so I measured it rather than assigning names by inspection. Feeding one star at each of the 121 input positions and recording which group changed recovered 11 regions whose sizes sum to 121. An independent solver confirmed that every region is 4-connected, found one solution before reaching its cap of five, and matched the grid accepted by the chip.

## Solving is not proving

Unrolling 122 cycles into CNF produced 11,970 variables and 39,650 clauses, from which a SAT solver returned the 121-bit, 22-star grid shown above. The unroll has to run one cycle past the grid, because at 121 cycles the verdict has not yet landed and the same query is correctly unsatisfiable. Gate-level simulation then placed the timing precisely: `success` remains low on the edge that consumes the last input, rises one cycle later, and opens the output stream.

```text
success right after last bit: 0
success one cycle later:      1

O[7:0] for the next 20 cycles:
hex: 28 2a 20 54 57 4f 20 53 54 41 52 53 20 2a 29 00 00 00 00 00
asc: (* TWO STARS *).....
```

One accepted input is weak evidence for a recovered specification, especially when that same input guided the reconstruction, so I built the Star Battle rules independently and compared the two predicates in both directions. Within a 122-cycle unroll with every input bit free, `chip accepts and specification rejects` is UNSAT, the reverse direction is also UNSAT, and the same specification has exactly one satisfying grid. Differential simulation added 37,382 structured cases with no disagreement: the accepted grid itself, all one-bit and two-bit changes to it, 20,000 random grids that already satisfy two stars per row, 5,000 uniform grids, and 5,000 random grids containing exactly 22 stars. These tests are illustrations around the proof, with the near-miss strata chosen to expose missing row, adjacency, or total-count logic.

Despite passing every simulation against the known solution stream, the first readable RTL still contained a timing error. I had asserted the verdict on the same edge that consumed the final bit, while the silicon registers it one cycle later. Bisection found equivalence through unroll depth 123 and a counterexample at 124; pinning the stream reproduced the failure with the accepted grid.

That counterexample was not a convenient choice made by the solver. I ran 121 additional miters, each forcing one input bit away from the solution while leaving the other 120 free, and all 121 were UNSAT across the full 145-cycle protocol window. Both implementations compute the same predicate and differ only in when they latch it, every output is gated by `success`, and only one grid is accepted, so the sole observable counterexample must be the accepting run. Only one extra observation cycle could therefore expose the timing error on the input I had simulated most carefully.

## The message is not stored as text

Jane Street marked the output generator as safe to ignore during the initial analysis, and it can indeed be removed without changing `success`, but understanding it explains why simulating the circuit is necessary to obtain the final bytes. I initially looked for plaintext constants among its gates, yet none exist there. Inside that block, an 8-bit LFSR combines with a 4-bit saturating index to compute

```text
O = permute(LFSR) XOR mask(index)
```

where the fifteen message masks are `4d ad fb 83 13 79 1c b5 79 63 c7 68 93 f5 8f`; a final mask, `6a`, occupies the saturated index and parks the output at zero. Identical mask bytes at indices 5 and 8 emit different letters, `O` and `T`, because the changing LFSR supplies the difference. Plaintext materialises only when the LFSR advances from its reset seed.

Three experiments distinguish that explanation from a fitting exercise. Across all 15 emitted bytes, flipping each of the eight LFSR bits moved exactly the one output bit predicted by the recovered permutation, giving 120 correct single-bit responses. Randomising the LFSR destroyed the text, and randomising the index did the same. Four un-reset flip-flops implement the index, and eight more hold the LFSR, four of which reset to zero while four reset to one. Those four are the only set-reset flops on the die, and they are what keeps the seed away from the all-zero state a shift register could never leave. After `success`, the counter advances to 15 and saturates as the LFSR continues to generate the value cancelled by the last mask.

## Logic returns to geometry

Cone membership divided the design into functional blocks, and probing the net at each cell's output pin placed those assignments back on the die. Their physical clustering supplied a useful cross-check: the output-generator box in the supplied hint contains 207 of the 208 cells assigned to that cone, all 12 of its flip-flops, no flip-flop from another block, and no non-shared cell from another block. Only cell `$296` sits well outside the box rather than straddling its boundary.

![Functional blocks placed on the recovered die](figures/floorplan.svg)

*Every gate is coloured by cone membership and placed from its output-pin geometry. Grey cells are shared or outside a single named cone.*

| Block | Cells | Flops | Role |
|---|---:|---:|---|
| Cell and row counters | 14 | 8 | Locate the incoming bit |
| Run and done flags | 3 | 2 | Mark the end of the stream |
| Input history | 12 | 12 | Retain the preceding twelve bits |
| Adjacency check | 7 | 1 | Reject touching stars |
| Row accumulator | 9 | 3 | Enforce two stars in the current row |
| Column accumulators | 59 | 22 | Enforce two stars in each column |
| Region accumulators | 206 | 22 | Enforce two stars in each recovered region |
| Total-star counter | 22 | 8 | Compare the running total against 22 |
| Success latch | 32 | 2 | Register the final verdict |
| Output generator | 208 | 12 | Emit the masked message |

*The rows above account for all 92 flip-flops. A further 124 cells are shared between cones and 17 resist single attribution.*

## Back to hardware

A reconstruction becomes more useful when it can survive another representation, so I wrote the recovered machine twice: 169 lines of Verilog and 109 lines of Hardcaml. Bounded miters against the extracted netlist close for 145 cycles under the operating protocol, with 3,100,406 variables and 8,531,120 clauses for Verilog, and 1,831,366 variables and 4,842,030 clauses for Hardcaml. A second proof keeps all 121 input bits free across the 122-cycle decision window. Hardcaml was a natural second language because the recovered payload, `(* TWO STARS *)`, is already an OCaml comment.

Both descriptions were then synthesized through the same Yosys flow onto a Liberty whose Boolean functions came from the PDK and whose areas were measured from `puzzle.gds`. Measured on that basis, the silicon contains 728 logic cells occupying 10,758 µm², Verilog maps to 451 cells and 6,816 µm², and Hardcaml maps to 363 cells and 5,892 µm². Their different totals are useful rather than awkward, since they show that logical equivalence does not imply a unique structural recovery.

Packaging the Verilog version behind the Tiny Tapeout interface completed the round trip. Its testbench drives only `uio[0]`, reaches `success = 1`, and receives all 15 payload bytes. At 6,816 µm² against a 160 by 100 µm tile, the design occupies an estimated 43 percent by cell area; that figure is not an OpenLane placement result.

## Where the proof stops

Bounded equivalence remains the strongest result established here, since an attempted k-induction proof did not converge across the differently encoded state spaces, particularly the one-hot and binary tallies, and a fixed-point argument also failed because an arbitrary finished state includes unreachable assignments. Nine flip-flops can still move under that unconstrained experiment, although neither success-latch flop is among them. Those results do not weaken the 122-cycle predicate proof or the 145-cycle protocol proof, but they do prevent either claim from becoming an unbounded equivalence statement.

One extracted net, `$1447`, has no driver and feeds two gates in the output path. Because the default simulator assigns unknown nets zero, I repeated the differential tests with the net forced to each value and obtained zero disagreements and one accepted grid both ways; the formal predicate proof also stays UNSAT in both directions when `$1447` receives a fresh SAT variable every cycle. Its position outside the `success` cone confines the uncertainty to `O[1]` and `O[4]`.

An eight-bit total-star counter remains in the design even though two stars in each of eleven valid rows already forces a total of 22. It is still electrically load-bearing: flipping any one of its eight flops midway through the accepted run prevented `success` in 24 of 24 injections. Even the unreachable high bit participates because the final comparator tests the entire register against 22.

## Below the die

Thirty-six placeholder cells had initially looked electrically irrelevant, which was correct and incomplete. Their row extends below the main cell array to y = -52.72 µm, outside the vertical range of the supplied layout image, and their two widths encode dots and dashes rather than logic.

![Morse code formed by placeholder-cell widths](figures/morse.svg)

*Drawn to scale, the 36 cells below the array decode to `PER ARENAM AD ASTRA`.*

Following the geometric anomaly recovered `PER ARENAM AD ASTRA`, “through the sand to the stars.” A second message sits in `example_inputs.vcd`: reading each row as 7-bit ASCII, least-significant bit in column zero, yields `The night sky awaits  ` with two trailing spaces. Together with the payload, those messages close the same chain the technical analysis establishes: a labelled cell library becomes an unlabelled netlist, the netlist becomes a streaming Star Battle machine, and only then does the machine disclose what its gates were arranged to say.

Full reproduction, including extraction, simulation, proofs, round-trip synthesis, and the scripts behind each quoted number, is documented in [TOOLCHAIN.md](TOOLCHAIN.md).
