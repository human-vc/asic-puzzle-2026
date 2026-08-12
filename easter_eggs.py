"""Recover the hidden messages in the puzzle files.

1. Morse spelled by the 36 anonymized placeholder cells below the cell array.
2. ASCII hidden in the stimulus of example_inputs.vcd.
"""
import klayout.db as db

from vcd_io import read_vcd, sampled_inputs

MORSE = {'.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F', '--.': 'G',
         '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N',
         '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T', '..-': 'U',
         '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y', '--..': 'Z'}


def morse_below_die(gds="puzzle.gds"):
    ly = db.Layout()
    ly.read(gds)
    top = ly.top_cell()
    marks = sorted((i.bbox().left * ly.dbu, i.bbox().width() * ly.dbu)
                   for i in top.each_inst() if i.bbox().top * ly.dbu < 0.01)
    unit = min(w for _, w in marks)
    out, cur = [], ""
    for k, (x, w) in enumerate(marks):
        cur += "." if w < 2 * unit else "-"
        if k + 1 < len(marks):
            gap = marks[k + 1][0] - (x + w)
            if gap > 6 * unit:
                out += [MORSE[cur], " "]
                cur = ""
            elif gap > 2 * unit:
                out.append(MORSE[cur])
                cur = ""
    out.append(MORSE[cur])
    return "".join(out)


def hidden_in_stimulus(vcd="example_inputs.vcd"):
    bits = [s[3] for s in sampled_inputs(read_vcd(vcd)) if s[2] == 1]
    msg = ""
    for g in range(len(bits) // 121):
        grid = bits[g * 121:(g + 1) * 121]
        for r in range(11):
            row = grid[r * 11:(r + 1) * 11]
            msg += chr(sum(row[c] << c for c in range(7)))
    return msg


if __name__ == "__main__":
    print("morse below the die:   %r" % morse_below_die())
    print("hidden in the stimulus: %r" % hidden_in_stimulus())
