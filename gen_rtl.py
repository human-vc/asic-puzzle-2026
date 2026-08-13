"""Emit a readable RTL reconstruction of the puzzle chip.

The region table and the output string are taken from what was recovered from
the layout, so nothing is hand-transcribed.
"""
from recovered import REGION_CELLS as REGIONS

N = 11
from recovered import MESSAGE as STRING

import re


def uncomment(text):
    out = []
    for l in text.splitlines():
        q, cut = False, None
        for i, ch in enumerate(l):
            if ch == '"':
                q = not q
            elif ch == "/" and not q and l[i:i + 2] == "//":
                cut = i
                break
        if cut is not None:
            l = l[:cut].rstrip()
            if not l:
                continue
        out.append(l)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip("\n") + "\n"


def main(out="puzzle_rtl.v"):
    grid = [REGIONS[r * N:(r + 1) * N] for r in range(N)]
    letters = sorted({ch for row in grid for ch in row})
    idx = {ch: i for i, ch in enumerate(letters)}

    rom_rows = []
    for r in range(N):
        vals = ", ".join("4'd%d" % idx[grid[r][c]] for c in range(N))
        rom_rows.append("    %s%s  // row %d" % (vals, "," if r < N - 1 else " ", r))

    chars = ", ".join("8'h%02x" % ord(c) for c in STRING)

    v = f'''// Reconstruction of the Jane Street ASIC puzzle, recovered from puzzle.gds.
//
// The chip reads an 11x11 grid as 121 serial bits on I (row-major, one bit per
// clock while enable is high) and raises success one cycle after the last bit
// if the grid is a valid two-star Star Battle solution: exactly two stars in
// every row, column and region, and no two stars touching, including
// diagonally. It then streams a 15-byte string out of O.
//
// Structure follows the silicon: a mod-11 cell counter and a mod-11 row
// counter, a 12-deep history of I that supplies the three neighbours in the
// row above, one row tally reused every row, and eleven column and eleven
// region tallies that persist to the end.

`default_nettype none

module puzzle_rtl (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    input  wire       I,
    output wire [7:0] O,
    output wire       success
);

    localparam integer N = {N};

    // Region each cell belongs to, recovered by probing the accumulators.
    localparam [4*N*N-1:0] REGION_ROM = {{
{chr(10).join(rom_rows)}
    }};

    function [3:0] region_of(input [3:0] r, input [3:0] c);
        integer k;
        begin
            k = r * N + c;
            region_of = REGION_ROM[4*(N*N-1-k) +: 4];
        end
    endfunction

    // ---- sequencing --------------------------------------------------------
    reg [3:0] col, row;
    reg       done;

    wire step      = enable & ~done;
    wire last_col  = (col == N-1);
    wire last_row  = (row  == N-1);
    wire star      = step & I;
    wire finish    = step & last_col & last_row;

    // ---- the three neighbours in the row above, plus the one to the left ----
    reg [11:0] hist;                 // I delayed 1..12 steps
    wire left     = hist[0]  & (col  != 0);
    wire up_right = hist[9]  & (row  != 0) & (col  != N-1);
    wire up       = hist[10] & (row  != 0);
    wire up_left  = hist[11] & (row  != 0) & (col  != 0);
    wire touching = star & (left | up | up_left | up_right);

    // ---- tallies -----------------------------------------------------------
    reg [1:0] rowcnt;
    reg [1:0] colcnt [0:N-1];
    reg [1:0] regcnt [0:N-1];
    reg       bad;

    wire [3:0] regid = region_of(row, col);

    function [1:0] bump(input [1:0] v, input inc);
        bump = (!inc) ? v : (v == 2'd3 ? 2'd3 : v + 2'd1);
    endfunction

    wire [1:0] rowcnt_next = bump(rowcnt, star);
    wire       row_bad     = step & last_col & (rowcnt_next != 2'd2);

    integer i;
    reg [1:0] colcnt_next [0:N-1];
    reg [1:0] regcnt_next [0:N-1];
    always @* begin
        for (i = 0; i < N; i = i + 1) begin
            colcnt_next[i] = bump(colcnt[i], star & (col   == i[3:0]));
            regcnt_next[i] = bump(regcnt[i], star & (regid == i[3:0]));
        end
    end

    reg all_two;
    always @* begin
        all_two = 1'b1;
        for (i = 0; i < N; i = i + 1)
            if (colcnt_next[i] != 2'd2 || regcnt_next[i] != 2'd2)
                all_two = 1'b0;
    end

    wire ok = all_two & ~bad & ~row_bad & ~touching;

    // The silicon registers the verdict one cycle after the last bit, so the
    // result is armed at the final cell and presented on the next clock.
    reg success_q, armed, ok_q;
    assign success = success_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            col       <= 4'd0;
            row       <= 4'd0;
            done      <= 1'b0;
            hist      <= 12'd0;
            rowcnt    <= 2'd0;
            bad       <= 1'b0;
            armed     <= 1'b0;
            ok_q      <= 1'b0;
            success_q <= 1'b0;
            for (i = 0; i < N; i = i + 1) begin
                colcnt[i] <= 2'd0;
                regcnt[i] <= 2'd0;
            end
        end else if (step) begin
            hist <= {{hist[10:0], I}};
            bad  <= bad | touching | row_bad;

            for (i = 0; i < N; i = i + 1) begin
                colcnt[i] <= colcnt_next[i];
                regcnt[i] <= regcnt_next[i];
            end

            rowcnt <= last_col ? 2'd0 : rowcnt_next;
            col    <= last_col ? 4'd0 : col + 4'd1;
            if (last_col)
                row <= last_row ? 4'd0 : row + 4'd1;

            if (finish) begin
                done  <= 1'b1;
                armed <= 1'b1;
                ok_q  <= ok;
            end
        end else if (armed) begin
            armed     <= 1'b0;
            success_q <= ok_q;
        end
    end

    // ---- output generator --------------------------------------------------
    // Starts when success rises, one byte per clock, then holds at zero.
    // It ignores enable, exactly as the silicon does.
    localparam integer NCHAR = {len(STRING)};
    localparam [8*NCHAR-1:0] MESSAGE = {{{chars}}};

    reg [3:0] oidx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            oidx <= 4'd0;
        else if (success_q && oidx != NCHAR[3:0])
            oidx <= oidx + 4'd1;
    end

    assign O = (success_q && oidx != NCHAR[3:0])
             ? MESSAGE[8*(NCHAR-1-oidx) +: 8]
             : 8'h00;

endmodule

`default_nettype wire
'''
    open(out, "w").write(uncomment(v))
    print("wrote %s (%d lines)" % (out, v.count("\n") + 1))
    print("regions:", "".join(letters), "-> ids 0..%d" % (len(letters) - 1))


if __name__ == "__main__":
    main()
