# Thank-you GIF generator

Builds an animated GIF from photos of your actual thank-you card + envelope:
the envelope turns around, its flap opens, the card slides out, and it opens
to reveal a handwritten note photo composited into the blank interior.

## Setup

```
pip install -r requirements.txt
```

## Usage

```
python generate_gif.py                                    # blank interior, no note
python generate_gif.py --note assets/notes/my_note.jpg     # with a handwritten note
python generate_gif.py --note assets/notes/my_note.jpg --out output/for_alex.gif
```

Drop handwritten-note photos into `assets/notes/` (git-ignored except for
`.gitkeep` -- these are one-off per recipient, not checked in). Shoot the
note straight-on, similar lighting to the source card photos, and it'll get
perspective-warped into the card's bottom-half panel.

## How it's put together

- `assets/source/` -- the four reference photos (envelope front, envelope
  back/flap, card cover, card open blank) this whole pipeline is built from.
- `thankyou_gif/config.py` -- every tunable number: measured bounding boxes,
  the note-placement quad, the flap triangle, canvas size, and per-stage
  timing. Start here when something needs adjusting.
- `thankyou_gif/imaging.py` -- generic helpers: cropping to a measured bbox,
  and the pivoted "flip" transition used both for the envelope turning
  around (squash on the x-axis) and the card opening (squash on the
  y-axis, hinged at the card's top edge since it's a top-fold card).
- `thankyou_gif/compositing.py` -- the two pieces of real photo compositing:
  perspective-warping a note photo into the card, and patching the flap's
  triangle out of the envelope-back photo.
- `thankyou_gif/stages.py` -- assembles the full ordered sequence (see
  below) into one frame list.
- `thankyou_gif/pipeline.py` -- quantizes and writes the GIF.

## The animation sequence

1. Hold on the envelope front.
2. Envelope turns around (front -> back).
3. Hold on the envelope back.
4. Flap opens.
5. Hold on the opened envelope.
6. Card slides up out of the envelope.
7. Hold on the closed card cover ("THANK YOU").
8. Card opens (hinged at its top edge -- it's a top-fold card, confirmed
   from the fold line in the blank open-card photo sitting at ~50% down a
   portrait sheet, which folds into a landscape closed card).
9. Hold on the finished card with the note.

## Calibration

```
python calibrate.py
```

Writes PNGs to `output/calibration/` with the measured bboxes, the flap
triangle, and the note quad drawn on top of the actual source photos --
check these any time you edit `config.py`, before spending time on a full
render. `note_quad.png` is the one worth double-checking most: it's an
axis-aligned rectangle in the bottom half of the card by default, but
`NOTE_QUAD_FRAC` in config.py holds 4 independent corners, so you can true
up perspective there if a note ever looks skewed once composited.

## Known placeholder: the flap-open fill

There's no reference photo of the envelope with its flap actually lifted,
so `compositing.envelope_with_flap_removed()` fakes it: it patches the
flap's triangle out with a flat color sampled from the envelope's own blank
panel, inflated and heavily blurred so it fully covers the flap's thin grey
printed border even though `FLAP_TRIANGLE_FRAC` in config.py was eyeballed
off a photo rather than precisely detected. It looks fine in motion (the
transition is fast) but is visibly soft/faded if you pause on that frame.
Two ways to improve it later, either works with the existing pivot machinery
in `imaging.flip_transition`:

- Take an actual photo of the envelope with the flap lifted open, drop it
  in as a fifth source asset, and swap it in for `envelope_open_src` in
  `stages.py` instead of the synthesized fill.
- Refine `FLAP_TRIANGLE_FRAC` against a higher-precision edge trace, then
  reduce the inflate/blur in `envelope_with_flap_removed`.

## Playback, delivery, and size

- **Plays once, then freezes on the final open-card still** -- no looping.
  This is done by omitting the loop directive entirely when writing the GIF
  (`config.LOOP = None`), which per the GIF spec plays through once and holds
  the last frame.
- **Built to be a plain email attachment** on desktop and mobile. Attach the
  `.gif` file itself (don't paste it inline into the message body): a plain
  attachment opens in the recipient's own image viewer, which animates
  everywhere (Apple Mail, Gmail, Outlook, iCloud, Yahoo, on both desktop and
  phone). The one caveat worth knowing -- Outlook for Windows freezes GIFs
  that are *embedded inline* in an HTML message body to their first frame --
  only applies to inline embedding, not to an attached file.
- **Size:** current defaults produce roughly an 8 MB file for the full
  9-stage sequence at 640x900 (about 11 MB "on the wire" after email base64
  encoding) -- comfortably under every consumer mail cap (Gmail 25 MB,
  iCloud/Outlook ~20 MB). If you ever need it smaller, drop `CANVAS_SIZE` or
  `GIF_COLORS` in config.py; if you want more detail and don't mind a bigger
  file, raise `CANVAS_SIZE`.

## Look / realism

- **Objects sit on real leather, not a flat color.** `background.py` samples
  a clean, object-free leather band out of a source photo
  (`LEATHER_SAMPLE_*` in config.py), tiles and vignettes it to canvas size,
  and every frame is composited over that. Object crops are feathered into it
  (`PASTE_FEATHER_PX`) so their edges dissolve into the leather instead of
  ending at a hard rectangle.
- **Everything is grounded with a soft contact shadow** (`OBJECT_SHADOW_*`
  in config.py, drawn in `imaging._draw_contact_shadow`) so objects rest on
  the leather rather than looking stamped on. During the flip transitions the
  shadow fades with the object's squash factor, so it matches the neighbouring
  holds exactly and never pops.
- **The composited note reads as ink on the card's own paper**, not a pasted
  rectangle (`compositing.composite_note`, `NOTE_*` in config.py): its paper
  tone is gain-shifted toward the card's blank-panel tone (`NOTE_EXPOSURE_MATCH`),
  it carries the card's own paper grain (`NOTE_GRAIN_STRENGTH`), and it casts
  a soft contact shadow (`NOTE_SHADOW_STRENGTH`). See the note about that
  shadow knob under "when real notes arrive" below.
- **One shared GIF palette** for the whole animation (`pipeline._shared_palette`),
  derived from frames sampled across the sequence, rather than a separate
  palette per frame -- the latter makes the photographed grain shimmer
  frame-to-frame. Dithering is off for the same reason (and it roughly
  halves the file size).
- **Foreshortening shear on the flips is built but shipped off**
  (`FLIP_SHEAR = 0` in config.py). It adds a subtle 3D skew to the envelope
  turn and card open, but its peak lands where the object is edge-on (a thin
  strip, so it's barely visible), while costing ~1.5 MB and pushing the file
  toward email size caps. Set a small value like `0.06` to turn it on -- it's
  tested and alpha-correct.

## When real handwritten-note photos arrive

The note-realism pipeline above (exposure-match, grain, contact shadow) is in
and validated against a placeholder, but two things are worth doing once real
notes are in hand:

1. **Set `NOTE_SHADOW_STRENGTH` to match the note format.** If your note is a
   separate slip of paper tucked into the card, keep or raise it (it sells the
   depth). If the writing is meant to read as ink directly on the card's own
   bottom-half paper, drop it toward 0 -- a full-rectangle shadow would make
   the note look like a separate sheet. The exposure-match and grain are wins
   either way.
2. **Check `note_quad.png` from `calibrate.py`** and true up `NOTE_QUAD_FRAC`
   if a real note looks skewed once composited (the quad has 4 independent
   corners for exactly this).
