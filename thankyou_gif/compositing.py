"""Photo compositing: warping a handwritten-note image into the card's note
quad, and patching the envelope's flap out of the back photo so we have a
plausible "flap lifted away" background for the flap-open stage.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config, imaging


def _find_perspective_coeffs(dst_quad, src_quad):
    """Coeffs for Image.transform(size, PERSPECTIVE, coeffs) such that the
    corners of `src_quad` (in the image being sampled) land at `dst_quad`
    (in the output image's coordinate space)."""
    matrix = []
    for (X, Y), (x, y) in zip(dst_quad, src_quad):
        matrix.append([X, Y, 1, 0, 0, 0, -X * x, -Y * x])
        matrix.append([0, 0, 0, X, Y, 1, -X * y, -Y * y])
    A = np.array(matrix, dtype=float)
    B = np.array(src_quad, dtype=float).reshape(8)
    return np.linalg.solve(A, B).tolist()


def note_quad_px(card_img):
    """Absolute pixel corners (TL, TR, BR, BL) of the note quad within the
    full, uncropped card_open photo."""
    x0, y0, x1, y1 = imaging.bbox_px("card_open", card_img.size)
    bw, bh = x1 - x0, y1 - y0
    return [(x0 + fx * bw, y0 + fy * bh) for fx, fy in config.NOTE_QUAD_FRAC]


def _match_exposure(note_img, card_img, dst_quad, amount):
    """Gain-shift the note so its paper tone moves toward the card's own
    blank-panel tone, per channel -- keeps a note shot under different
    lighting from glowing brighter/cooler than the card it sits on."""
    if amount <= 0:
        return note_img
    xs = [p[0] for p in dst_quad]
    ys = [p[1] for p in dst_quad]
    pad = 0.06 * (max(xs) - min(xs))
    panel = np.asarray(
        card_img.crop((min(xs) + pad, min(ys) + pad, max(xs) - pad, max(ys) - pad)),
        dtype=float,
    ).reshape(-1, 3)
    card_tone = np.median(panel, axis=0)

    na = np.asarray(note_img, dtype=float)
    lum = na.reshape(-1, 3).mean(axis=1)
    paper = na.reshape(-1, 3)[lum >= np.percentile(lum, 60)]
    note_tone = paper.mean(axis=0)

    gain = np.where(note_tone > 1, card_tone / note_tone, 1.0)
    gain = 1 + (gain - 1) * amount
    out = np.clip(na * gain, 0, 255).astype("uint8")
    return Image.fromarray(out, "RGB")


def _paper_grain_map(card_img, strength):
    """A per-pixel multiply map (~1.0) carrying the card paper's high-frequency
    grain, lighting/vignette divided out, so it can be imprinted onto the note
    without also darkening it."""
    arr = np.asarray(card_img, dtype=float).mean(axis=2)
    blur = np.asarray(
        Image.fromarray(arr.astype("uint8")).filter(ImageFilter.GaussianBlur(6)),
        dtype=float,
    )
    grain = arr / np.clip(blur, 1, None)
    return 1 + (grain - 1) * strength


def composite_note(card_img, note_img, feather_px=2):
    """Returns a copy of card_img (full uncropped photo) with note_img
    perspective-warped into the configured note quad and blended to read as
    ink on the card's own paper: exposure-matched to the card's panel tone,
    grounded with a soft contact shadow, and carrying the card's paper grain.
    """
    dst_quad = note_quad_px(card_img)
    note_img = _match_exposure(note_img, card_img, dst_quad, config.NOTE_EXPOSURE_MATCH)

    w, h = note_img.size
    src_quad = [(0, 0), (w, 0), (w, h), (0, h)]
    coeffs = _find_perspective_coeffs(dst_quad, src_quad)

    warped = note_img.convert("RGBA").transform(
        card_img.size, Image.PERSPECTIVE, coeffs,
        resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0),
    )
    alpha = warped.getchannel("A")
    if feather_px:
        alpha = imaging.feather_alpha(alpha, feather_px)
        warped.putalpha(alpha)

    if config.NOTE_GRAIN_STRENGTH > 0:
        grain = _paper_grain_map(card_img, config.NOTE_GRAIN_STRENGTH)
        rgb = np.asarray(warped.convert("RGB"), dtype=float) * grain[..., None]
        grained = Image.fromarray(np.clip(rgb, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        grained.putalpha(alpha)
        warped = grained

    result = card_img.convert("RGBA")

    if config.NOTE_SHADOW_STRENGTH > 0:
        dx, dy = config.NOTE_SHADOW_OFFSET
        shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(config.NOTE_SHADOW_BLUR))
        shadow_alpha = shadow_alpha.point(lambda a: int(a * config.NOTE_SHADOW_STRENGTH))
        shifted = Image.new("L", card_img.size, 0)
        shifted.paste(shadow_alpha, (dx, dy))
        shadow = Image.new("RGBA", card_img.size, (0, 0, 0, 0))
        shadow.putalpha(shifted)
        result.alpha_composite(shadow)

    result.alpha_composite(warped)
    return result.convert("RGB")


def flap_triangle_px(envelope_img):
    x0, y0, x1, y1 = imaging.bbox_px("envelope_back", envelope_img.size)
    bw, bh = x1 - x0, y1 - y0
    return [(x0 + fx * bw, y0 + fy * bh) for fx, fy in config.FLAP_TRIANGLE_FRAC]


def _inflate_polygon(points, factor):
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in points]


