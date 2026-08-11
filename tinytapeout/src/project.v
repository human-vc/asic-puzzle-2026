/*
 * Star Battle checker -- Tiny Tapeout wrapper.
 *
 * The design inside is a reconstruction of the Jane Street 2026 ASIC puzzle
 * chip, recovered from its GDS: it reads an 11x11 grid as 121 serial bits and
 * asserts success if the grid is a valid two-star Star Battle solution, then
 * streams a message out of the dedicated output byte.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_starbattle_checker (
    input  wire [7:0] ui_in,    // dedicated inputs
    output wire [7:0] uo_out,   // dedicated outputs
    input  wire [7:0] uio_in,   // bidirectional: input path
    output wire [7:0] uio_out,  // bidirectional: output path
    output wire [7:0] uio_oe,   // bidirectional: 1 = drive
    input  wire       ena,      // high while the design is selected
    input  wire       clk,
    input  wire       rst_n
);

    wire       grid_bit = ui_in[0];
    wire       feed     = ui_in[1] & ena;
    wire       success;

    puzzle_rtl core (
        .clk    (clk),
        .rst_n  (rst_n),
        .enable (feed),
        .I      (grid_bit),
        .O      (uo_out),
        .success(success)
    );

    assign uio_out = {7'b0, success};
    assign uio_oe  = 8'b0000_0001;

    wire _unused = &{ui_in[7:2], uio_in, 1'b0};

endmodule

`default_nettype wire
