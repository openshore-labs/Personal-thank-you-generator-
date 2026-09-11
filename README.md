# Thank-you GIF generator

Builds an animated GIF from photos of your actual thank-you card + envelope:
the envelope (addressed in your handwriting) turns around, its flap opens,
the card is pulled up out of it, and the cover lifts away to reveal your
handwritten note underneath. The note and the address are supplied as photos
of real handwriting; the ink is lifted off the paper and written onto the
card / envelope so it reads as penned there. Everything is cut out of its
maroon-leather reference photo and sits flat on a plain white background.

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

- `assets/source/` -- the five reference photos (envelope front, envelope
  back/flap-closed, envelope flap-open, card cover, card open blank) this
  whole pipeline is built from.
- `thankyou_gif/config.py` -- every tunable number: measured bounding boxes,
  the ink-extraction params, where the note and address get written, canvas
  size, and per-stage timing. Start here to adjust anything.
- `thankyou_gif/imaging.py` -- generic helpers: cutting an object out of its
  leather photo onto a transparent background (`extract_object`), the
  pivoted "flip" transition used for the envelope turning around (squash on
  the x-axis) and the flap opening, and the card-specific choreography
  (`card_pull`, `card_unfold`, below).
- `thankyou_gif/compositing.py` -- lifts the ink off a handwriting photo
  (`extract_ink`) and writes it to scale onto the card (`write_note`) or
  envelope (`write_address`).
- `thankyou_gif/stages.py` -- assembles the full ordered sequence (see
  below) into one frame list.
- `thankyou_gif/pipeline.py` -- quantizes and writes the GIF.

## The animation sequence

1. Hold on the envelope front (addressed).
2. Envelope turns around (front -> back).
3. Hold on the envelope back (flap closed, PAPYRUS).
4. Flap opens -- a real photo of the envelope with its flap lifted
   (`envelope_open.jpg`). The envelope stages are bottom-aligned
   (`ENVELOPE_BOTTOM_Y_FRAC`), so the taller open envelope grows upward from
   the same base edge and the flap reads as lifting rather than the whole
   thing jumping.
5. Hold on the opened envelope (grey liner, mouth open).
6. Card is pulled straight up out of the envelope's mouth -- the envelope
   itself doesn't move (`imaging.card_pull`). The rising card is clipped at
   the envelope's fixed mouth line, so the part still tucked inside stays
   hidden behind the envelope's own front-pocket wall until it clears it: a
   real "pulled from the pocket" motion, not a slide up the screen.
7. Once clear, the card drifts down to its resting spot as the (now empty)
   envelope fades away to white.
8. Hold on the closed card cover ("THANK YOU").
9. Card unfolds (`imaging.card_unfold`) -- not a texture-swap flip. The cover
   foreshortens away (top-anchored at the fold/hinge) revealing the note
   underneath, which was there the whole time just hidden beneath it,
   starting from its free (bottom) edge -- the physically correct order for
   a top-hinged lid lifting off, viewed from directly above. Then the
   (blank) interior of the lid grows in above the fold to complete the open
   card, as if it settled open after a full rotation.
10. Hold on the finished card with the note.

## Calibration

```
python calibrate.py
```

Writes PNGs to `output/calibration/` with the measured object bboxes and the
note / address write-rectangles drawn on top of the actual source photos --
check these any time you edit `config.py`, before spending time on a full
render. `card_write_rect.png` and `envelope_address_rect.png` show exactly
where the handwriting will be fit and centered (`CARD_WRITE_RECT_FRAC` /
`ENVELOPE_ADDRESS_RECT_FRAC` in config.py).

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
- **Size:** current defaults produce roughly a 4 MB file for the full
  10-stage sequence at 544x765 (about 6 MB "on the wire" after email base64
  encoding) -- comfortably under every consumer and corporate mail cap. A
  plain white background compresses far better under GIF's palette+LZW than
  the photographed leather did, so there's a lot of headroom; the biggest
  remaining levers are `CANVAS_SIZE` and the transition frame counts in
  `TIMING` if you want to push detail further.

## Look / realism

- **Everything sits flat on plain white**, cut out of its maroon-leather
  reference photo. `imaging.extract_object` separates the bright paper from
  the dark leather by luminance threshold, fills interior holes (so dark ink
  strokes inside the card stay opaque), keeps only the largest connected
  piece, and erodes the mask a touch to shed the thin leather fringe right at
  the edge (`OBJECT_MASK_*` in config.py). No background texture, no contact
  shadow -- a clean product-shot look, by design.
- **The card is pulled from the envelope, not slid up the screen**
  (`imaging.card_pull`): the envelope stays fixed and the rising card is
  clipped at its fixed mouth line, so it's genuinely occluded by the
  envelope's own pocket wall until it clears it.
- **The card unfolds instead of flipping** (`imaging.card_unfold`): the cover
  foreshortens away to reveal the note that was hidden beneath it the whole
  time, rather than doing an instant texture swap when a squash reaches zero.
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
- **Foreshortening shear on the envelope flips is built but shipped off**
  (`FLIP_SHEAR = 0` in config.py). It adds a subtle 3D skew to the envelope
  turn and flap open, but its peak lands where the object is edge-on (a thin
  strip, so it's barely visible), while costing file size. Set a small value
  like `0.06` to turn it on -- it's tested and alpha-correct.

## Tuning the handwriting

If the ink extraction leaves faint ghosts or drops light strokes on a new
handwriting photo, adjust `INK_*` in config.py: raise `INK_FLOOR` / `INK_CUTOFF`
to suppress more of the paper and embossing, lower them (or raise `INK_GAIN`)
to keep more of a light-pen stroke. To reposition or resize the writing, edit
`CARD_WRITE_RECT_FRAC` / `ENVELOPE_ADDRESS_RECT_FRAC` (and the `*_ALIGN`
settings) and check `calibrate.py`'s `card_write_rect.png` /
`envelope_address_rect.png` before a full render.
