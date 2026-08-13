

`default_nettype none

module tt_um_starbattle_checker (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
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