def envelope_with_flap_removed(envelope_back_img, envelope_front_img=None, feather_px=32):
    """Patches the flap out of envelope_back_img for the "flap opens" stage.

    We don't have a real photo of the flap lifted away, and the flap's grey
    printed border is thin enough that the measured FLAP_TRIANGLE_FRAC
    corners (eyeballed off a photo, not detected) won't line up with it to
    the pixel -- a crisp mask makes that mismatch obvious as a leftover
    ghost line. So this deliberately over-covers: the triangle is inflated
    well past the visible border and blurred heavily, trading a touch of
    "faded envelope" softness in this one transitional frame for a fill
    that fully hides the border regardless of the small calibration error.
    Swap this for real cloning/inpainting, or better, a second reference
    photo of the envelope with its flap actually open, once that's in hand.

    envelope_front_img is accepted but unused for now -- kept in the
    signature so a future cross-photo clone can drop back in here without
    touching stages.py.
    """
    bx0, by0, bx1, by1 = imaging.bbox_px("envelope_back", envelope_back_img.size)
    triangle = _inflate_polygon(flap_triangle_px(envelope_back_img), 1.35)
    # Keep the (now generously oversized) mask from bleeding past the
    # envelope's own edges onto the backdrop behind it.
    triangle = [(min(max(x, bx0), bx1), min(max(y, by0), by1)) for x, y in triangle]
    sample_box = (
        round(bx0 + 0.16 * (bx1 - bx0)), round(by1 - 0.13 * (by1 - by0)),
        round(bx1 - 0.16 * (bx1 - bx0)), round(by1 - 0.04 * (by1 - by0)),
    )
    mean_color = tuple(
        round(v) for v in np.array(envelope_back_img.crop(sample_box)).reshape(-1, 3).mean(axis=0)
    )

    mask = Image.new("L", envelope_back_img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(triangle, fill=255)
    mask = imaging.feather_alpha(mask, feather_px)

    # The blur above can bleed a few px past the envelope's own edges;
    # clip it back so the fill never paints onto the backdrop behind it.
    bbox_mask = Image.new("L", envelope_back_img.size, 0)
    ImageDraw.Draw(bbox_mask).rectangle((bx0, by0, bx1, by1), fill=255)
    mask = Image.fromarray((np.array(mask) * (np.array(bbox_mask) / 255)).astype("uint8"))

    fill = Image.new("RGB", envelope_back_img.size, mean_color)
    result = envelope_back_img.copy()
    result.paste(fill, (0, 0), mask)
    return result
