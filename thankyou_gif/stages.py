"""Assembles the full ordered frame list for the thank-you GIF:

  1. hold on envelope front
  2. envelope turns around (front -> back)
  3. hold on envelope back
  4. flap opens (back w/ flap -> back w/ flap patched away)
  5. hold on opened envelope
  6. card slides up out of the envelope
  7. hold on closed card cover ("THANK YOU")
  8. card opens (cover -> full open card, hinged at its top edge)
  9. hold on the finished card with the handwritten note
"""

from PIL import Image

from . import compositing, config, imaging


def _fitted(img, name, target_width):
    return imaging.fit_width(imaging.crop_to_bbox(img, name), target_width)


def build_frames(note_path=None):
    envelope_front_src = imaging.load_source("envelope_front")
    envelope_back_src = imaging.load_source("envelope_back")
    card_cover_src = imaging.load_source("card_cover")
    card_open_src = imaging.load_source("card_open")

    if note_path:
        note_img = Image.open(note_path).convert("RGB")
        card_open_src = compositing.composite_note(card_open_src, note_img)

    envelope_open_src = compositing.envelope_with_flap_removed(envelope_back_src, envelope_front_src)

    ef = _fitted(envelope_front_src, "envelope_front", config.ENVELOPE_TARGET_WIDTH)
    eb = _fitted(envelope_back_src, "envelope_back", config.ENVELOPE_TARGET_WIDTH)
    eo = _fitted(envelope_open_src, "envelope_back", config.ENVELOPE_TARGET_WIDTH)
    cc = _fitted(card_cover_src, "card_cover", config.CARD_TARGET_WIDTH)
    co = _fitted(card_open_src, "card_open", config.CARD_TARGET_WIDTH)

    canvas_w, canvas_h = config.CANVAS_SIZE
    envelope_anchor = (canvas_w / 2, canvas_h * config.ENVELOPE_CENTER_Y_FRAC)
    hinge_y = canvas_h * config.CARD_HINGE_Y_FRAC
    card_cover_anchor = (canvas_w / 2, hinge_y + cc.height / 2)  # cover rests below the hinge

    frames = []

    n, ms = config.TIMING["hold_envelope_front"]
    frames += [(f, ms) for f in imaging.hold(ef, n, envelope_anchor)]

    n, ms = config.TIMING["turn_envelope"]
    frames += [(f, ms) for f in imaging.flip_transition(ef, eb, "x", n, envelope_anchor)]

    n, ms = config.TIMING["hold_envelope_back"]
    frames += [(f, ms) for f in imaging.hold(eb, n, envelope_anchor)]

    n, ms = config.TIMING["flap_open"]
    frames += [(f, ms) for f in imaging.flip_transition(eb, eo, "y", n, envelope_anchor)]

    n, ms = config.TIMING["hold_envelope_open"]
    frames += [(f, ms) for f in imaging.hold(eo, n, envelope_anchor)]

    n, ms = config.TIMING["card_slide_out"]
    bg = imaging.paste_with_pivot(imaging.blank_canvas(), eo, envelope_anchor)
    frames += [
        (f, ms)
        for f in imaging.slide_reveal(
            cc, n, canvas_w / 2, envelope_anchor[1], card_cover_anchor[1] - cc.height / 2, bg
        )
    ]

    n, ms = config.TIMING["hold_card_cover"]
    frames += [(f, ms) for f in imaging.hold(cc, n, card_cover_anchor)]

    n, ms = config.TIMING["card_open"]
    frames += [
        (f, ms)
        for f in imaging.flip_transition(
            cc, co, "y", n, (canvas_w / 2, hinge_y),
            pivot_frac_a=0.0, pivot_frac_b=config.CARD_FOLD_FRAC,
        )
    ]

    n, ms = config.TIMING["hold_final"]
    frames += [
        (f, ms)
        for f in imaging.hold(co, n, (canvas_w / 2, hinge_y), pivot_frac=(0.5, config.CARD_FOLD_FRAC))
    ]

    return frames
