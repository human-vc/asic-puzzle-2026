open! Base
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
    printf "success = %d\n" (Bits.to_int !success);
    let buf = Buffer.create 32 in
    for _ = 1 to 20 do
      let v = Bits.to_int !o in
      if Bits.to_int !success = 1 && v <> 0 then Buffer.add_char buf (Char.of_int_exn v);
      step ()
    done;
    printf "message = %S\n" (Buffer.contents buf)
;;
