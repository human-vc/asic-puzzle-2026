`timescale 1ns/1ps
`default_nettype none

module tb_tt;
  reg clk = 0, rst_n = 0, ena = 1;
  reg [7:0] ui_in = 0;
  wire [7:0] uo_out, uio_out, uio_oe;
  integer fd, k, ch, nchar = 0;
  reg [120:0] bits;
  reg [8*16-1:0] msg;

  tt_um_starbattle_checker dut (
      .ui_in(ui_in), .uo_out(uo_out), .uio_in(8'b0),
      .uio_out(uio_out), .uio_oe(uio_oe), .ena(ena), .clk(clk), .rst_n(rst_n));

  always #5 clk = ~clk;

  initial begin
    fd = $fopen("solution_bits.txt", "r");
    for (k = 0; k < 121; k = k + 1) begin
      ch = $fgetc(fd);
      bits[k] = (ch == "1");
    end
    $fclose(fd);

    repeat (3) @(posedge clk);
    #1 rst_n = 1;
    for (k = 0; k < 121; k = k + 1) begin
      ui_in = {6'b0, 1'b1, bits[k]};
      @(posedge clk); #1;
    end
    ui_in = 8'b0;
    @(posedge clk); #1;
    $display("uio_oe            = %08b (bit 0 driven)", uio_oe);
    $display("success           = %b", uio_out[0]);
    for (k = 0; k < 20; k = k + 1) begin
      if (uio_out[0] && uo_out != 8'h00) begin
        msg = (msg << 8) | uo_out;
        nchar = nchar + 1;
      end
      @(posedge clk); #1;
    end
    $display("message (%0d bytes) = \"%0s\"", nchar, msg);
    if (uio_out[0] !== 1'b1) $display("FAIL: success not asserted");
    $finish;
  end
endmodule
`default_nettype wire
