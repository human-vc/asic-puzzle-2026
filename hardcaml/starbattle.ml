

open! Base
open Hardcaml
open Signal

let n = 11
let k w v = of_int ~width:w v

let region_rom =
  [
      [ k 4 0; k 4 0; k 4 0; k 4 0; k 4 0; k 4 2; k 4 2; k 4 6; k 4 9; k 4 9; k 4 8 ]  ;
      [ k 4 0; k 4 0; k 4 3; k 4 0; k 4 0; k 4 2; k 4 6; k 4 6; k 4 9; k 4 9; k 4 8 ]  ;
      [ k 4 0; k 4 0; k 4 3; k 4 2; k 4 2; k 4 2; k 4 2; k 4 6; k 4 6; k 4 9; k 4 8 ]  ;
      [ k 4 0; k 4 0; k 4 3; k 4 2; k 4 1; k 4 1; k 4 1; k 4 8; k 4 6; k 4 6; k 4 8 ]  ;
      [ k 4 3; k 4 0; k 4 3; k 4 2; k 4 1; k 4 8; k 4 8; k 4 8; k 4 8; k 4 8; k 4 8 ]  ;
      [ k 4 3; k 4 3; k 4 3; k 4 2; k 4 1; k 4 1; k 4 1; k 4 8; k 4 10; k 4 10; k 4 10 ]  ;
      [ k 4 2; k 4 2; k 4 2; k 4 2; k 4 2; k 4 2; k 4 1; k 4 8; k 4 10; k 4 7; k 4 7 ]  ;
      [ k 4 2; k 4 5; k 4 5; k 4 5; k 4 1; k 4 1; k 4 1; k 4 8; k 4 10; k 4 7; k 4 7 ]  ;
      [ k 4 2; k 4 5; k 4 5; k 4 4; k 4 8; k 4 8; k 4 8; k 4 8; k 4 10; k 4 7; k 4 7 ]  ;
      [ k 4 2; k 4 2; k 4 5; k 4 4; k 4 4; k 4 8; k 4 8; k 4 8; k 4 10; k 4 10; k 4 10 ]  ;
      [ k 4 2; k 4 5; k 4 5; k 4 4; k 4 8; k 4 8; k 4 8; k 4 8; k 4 8; k 4 8; k 4 8 ]
  ]
;;

let message = [ k 8 0x28; k 8 0x2a; k 8 0x20; k 8 0x54; k 8 0x57; k 8 0x4f; k 8 0x20; k 8 0x53; k 8 0x54; k 8 0x41; k 8 0x52; k 8 0x53; k 8 0x20; k 8 0x2a; k 8 0x29 ]

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

  col_w <== reg spec ~enable:step (mux2 last_col (k 4 0) (col_w +:. 1));
  row_w <== reg spec ~enable:(step &: last_col) (mux2 last_row (k 4 0) (row_w +:. 1));
  done_w <== reg spec ~enable:finish vdd;

  hist_w <== reg spec ~enable:step (concat_msb [ select hist_w 10 0; i ]);
  let left = bit hist_w 0 &: (col_w <>:. 0) in
  let up_right = bit hist_w 9 &: (row_w <>:. 0) &: (col_w <>:. (n - 1)) in
  let up = bit hist_w 10 &: (row_w <>:. 0) in
  let up_left = bit hist_w 11 &: (row_w <>:. 0) &: (col_w <>:. 0) in
  let touching = star &: (left |: up |: up_left |: up_right) in

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

  let arm = step &: finish in
  let fire = ~:step &: armed_w in
  armed_w <== reg spec ~enable:(arm |: fire) arm;
  let ok_q = reg spec ~enable:arm ok in
  success_w <== reg spec ~enable:fire ok_q;

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
