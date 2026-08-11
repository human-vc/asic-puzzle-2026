<!--
Do not publish this project before 4 September 2026: it contains the answer to
the Jane Street ASIC puzzle, and submissions are still open until then.
-->

## How it works

This is an 11x11 two-star Star Battle checker, reconstructed from the layout of
the chip in the Jane Street 2026 ASIC reverse-engineering puzzle. Nothing about
the design was given: the gate netlist was extracted from `puzzle.gds`, the
function was recovered from that netlist, and this RTL was then written to match
it and proved equivalent to the extracted netlist.

The grid arrives one cell at a time, row-major, on `ui[0]`, with `ui[1]` high on
each cycle that should be consumed. After 121 cells the design freezes and
reports on `uio[0]` whether the grid is a valid solution:

- exactly two stars in every row,
- exactly two stars in every column,
- exactly two stars in every one of eleven irregular regions,
- and no two stars orthogonally or diagonally adjacent.

The region map is a hard-wired 121-entry table, recovered by feeding the
original chip a single star at each cell in turn and watching which of its
eleven region accumulators moved.

Internally the structure follows the silicon: a mod-11 counter for the position
within a row and another for the row, a twelve-deep history of the input that
supplies the three neighbours in the row above, a single row tally reused every
row, and eleven column and eleven region tallies that persist to the end. When
the verdict is registered, a small ROM streams a message out of `uo[7:0]`, one
byte per clock, and then holds at zero.

## How to test

Hold `rst_n` low for a few clocks. Then, for each of the 121 grid cells in
row-major order, put the cell's value on `ui[0]` (1 for a star), drive `ui[1]`
high, and clock once. `ui[1]` may be held low for any number of cycles to pause;
the design ignores those cycles.

One clock after the 121st cell, `uio[0]` reports the verdict. If it is high, keep
clocking and read `uo[7:0]` once per cycle to collect the 15-byte message.

`test/tb_tt.v` does exactly this, reading the grid from `solution_bits.txt`:

```
iverilog -g2012 -o tt.vvp src/project.v src/puzzle_rtl.v test/tb_tt.v && vvp tt.vvp
```

There is exactly one grid the checker accepts, and finding it is the puzzle.

## External hardware

None. Any source of a clock and two input bits will do; eleven LEDs on `uo` and
one on `uio[0]` make a pleasant demonstrator.
