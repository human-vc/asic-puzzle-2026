`timescale 1ns / 1ps
`default_nettype none

module tb;
  reg clk = 0, rst_n = 0, enable = 0, I = 0;
  wire [7:0] O;
  wire success;
  integer k, fd, ch, nchar = 0;
  reg [120:0] bits;
  reg [8*32-1:0] str;

  puzzle dut (.clk(clk), .rst_n(rst_n), .enable(enable), .I(I),
              .O(O), .success(success));

  always #5 clk = ~clk;

  initial begin
    fd = $fopen("solution_bits.txt", "r");
    for (k = 0; k < 121; k = k + 1) begin
      ch = $fgetc(fd);
      bits[k] = (ch == "1");
    end
    $fclose(fd);

    repeat (3) @(posedge clk);
    #1 rst_n = 1; enable = 1;
    for (k = 0; k < 121; k = k + 1) begin
      I = bits[k];
      @(posedge clk);
      #1;
    end
    I = 0;
    $display("success right after last bit : %b", success);
    @(posedge clk); #1;
    $display("success one cycle later      : %b", success);

    for (k = 0; k < 24; k = k + 1) begin
      if (success && O != 8'h00) begin
        str = (str << 8) | O;
        nchar = nchar + 1;
      end
      @(posedge clk); #1;
    end
    $display("output string                : \"%0s\"", str);
    $finish;
  end
endmodule
`default_nettype wire
