import re
import sys
import pcbnew

VALUE_MATCH = "XL-1010"
PAD_DOUT    = 1
PAD_DIN     = 4
LAYER       = pcbnew.B_Cu
TRACK_WIDTH = pcbnew.FromMM(0.15)   # match your data-line net class width

board = pcbnew.GetBoard()


def ref_key(ref):
    m = re.search(r"(\d+)$", ref)
    return int(m.group(1)) if m else 0
 
 
leds = [fp for fp in board.GetFootprints() if VALUE_MATCH.lower() in fp.GetValue().lower()]
leds.sort(key=lambda fp: ref_key(fp.GetReference()))

print("Chain order:", [fp.GetReference() for fp in leds])

created = skipped = 0
for led_a, led_b in zip(leds, leds[1:]):
    pad_out = led_a.FindPadByNumber(PAD_DOUT)
    pad_in = led_b.FindPadByNumber(PAD_DIN)
    ra, rb = led_a.GetReference(), led_b.GetReference()
    if pad_out is None:
        print(f"  ! {ra}: no pad named '{PAD_DOUT}' -- skipping")
        skipped += 1
        continue
    
    if pad_in is None:
        print(f"  ! {rb}: no pad named '{PAD_DIN}' -- skipping")
        skipped += 1
        continue
    
    if pad_out.GetNetCode() != pad_in.GetNetCode():
        print(f"  ! {ra}.{PAD_DOUT} ('{pad_out.GetNetname()}') and "
              f"{rb}.{PAD_DIN} ('{pad_in.GetNetname()}') are different "
              f"nets -- wire them in schematic (or use a Net Tie) first. "
              f"Skipping.")
        skipped += 1
        continue

    track = pcbnew.PCB_TRACK(board)
    track.SetStart(pad_out.GetCenter())
    track.SetEnd(pad_in.GetCenter())
    track.SetWidth(TRACK_WIDTH)
    track.SetLayer(LAYER)
    track.SetNetCode(pad_out.GetNetCode())
    board.Add(track)
    created += 1
    print(f"  + {ra}.{PAD_DOUT} -> {rb}.{PAD_DIN}  (net '{pad_out.GetNetname()}')")


print(f"\n{created} track(s) created, {skipped} pair(s) skipped.")

pcbnew.Refresh()