#!/usr/bin/env python3
"""Generate the WLED 2D ledmap for the catears from the KiCad LED grids.

Reads the LED footprints of pcb_a_rev3 / pcb_b_rev3, follows the DIN->DOUT
nets from LED_IN to recover the real chain order, snaps each LED to the 2 mm
grid (User.4 layer) and writes a ledmap.json with an explicit "map".

Segment layout (pin -> start): 0 Front right (A) @0, 1 Front left (B) @290,
2 Back left (B) @580, 3 Back right (A) @870, band (78) @1160.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "electronics"
PITCH = 2.0
Y0 = 71.415                       # first grid row (User.4)
X0 = {"a": 149.15, "b": 150.15}   # first grid column per board (User.4)
PANEL_W, PANEL_H = 22, 25
# left -> right order of the panels in the matrix: (board, physical start, mirror)
# front pair is mirrored (seen from the LED side), back pair is flipped again so its text reads correctly
PANELS = [("a", 0, True), ("b", 290, True), ("b", 580, False), ("a", 870, False)]
BAND_START, BAND_LEN = 1160, 78
TOTAL = 1238


def load(board):
    t = (ROOT / f"pcb_{board}_rev3" / f"pcb_{board}_rev3.kicad_pcb").read_text(encoding="utf8")
    leds = []
    for p in t.split("\n\t(footprint ")[1:]:
        if not p.startswith('"LED_SMD_3D:XL-1010RGBC"'):
            continue
        at = re.search(r"\n\t\t\(at ([\d.-]+) ([\d.-]+)", p)
        net = lambda f: re.search(r'\(net \d+ "([^"]*)"\)\s*\(pinfunction "%s"' % f, p).group(1)
        leds.append(dict(x=float(at.group(1)), y=float(at.group(2)), din=net("DIN"), dout=net("DOUT")))
    by_din = {l["din"]: l for l in leds}
    cur, seq = by_din["LED_IN"], []
    while cur:
        seq.append(cur)
        cur = by_din.get(cur["dout"])
    assert len(seq) == len(leds) == 290, (board, len(seq), len(leds))
    return seq


def panel_cells(board, mirror):
    cells = []
    for l in load(board):
        c = round((l["x"] - X0[board]) / PITCH)
        r = round((l["y"] - Y0) / PITCH)
        assert 0 <= c < PANEL_W and 0 <= r < PANEL_H
        cells.append((PANEL_W - 1 - c if mirror else c, r))
    assert len(set(cells)) == 290
    return cells


def main():
    width = PANEL_W * len(PANELS)
    height = PANEL_H + 1          # extra bottom row for the band
    grid = [-1] * (width * height)
    cache = {(b, m): panel_cells(b, m) for b in "ab" for m in (True, False)}
    for p, (board, start, mirror) in enumerate(PANELS):
        for i, (c, r) in enumerate(cache[(board, mirror)]):
            grid[r * width + p * PANEL_W + c] = start + i
    for i in range(BAND_LEN):
        grid[PANEL_H * width + i] = BAND_START + i
    used = [v for v in grid if v >= 0]
    assert sorted(used) == list(range(TOTAL)), "every LED must be mapped exactly once"
    out = Path(__file__).with_name("2d_ledmap.json")
    out.write_text(json.dumps({"n": "Catears 2D", "width": width, "height": height, "map": grid}) + "\n")
    for r in range(height):
        print("".join("#" if grid[r * width + x] >= 0 else "." for x in range(width)))
    print(f"wrote {out} ({width}x{height})")


if __name__ == "__main__":
    sys.exit(main())
