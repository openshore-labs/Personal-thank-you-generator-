"""Photo compositing: lifting the ink off a photo of handwriting so it can be
written onto the card interior / envelope front as if penned there, and
patching the envelope's flap out of the back photo for the flap-open stage.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config, imaging


def extract_ink(source):
    """Lift the handwriting off a photo of it on paper: returns an RGBA image
    where the pen strokes keep their natural colour and everything else (paper,
    lighting gradients, and the embossed show-through from writing on the pages
    above) is transparent, plus the tight bounding box of the ink.

    Works by dividing the photo by a local estimate of the paper tone (a
    max-filtered, heavily blurred copy), so only marks meaningfully darker
    than their surrounding paper survive -- faint embossing divides out to
    ~1.0 and drops away.
    """
    img = (source if isinstance(source, Image.Image) else Image.open(source)).convert("RGB")
    gray = img.convert("L")
    paper = gray.filter(
        ImageFilter.MaxFilter(2 * config.INK_MAX_RADIUS + 1)
    ).filter(ImageFilter.GaussianBlur(config.INK_BG_BLUR))

    darkness = np.clip(1 - np.asarray(gray, float) / np.clip(np.asarray(paper, float), 1, None), 0, 1)
    alpha = np.clip((darkness - config.INK_FLOOR) / (1 - config.INK_FLOOR) * config.INK_GAIN, 0, 1)
    a = (alpha * 255).astype("uint8")
    a[a < config.INK_CUTOFF] = 0  # kill faint embossing/noise so it leaves no ghost

    rgba = Image.fromarray(np.dstack([np.asarray(img), a]), "RGBA")
    ys, xs = np.where(a > config.INK_BBOX_THRESH)
    if not len(xs):
        return rgba, (0, 0, img.width, img.height)
    return rgba, (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _rect_in_bbox(base_img, bbox_name, rect_frac):
    """Absolute px rect (x0,y0,x1,y1) from a fraction-of-object-bbox rect."""
    x0, y0, x1, y1 = imaging.bbox_px(bbox_name, base_img.size)
    bw, bh = x1 - x0, y1 - y0
    fx0, fy0, fx1, fy1 = rect_frac
    return (x0 + fx0 * bw, y0 + fy0 * bh, x0 + fx1 * bw, y0 + fy1 * bh)


def place_handwriting(base_img, photo_source, dst_rect, align):
    """Extract the ink from photo_source and write it onto base_img, scaled to
    fit within dst_rect (preserving the handwriting's aspect ratio) and aligned
    within it. align is (horizontal, vertical) from {left/center/right} x
    {top/center/bottom}."""
    ink, bbox = extract_ink(photo_source)
    crop = ink.crop(bbox)

    dw, dh = dst_rect[2] - dst_rect[0], dst_rect[3] - dst_rect[1]
    scale = min(dw / crop.width, dh / crop.height)
    nw, nh = max(1, round(crop.width * scale)), max(1, round(crop.height * scale))
    resized = crop.resize((nw, nh), Image.LANCZOS)

    ax = {"left": 0.0, "center": 0.5, "right": 1.0}[align[0]]
    ay = {"top": 0.0, "center": 0.5, "bottom": 1.0}[align[1]]
    x = round(dst_rect[0] + ax * (dw - nw))
    y = round(dst_rect[1] + ay * (dh - nh))

    out = base_img.convert("RGBA")
    out.alpha_composite(resized, (x, y))
    return out.convert("RGB")


def write_note(card_img, note_source):
    """Write the extracted note onto the open card's interior."""
    rect = _rect_in_bbox(card_img, "card_open", config.CARD_WRITE_RECT_FRAC)
    return place_handwriting(card_img, note_source, rect, config.CARD_WRITE_ALIGN)


def write_address(envelope_front_img, address_source):
    """Write the extracted address onto the envelope front."""
    rect = _rect_in_bbox(envelope_front_img, "envelope_front", config.ENVELOPE_ADDRESS_RECT_FRAC)
    return place_handwriting(envelope_front_img, address_source, rect, config.ENVELOPE_ADDRESS_ALIGN)


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
