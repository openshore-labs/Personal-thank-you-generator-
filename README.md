# Thank-you GIF generator

Builds an animated GIF from photos of your actual thank-you card + envelope:
the envelope (addressed in your handwriting) turns around, its flap opens, the
card slides out, and it opens to reveal your handwritten note. The note and the
address are supplied as photos of real handwriting; the ink is lifted off the
paper and written onto the card / envelope so it reads as penned there.

## Setup

```
pip install -r requirements.txt
```

## Usage

```
python generate_gif.py                                     # blank card + envelope
python generate_gif.py --note assets/notes/note_body.jpg   # note written into the card
python generate_gif.py --note assets/notes/note_body.jpg \
    --address assets/notes/envelope_address.jpg \
    --out output/for_natalie.gif                            # + address on the envelope
```

Drop handwriting photos into `assets/notes/` (git-ignored except for
`.gitkeep` -- these are one-off per recipient, and personal, so they're not
checked in). Shoot them straight-on on white-ish paper in even light; the ink
extraction (see below) handles the paper, shadows, and any embossed
show-through from previous pages. The note is fit to scale onto the card
interior (centered); the address is centered on the envelope front.

## How it's put together

- `assets/source/` -- the four reference photos (envelope front, envelope
  back/flap, card cover, card open blank) this whole pipeline is built from.
- `thankyou_gif/config.py` -- every tunable number: measured bounding boxes,
  the ink-extraction params, where the note and address get written, the flap
  triangle, canvas size, and per-stage timing. Start here to adjust anything.
- `thankyou_gif/imaging.py` -- generic helpers: cropping to a measured bbox,
  and the pivoted "flip" transition used both for the envelope turning
  around (squash on the x-axis) and the card opening (squash on the
  y-axis, hinged at the card's top edge since it's a top-fold card).
- `thankyou_gif/compositing.py` -- lifts the ink off a handwriting photo
  (`extract_ink`) and writes it to scale onto the card (`write_note`) or
  envelope (`write_address`); also patches the flap's triangle out of the
  envelope-back photo for the flap-open stage.
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
triangle, and the note / address write-rectangles drawn on top of the actual
source photos -- check these any time you edit `config.py`, before spending
time on a full render. `card_write_rect.png` and `envelope_address_rect.png`
show exactly where the handwriting will be fit and centered
(`CARD_WRITE_RECT_FRAC` / `ENVELOPE_ADDRESS_RECT_FRAC` in config.py).

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
- **The handwriting reads as real ink on the card / envelope paper**, not a
  pasted photo of a sheet. `compositing.extract_ink` lifts just the pen strokes
  off the handwriting photo (dividing out the paper, lighting, and any embossed
  show-through), so when it's written on, the card's and envelope's own paper
  grain shows through the strokes. `INK_*` in config.py tune the extraction.
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

## Tuning the handwriting

If the ink extraction leaves faint ghosts or drops light strokes on a new
handwriting photo, adjust `INK_*` in config.py: raise `INK_FLOOR` / `INK_CUTOFF`
to suppress more of the paper and embossing, lower them (or raise `INK_GAIN`)
to keep more of a light-pen stroke. To reposition or resize the writing, edit
`CARD_WRITE_RECT_FRAC` / `ENVELOPE_ADDRESS_RECT_FRAC` (and the `*_ALIGN`
settings) and check `calibrate.py`'s `card_write_rect.png` /
`envelope_address_rect.png` before a full render.
