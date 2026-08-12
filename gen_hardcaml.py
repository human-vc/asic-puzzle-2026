"""Emit a Hardcaml (OCaml) implementation of the recovered chip.

Same source of truth as gen_rtl.py: the region table and the message come from
what was recovered from the layout. Hardcaml writes Verilog, so the result goes
through the identical yosys miter against the netlist extracted from puzzle.gds.
"""
import os

from recovered import REGION_CELLS as REGIONS

N = 11
from recovered import MESSAGE as STRING
OUT = "hardcaml"


def main():
    os.makedirs(os.path.join(OUT, "bin"), exist_ok=True)
    grid = [REGIONS[r * N:(r + 1) * N] for r in range(N)]
    letters = sorted({ch for row in grid for ch in row})
    idx = {ch: i for i, ch in enumerate(letters)}

    rows = []
    for r in range(N):
        vals = "; ".join("k 4 %d" % idx[grid[r][c]] for c in range(N))
        rows.append("      [ %s ]  (* row %-2d *)" % (vals, r))
    region_rows = ";\n".join(rows)

    msg = "; ".join("k 8 0x%02x" % ord(c) for c in STRING)

    ml = f'''(* The Jane Street 2026 ASIC puzzle chip, recovered from its layout and
   written in Hardcaml.

   The design reads an 11x11 grid as 121 serial bits and reports whether it is a
   valid two-star Star Battle solution: two stars in every row, column and
   region, none of them touching. It then streams a message out of [o].

   The structure follows the silicon: a mod-11 column counter and a mod-11 row
   counter, a 12-deep history of the input supplying the three neighbours in the
   row above, one row tally reused every row, and eleven column and eleven
   region tallies that persist to the end. *)

open! Base
open Hardcaml
open Signal

let n = {N}
let k w v = of_int ~width:w v

(* Region of each cell, recovered by probing the accumulators of the real chip. *)
let region_rom =
  [
{region_rows}
  ]
;;

let message = [ {msg} ]

let create ~clock ~reset ~enable ~i =
  let spec = Reg_spec.create ~clock ~reset () in
  let done_w = wire 1 in
  let col_w = wire 4 in
  let row_w = wire 4 in
  let bad_w = wire 1 in
  let armed_w = wire 1 in
  let hist_w = wire 12 in
  let rowcnt_w = wire 2 in
  let success_w = wire 1 in
  let oidx_w = wire 4 in
  let step = enable &: ~:done_w in
  let last_col = col_w ==:. (n - 1) in
  let last_row = row_w ==:. (n - 1) in
  let star = step &: i in
  let finish = step &: last_col &: last_row in
  (* sequencing *)
  col_w <== reg spec ~enable:step (mux2 last_col (k 4 0) (col_w +:. 1));
  row_w <== reg spec ~enable:(step &: last_col) (mux2 last_row (k 4 0) (row_w +:. 1));
  done_w <== reg spec ~enable:finish vdd;
  (* the neighbours: hist.(0) is the cell to the left, 9/10/11 the row above *)
  hist_w <== reg spec ~enable:step (concat_msb [ select hist_w 10 0; i ]);
  let left = bit hist_w 0 &: (col_w <>:. 0) in
  let up_right = bit hist_w 9 &: (row_w <>:. 0) &: (col_w <>:. (n - 1)) in
  let up = bit hist_w 10 &: (row_w <>:. 0) in
  let up_left = bit hist_w 11 &: (row_w <>:. 0) &: (col_w <>:. 0) in
  let touching = star &: (left |: up |: up_left |: up_right) in
  (* tallies: two bits, saturating at three *)
  let bump v inc = mux2 inc (mux2 (v ==:. 3) v (v +:. 1)) v in
  let regid =
    mux row_w (List.map region_rom ~f:(fun r -> mux col_w r))
  in
  let rowcnt_next = bump rowcnt_w star in
  rowcnt_w <== reg spec ~enable:step (mux2 last_col (k 2 0) rowcnt_next);
  let row_bad = step &: last_col &: (rowcnt_next <>:. 2) in
  let tally sel =
    List.init n ~f:(fun j ->
      let w = wire 2 in
      let next = bump w (star &: sel j) in
      w <== reg spec ~enable:step next;
      next)
  in
  let col_next = tally (fun j -> col_w ==:. j) in
  let reg_next = tally (fun j -> regid ==:. j) in
  let all_two =
    List.fold (col_next @ reg_next) ~init:vdd ~f:(fun acc c -> acc &: (c ==:. 2))
  in
  bad_w <== reg spec ~enable:step (bad_w |: touching |: row_bad);
  let ok = all_two &: ~:bad_w &: ~:row_bad &: ~:touching in
  (* the verdict is registered one cycle after the last cell, as in the silicon *)
  let arm = step &: finish in
  let fire = ~:step &: armed_w in
  armed_w <== reg spec ~enable:(arm |: fire) arm;
  let ok_q = reg spec ~enable:arm ok in
  success_w <== reg spec ~enable:fire ok_q;
  (* output generator: starts when success rises, one byte per clock *)
  let sending = success_w &: (oidx_w <>:. List.length message) in
  oidx_w <== reg spec ~enable:sending (oidx_w +:. 1);
  let o = mux2 sending (mux oidx_w (message @ [ k 8 0 ])) (k 8 0) in
  o, success_w
;;

let circuit () =
  let clock = input "clk" 1 in
  let reset = input "reset" 1 in
  let enable = input "enable" 1 in
  let i = input "i" 1 in
  let o, success = create ~clock ~reset ~enable ~i in
  Circuit.create_exn ~name:"starbattle" [ output "o" o; output "success" success ]
;;
'''

    main_ml = '''open! Base
open Hardcaml
open Stdio

let () =
  let circuit = Starbattle.circuit () in
  match Sys.get_argv () |> Array.to_list with
  | _ :: "verilog" :: _ -> Rtl.print Verilog circuit
  | _ ->
    let bits =
      In_channel.read_all "solution_bits.txt"
      |> String.strip
      |> String.to_list
      |> List.map ~f:(fun c -> Char.equal c '1')
    in
    let sim = Cyclesim.create circuit in
    let port name = Cyclesim.in_port sim name in
    let out name = Cyclesim.out_port sim name in
    let reset = port "reset" and enable = port "enable" and i = port "i" in
    let o = out "o" and success = out "success" in
    let step () = Cyclesim.cycle sim in
    reset := Bits.vdd;
    enable := Bits.gnd;
    i := Bits.gnd;
    step ();
    step ();
    reset := Bits.gnd;
    enable := Bits.vdd;
    List.iter bits ~f:(fun b ->
      i := (if b then Bits.vdd else Bits.gnd);
      step ());
    i := Bits.gnd;
    step ();
    printf "success = %d\\n" (Bits.to_int !success);
    let buf = Buffer.create 32 in
    for _ = 1 to 20 do
      let v = Bits.to_int !o in
      if Bits.to_int !success = 1 && v <> 0 then Buffer.add_char buf (Char.of_int_exn v);
      step ()
    done;
    printf "message = %S\\n" (Buffer.contents buf)
;;
'''

    open(os.path.join(OUT, "starbattle.ml"), "w").write(ml)
    open(os.path.join(OUT, "main.ml"), "w").write(main_ml)
    open(os.path.join(OUT, "dune-project"), "w").write("(lang dune 3.0)\n")
    open(os.path.join(OUT, "dune"), "w").write(
        "(executable\n (name main)\n (modules main starbattle)\n"
        " (libraries base stdio hardcaml))\n")
    print("wrote %s/{starbattle.ml,main.ml,dune,dune-project}" % OUT)


if __name__ == "__main__":
    main()
