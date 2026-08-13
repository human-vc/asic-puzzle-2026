"""Score the independently derived floorplan against Jane Street's hint image.

`layout.png` ships with the puzzle and boxes one region labelled "output
generator". The box is measured off the image rather than eyeballed: the die
outline in the render is a known 200 x 300 um rectangle, which fixes the
pixel-to-micron scale in both axes, and the box border is the only pure-black
rectangle in the frame.

The floorplan in blocks.json was derived from cone membership and per-net
probing, with no reference to this image. Counting how much of the block called
"output generator" lands inside their box is therefore a test of that
derivation, not an input to it.
"""
import json

import numpy as np
from PIL import Image

from sim import Design
from recovered import OUT_INDEX, OUT_LFSR

BLOCK = "output generator"
DIE_W_UM = 200.0
DIE_H_UM = 300.0


def measure_png(path="layout.png"):
    im = np.array(Image.open(path).convert("RGB")).astype(int)

    grey = (abs(im[:, :, 0] - im[:, :, 1]) < 6) & (abs(im[:, :, 1] - im[:, :, 2]) < 6)
    outline = grey & (im[:, :, 0] > 140) & (im[:, :, 0] < 225)
    rows = np.flatnonzero(outline.sum(axis=1) > 400)
    cols = np.flatnonzero(outline.sum(axis=0) > 300)
    die_top, die_bot = rows.min(), rows.max()
    die_right = cols.max()
    mid = im[(die_top + die_bot) // 2]
    die_left = next(x for x in range(im.shape[1]) if mid[x].max() < 200)

    dark = im.max(axis=2) < 60
    brows = np.flatnonzero(dark.sum(axis=1) > 100)
    bcols = np.flatnonzero(dark.sum(axis=0) > 200)

    sx = DIE_W_UM / (die_right - die_left)
    sy = DIE_H_UM / (die_bot - die_top)
    return {
        "scale_x_um_per_px": sx,
        "scale_y_um_per_px": sy,
        "box": (
            (bcols.min() - die_left) * sx,
            (die_bot - brows.max()) * sy,
            (bcols.max() - die_left) * sx,
            (die_bot - brows.min()) * sy,
        ),
    }


def inside(cell, box, frac=0.999):
    """cell counts as inside if at least `frac` of its area is in the box.

    The default is whole-cell containment; 0.999 rather than 1.0 only because
    the overlap is computed in floating point. The count is not sensitive to
    this: every cell in the block is either wholly inside or wholly outside.
    """
    x0, y0, x1, y1 = box
    ox = max(0.0, min(cell["x"] + cell["w"], x1) - max(cell["x"], x0))
    oy = max(0.0, min(cell["y"] + cell["h"], y1) - max(cell["y"], y0))
    return ox * oy >= frac * cell["w"] * cell["h"]


def main():
    m = measure_png()
    box = m["box"]
    print("die outline scale: %.5f um/px in x, %.5f um/px in y  (agree to %.2f%%)"
          % (m["scale_x_um_per_px"], m["scale_y_um_per_px"],
             100 * abs(m["scale_x_um_per_px"] / m["scale_y_um_per_px"] - 1)))
    print("their box, in die coordinates: x %.1f - %.1f um,  y %.1f - %.1f um"
          % (box[0], box[2], box[1], box[3]))

    bl = json.load(open("blocks.json"))
    cells = {c["name"]: c for c in bl["cells"]}

    ours = [c for c in bl["cells"] if c["block"] == BLOCK]
    hit = [c for c in ours if inside(c, box)]
    print()
    print("cells we attribute to the %r block: %d" % (BLOCK, len(ours)))
    print("  of those, wholly inside their box: %d" % len(hit))
    for c in ours:
        if not inside(c, box):
            print("    outside: %s at (%.2f, %.2f)" % (c["name"], c["x"], c["y"]))

    d = Design("puzzle_net.json")
    gen_flops = set(OUT_INDEX + OUT_LFSR)
    ins, outs = 0, 0
    foreign = []
    for i, f in enumerate(d.flops):
        c = cells.get(f[5])
        if c is None:
            continue
        if i in gen_flops:
            ins += inside(c, box)
            outs += not inside(c, box)
        elif inside(c, box):
            foreign.append((i, f[5]))
    print("  its flip-flops inside their box: %d of %d" % (ins, ins + outs))
    print("  flip-flops from any other block inside their box: %d %s"
          % (len(foreign), [n for _i, n in foreign]))

    other = [c for c in bl["cells"]
             if c["block"] not in (BLOCK, "shared", "unassigned") and inside(c, box)]
    print("  non-shared cells from other blocks inside their box: %d" % len(other))


if __name__ == "__main__":
    main()
