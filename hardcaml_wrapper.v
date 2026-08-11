// Adapts the Hardcaml design to the silicon's port names and reset polarity so
// the same miter can compare it against the netlist extracted from puzzle.gds.
`default_nettype none
module puzzle_hardcaml (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    input  wire       I,
    output wire [7:0] O,
    output wire       success
);
    starbattle u_core (
        .clk    (clk),
        .reset  (~rst_n),
        .enable (enable),
        .i      (I),
        .o      (O),
        .success(success)
    );
endmodule
`default_nettype wire
