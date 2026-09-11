"""Assembles the full ordered frame list for the thank-you GIF:

  1. hold on envelope front
  2. envelope turns around (front -> back)
  3. hold on envelope back
  4. flap opens (real photo of the envelope with its flap lifted)
  5. hold on opened envelope
  6. card is pulled up out of the envelope's mouth (envelope stays put)
  7. card settles into its resting spot as the envelope fades away
  8. hold on closed card cover ("THANK YOU")
  9. card unfolds (cover lifts away, the note is revealed underneath, then
     the interior settles open above the fold -- not a texture-swap flip)
  10. hold on the finished card with the handwritten note
"""

from . import compositing, config, imaging


def _fitted(img, name, target_width):
    return imaging.fit_width(imaging.extract_object(img, name), target_width)


def build_frames(note_path=None, address_path=None):
    envelope_front_src = imaging.load_source("envelope_front")
    envelope_back_src = imaging.load_source("envelope_back")
    card_cover_src = imaging.load_source("card_cover")
    card_open_src = imaging.load_source("card_open")

    if note_path:
        card_open_src = compositing.write_note(card_open_src, note_path)
    if address_path:
        envelope_front_src = compositing.write_address(envelope_front_src, address_path)

    ef = _fitted(envelope_front_src, "envelope_front", config.ENVELOPE_TARGET_WIDTH)
    eb = _fitted(envelope_back_src, "envelope_back", config.ENVELOPE_TARGET_WIDTH)
    eo = _fitted(imaging.load_source("envelope_open"), "envelope_open", config.ENVELOPE_TARGET_WIDTH)
    cc = _fitted(card_cover_src, "card_cover", config.CARD_TARGET_WIDTH)
    co = _fitted(card_open_src, "card_open", config.CARD_TARGET_WIDTH)

    canvas_w, canvas_h = config.CANVAS_SIZE
    cx = canvas_w / 2
    env_bottom = canvas_h * config.ENVELOPE_BOTTOM_Y_FRAC
    env_anchor = (cx, env_bottom)
    env_pivot = (0.5, 1.0)  # bottom-aligned
    hinge_y = canvas_h * config.CARD_HINGE_Y_FRAC
    card_cover_anchor = (cx, hinge_y + cc.height / 2)  # cover rests below the hinge

    frames = []

    n, ms = config.TIMING["hold_envelope_front"]
    frames += [(f, ms) for f in imaging.hold(ef, n, env_anchor, pivot_frac=env_pivot)]

    n, ms = config.TIMING["turn_envelope"]
    frames += [(f, ms) for f in imaging.flip_transition(ef, eb, "x", n, env_anchor, cross_pivot=1.0)]

    n, ms = config.TIMING["hold_envelope_back"]
    frames += [(f, ms) for f in imaging.hold(eb, n, env_anchor, pivot_frac=env_pivot)]

    # Flap opens: the open envelope is much taller (flap up), so pivot the flip
    # at the bottom edge -- the closed envelope squashes down and the open one
    # grows upward from the same base, reading as the flap lifting.
    n, ms = config.TIMING["flap_open"]
    frames += [
        (f, ms)
        for f in imaging.flip_transition(
            eb, eo, "y", n, env_anchor, pivot_frac_a=1.0, pivot_frac_b=1.0, cross_pivot=0.5
        )
    ]

    n, ms = config.TIMING["hold_envelope_open"]
    frames += [(f, ms) for f in imaging.hold(eo, n, env_anchor, pivot_frac=env_pivot)]

    # The card is pulled straight up out of the envelope's mouth -- the
    # envelope itself doesn't move. It's clipped at the fixed mouth line so
    # the part still tucked inside stays hidden behind the envelope's own
    # front-pocket wall (already the lower part of env_bg) until it rises
    # clear of it: a real "pulled from the pocket" motion, not a slide up
    # the screen.
    env_bg = imaging.paste_with_pivot(imaging.blank_canvas(), eo, env_anchor, pivot_frac=env_pivot)
    mouth_y = env_bottom - config.ENVELOPE_MOUTH_FROM_BOTTOM_FRAC * eo.height
    card_top_clear = mouth_y - cc.height - config.CARD_CLEAR_MARGIN
    card_top_rest = card_cover_anchor[1] - cc.height / 2

    n, ms = config.TIMING["card_pull"]
    frames += [
        (f, ms)
        for f in imaging.card_pull(env_bg, cc, n, cx, mouth_y, mouth_y, card_top_clear)
    ]

    # Once fully clear, the card drifts down to its resting spot while the
    # (now empty of card) envelope fades away to a clean background.
    n, ms = config.TIMING["card_settle"]
    frames += [
        (f, ms)
        for f in imaging.slide_reveal(
            cc, n, cx, card_top_clear, card_top_rest, env_bg, imaging.blank_canvas()
        )
    ]

    n, ms = config.TIMING["hold_card_cover"]
    frames += [(f, ms) for f in imaging.hold(cc, n, card_cover_anchor)]

    # The cover unfolds (lifts away to reveal the note beneath, then the
    # interior settles open above the fold) rather than flipping/swapping.
    fold_row = round(co.height * config.CARD_FOLD_FRAC)
    note_top = co.crop((0, 0, co.width, fold_row))
    note_bottom = co.crop((0, fold_row, co.width, co.height))

    n, ms = config.TIMING["card_open"]
    frames += [
        (f, ms)
        for f in imaging.card_unfold(cc, note_top, note_bottom, n, cx, hinge_y)
    ]

    n, ms = config.TIMING["hold_final"]
    frames += [
        (f, ms)
        for f in imaging.hold(co, n, (canvas_w / 2, hinge_y), pivot_frac=(0.5, config.CARD_FOLD_FRAC))
    ]

    return frames
