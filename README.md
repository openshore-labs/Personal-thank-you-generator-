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

## GIF size

`CANVAS_SIZE` and `GIF_COLORS` in config.py trade quality for file size --
GIF's palette + LZW compression is unkind to photographic texture (paper
grain, soft lighting). Current defaults land around 3-4 MB for the full
9-stage sequence; push `CANVAS_SIZE` up if you want more detail and don't
mind a bigger file.
