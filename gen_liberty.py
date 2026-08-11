"""Build a minimal Liberty file for the cells this die uses.

Functions come from the SkyWater functional models (already verified
exhaustively); areas are measured off puzzle.gds itself. Enough for yosys+abc
to map the reconstructed RTL back onto the same cell set for a round trip.
"""
import json

import klayout.db as db

import cells as cells_mod

LIB_OPS = {"and": " * ", "or": " + ", "nand": " * ", "nor": " + ",
           "xor": " ^ ", "xnor": " ^ "}
NEG = {"nand", "nor", "xnor"}
SEQ = {"dfxtp": None, "dfrtp": "RESET_B", "dfstp": "SET_B"}


def lib_expr(cell):
    vals = {i: i for i in cell.inputs}
    pending = list(cell.ops)
    for _ in range(len(pending) + 2):
        rest, progressed = [], False
        for prim, out, ins in pending:
            if all(i in vals for i in ins):
                a = [vals[i] for i in ins]
                if prim == "buf":
                    e = a[0]
                elif prim == "not":
                    e = "!(%s)" % a[0]
                elif prim == "mux":
                    e = "((%s * !(%s)) + (%s * %s))" % (a[0], a[2], a[1], a[2])
                else:
                    e = "(%s)" % LIB_OPS[prim].join(a)
                    if prim in NEG:
                        e = "!%s" % e
                vals[out] = e
                progressed = True
            else:
                rest.append((prim, out, ins))
        pending = rest
        if not pending or not progressed:
            break
    return {o: vals.get(o) for o in cell.outputs}


def areas(gds="puzzle.gds"):
    ly = db.Layout()
    ly.read(gds)
    out = {}
    for c in ly.each_cell():
        if c.name.startswith("sky130"):
            bb = c.bbox()
            out[c.name] = bb.width() * ly.dbu * bb.height() * ly.dbu
    return out


HEADER = '''library (sky130_hd_measured) {
  technology (cmos);
  delay_model : table_lookup;
  time_unit : "1ns";
  voltage_unit : "1V";
  current_unit : "1mA";
  capacitive_load_unit (1, pf);
  pulling_resistance_unit : "1kohm";
  leakage_power_unit : "1nW";
  default_max_transition : 1.5;
  default_cell_leakage_power : 0.0;
  default_fanout_load : 1.0;
  default_inout_pin_cap : 0.005;
  default_input_pin_cap : 0.005;
  default_output_pin_cap : 0.0;
  nom_process : 1.0;
  nom_temperature : 25.0;
  nom_voltage : 1.8;

  lu_table_template (scalar) {
    variable_1 : input_net_transition;
    variable_2 : total_output_net_capacitance;
    index_1 ("0.0");
    index_2 ("0.0");
  }
'''

TIMING = '''        timing () {
          related_pin : "%s";%s
          cell_rise (scalar) { values("%0.3f"); }
          cell_fall (scalar) { values("%0.3f"); }
          rise_transition (scalar) { values("0.05"); }
          fall_transition (scalar) { values("0.05"); }
        }
'''


def main(out="sky130_hd_measured.lib"):
    lib = cells_mod.load_cells("pdk/functional")
    data = json.load(open("puzzle_net.json"))
    used = sorted({i["cell"] for i in data["instances"] if i["cell"].startswith("sky130")})
    ar = areas()

    text = [HEADER]
    n = 0
    for full in used:
        base = cells_mod.base_name(full)
        cell = lib[base]
        if cell.kind == "none" or base == "conb":
            continue  # tie cells: yosys emits constants directly
        area = ar.get(full, 5.0)
        text.append('  cell (%s) {\n    area : %0.3f;\n' % (full, area))
        if cell.kind in SEQ:
            ctrl = SEQ[cell.kind]
            clr = '\n      clear : "!%s";' % ctrl if ctrl == "RESET_B" else ""
            pre = '\n      preset : "!%s";' % ctrl if ctrl == "SET_B" else ""
            extra = ""
            if ctrl == "SET_B":
                extra = '\n      clear_preset_var1 : L;\n      clear_preset_var2 : L;'
            text.append('    ff (IQ, IQN) {\n      next_state : "D";\n'
                        '      clocked_on : "CLK";%s%s%s\n    }\n' % (clr, pre, extra))
            for p in cell.inputs:
                kind = "      clock : true;\n" if p == "CLK" else ""
                text.append('    pin (%s) {\n      direction : input;\n'
                            '      capacitance : 0.005;\n%s    }\n' % (p, kind))
            text.append('    pin (Q) {\n      direction : output;\n      function : "IQ";\n'
                        + TIMING % ("CLK", '\n          timing_type : rising_edge;', 0.2, 0.2)
                        + '    }\n')
        else:
            exprs = lib_expr(cell)
            for p in cell.inputs:
                text.append('    pin (%s) {\n      direction : input;\n'
                            '      capacitance : 0.005;\n    }\n' % p)
            for o, e in exprs.items():
                if e is None:
                    raise RuntimeError("no liberty expression for %s.%s" % (full, o))
                arcs = "".join(TIMING % (p, "", 0.1, 0.1) for p in cell.inputs)
                text.append('    pin (%s) {\n      direction : output;\n'
                            '      max_capacitance : 0.5;\n      function : "%s";\n%s    }\n'
                            % (o, e, arcs))
        text.append('  }\n')
        n += 1
    text.append("}\n")
    open(out, "w").write("".join(text))
    print("wrote %s: %d cells (areas measured from puzzle.gds)" % (out, n))


if __name__ == "__main__":
    main()
