"""Low-level image helpers: loading, cropping to a measured bbox, easing,
and the generic pivoted "flip" transition used for both the envelope
turning around and the card lid opening (same squash-and-swap trick, just
on different axes with different pivot points).
"""

import math
import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from scipy import ndimage

from . import config


def load_source(name):
    path = os.path.join(config.SOURCE_DIR, config.FILES[name])
    return Image.open(path).convert("RGB")


def bbox_px(name, img_size):
    """Pixel bbox (x0, y0, x1, y1) for a named asset, scaled to img_size."""
    w, h = img_size
    x0f, y0f, x1f, y1f = config.BBOX_FRAC[name]
    return (round(x0f * w), round(y0f * h), round(x1f * w), round(y1f * h))


def crop_to_bbox(img, name, pad_frac=0.015):
    """Crop img to its measured object bbox, with a little breathing room."""
    x0, y0, x1, y1 = bbox_px(name, img.size)
    pw, ph = round((x1 - x0) * pad_frac), round((y1 - y0) * pad_frac)
    x0, y0 = max(0, x0 - pw), max(0, y0 - ph)
    x1, y1 = min(img.width, x1 + pw), min(img.height, y1 + ph)
    return img.crop((x0, y0, x1, y1))


def extract_object(img, name, pad_frac=0.02):
    """Cut the object (envelope/card) out of its maroon-leather photo, returning
    an RGBA crop where the leather is transparent so it can sit on plain white.

    The paper is much brighter than the leather, so a luminance threshold
    separates them; interior holes are filled (dark ink strokes inside the card
    stay opaque), only the largest piece is kept (drops stray bright specks on
    the leather), and the mask is eroded a touch to shed the thin leather fringe
    at the very edge, then feathered for a clean anti-aliased boundary."""
    crop = crop_to_bbox(img, name, pad_frac).convert("RGB")
    gray = np.asarray(crop.convert("L"))
    mask = ndimage.binary_fill_holes(gray > config.OBJECT_MASK_THRESHOLD)
    labels, n = ndimage.label(mask)
    if n > 1:
        sizes = ndimage.sum(mask, labels, range(1, n + 1))
        mask = labels == (int(np.argmax(sizes)) + 1)
    if config.OBJECT_MASK_ERODE:
        mask = ndimage.binary_erosion(mask, iterations=config.OBJECT_MASK_ERODE)
    alpha = Image.fromarray((mask * 255).astype("uint8")).filter(
        ImageFilter.GaussianBlur(config.OBJECT_EDGE_FEATHER)
    )
    rgba = crop.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def fit_width(img, target_width):
    w, h = img.size
    scale = target_width / w
    return img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)


def blank_canvas():
    return Image.new("RGB", config.CANVAS_SIZE, config.BG_COLOR)


def _feathered_mask(size, feather_px):
    """Solid-white mask the size of an object crop, with its border feathered
    inward so the paste dissolves into the background over `feather_px`."""
    w, h = size
    mask = Image.new("L", (w, h), 0)
    inset = feather_px
    ImageDraw.Draw(mask).rectangle(
        (inset, inset, w - 1 - inset, h - 1 - inset), fill=255
    )
    return mask.filter(ImageFilter.GaussianBlur(feather_px / 2))


def _object_mask(img, feather_px):
    """The paste mask for an object: its own alpha if it carries one (a cut-out
    RGBA object or a sheared image with transparent corners), otherwise a solid
    rectangle optionally feathered at the outer edge."""
    if img.mode == "RGBA":
        return img.getchannel("A")
    base = Image.new("L", img.size, 255)
    if feather_px:
        base = ImageChops.multiply(base, _feathered_mask(img.size, feather_px))
    return base


def _draw_contact_shadow(frame, obj_mask, topleft, strength):
    """Darken `frame` (in place) with a soft blurred shadow the shape of the
    object (obj_mask), offset by config.OBJECT_SHADOW_OFFSET, so the object
    reads as resting on the leather rather than stamped on it."""
    if strength <= 0:
        return
    dx, dy = config.OBJECT_SHADOW_OFFSET
    x, y = topleft
    sil = Image.new("L", frame.size, 0)
    sil.paste(obj_mask, (x + dx, y + dy))
    sil = sil.filter(ImageFilter.GaussianBlur(config.OBJECT_SHADOW_BLUR))
    sil = sil.point(lambda a: int(a * strength))
    frame.paste(Image.new("RGB", frame.size, (0, 0, 0)), (0, 0), sil)


def paste_with_pivot(
    canvas, img, anchor_point, pivot_frac=(0.5, 0.5), feather_px=None, shadow=0.0
):
    """Paste img onto a copy of canvas such that the point at
    (pivot_frac[0]*img.width, pivot_frac[1]*img.height) lands on
    anchor_point (x, y) in canvas coordinates. When feather_px is set, the
    object's rectangular edge is softened into the background over that many
    px (defaults to config.PASTE_FEATHER_PX; pass 0 to disable). When shadow
    > 0, a soft contact shadow at that strength is drawn under the object.
    Respects the image's own alpha when it has one."""
    frame = canvas.copy()
    px_frac, py_frac = pivot_frac
    ax, ay = anchor_point
    x = round(ax - px_frac * img.width)
    y = round(ay - py_frac * img.height)
    fp = config.PASTE_FEATHER_PX if feather_px is None else feather_px
    fp = fp if (fp and img.width > 2 * fp and img.height > 2 * fp) else 0
    mask = _object_mask(img, fp)
    if shadow:
        _draw_contact_shadow(frame, mask, (x, y), shadow)
    frame.paste(img.convert("RGB"), (x, y), mask)
    return frame


def hold(img, n_frames, anchor_point, pivot_frac=(0.5, 0.5)):
    frame = paste_with_pivot(
        blank_canvas(), img, anchor_point, pivot_frac, shadow=config.OBJECT_SHADOW_STRENGTH
    )
    return [frame.copy() for _ in range(n_frames)]


def _shear_about_pivot(img, axis, shear_k, pivot):
    """Shear img along the cross-axis about its pivot line, expanding the
    canvas so nothing clips. Returns (sheared_img, new_pivot_frac) where the
    pivot point is preserved. shear_k is signed slope. For a 'y' (lid) flip
    this is a horizontal shear about the hinge row; for an 'x' (turn) flip a
    vertical shear about the seam column."""
    w, h = img.size
    if axis == "y":
        yp = pivot * h
        pad = int(abs(shear_k) * h) + 1
        canvas = Image.new("RGBA", (w + 2 * pad, h), (0, 0, 0, 0))
        canvas.paste(img.convert("RGBA"), (pad, 0))
        # output_x samples input at x - k*(y - yp); +pad keeps content in frame
        out = canvas.transform(
            canvas.size, Image.AFFINE,
            (1, -shear_k, shear_k * yp, 0, 1, 0), resample=Image.BICUBIC,
        )
        new_pivot = ((pad + w * 0.5) / out.width, pivot)
        return out, new_pivot
    else:
        xp = pivot * w
        pad = int(abs(shear_k) * w) + 1
        canvas = Image.new("RGBA", (w, h + 2 * pad), (0, 0, 0, 0))
        canvas.paste(img.convert("RGBA"), (0, pad))
        out = canvas.transform(
            canvas.size, Image.AFFINE,
            (1, 0, 0, -shear_k, 1, shear_k * xp), resample=Image.BICUBIC,
        )
        new_pivot = (pivot, (pad + h * 0.5) / out.height)
        return out, new_pivot


def flip_transition(
    img_a, img_b, axis, n_frames, anchor_point,
    pivot_frac_a=0.5, pivot_frac_b=0.5, cross_pivot=0.5, ease=ease_in_out_cubic,
):
    """Frames of img_a squashing flat and un-squashing into img_b, mimicking
    a card/envelope flipping over.

    axis: 'x' scales width (turning left/right around a vertical seam),
          'y' scales height (opening like a lid around a horizontal hinge).
    anchor_point: canvas (x, y) that stays fixed as the scaling axis pivots.
    pivot_frac_a / pivot_frac_b: where, along the scaling axis (0=leading
        edge, 0.5=center, 1=trailing edge) of img_a / img_b, the anchor
        point sits. E.g. for a lid hinged at its top edge, pivot_frac=0.
    cross_pivot: where the anchor sits on the OTHER axis (the one not being
        scaled). 0.5 centers; 1.0 bottom-aligns a 'y' flip / right-aligns an
        'x' flip. Used to keep an envelope's bottom edge fixed while its flap
        grows upward.
    """
    frames = []
    for i in range(n_frames):
        t = i / (n_frames - 1) if n_frames > 1 else 1.0
        te = ease(t)
        scale = max(abs(math.cos(math.pi * te)), 0.01)
        use_b = te > 0.5
        src = img_b if use_b else img_a
        pivot = pivot_frac_b if use_b else pivot_frac_a
        w, h = src.size
        if axis == "x":
            new_w, new_h = max(1, round(w * scale)), h
            pivot_frac = (pivot, cross_pivot)
        else:
            new_w, new_h = w, max(1, round(h * scale))
            pivot_frac = (cross_pivot, pivot)
        resized = src.resize((new_w, new_h), Image.LANCZOS)

        # Foreshortening shear, peaking mid-flip and zero at the flat ends so
        # it blends into the neighbouring holds. Applied to the already-squashed
        # image about its pivot line.
        if config.FLIP_SHEAR:
            k = config.FLIP_SHEAR * math.sin(math.pi * te)
            resized, pivot_frac = _shear_about_pivot(resized, axis, k, pivot)

        # Fade the contact shadow with the squash factor: full at the flat
        # start/end (matching the neighbouring holds, so no pop), gone when
        # the object is edge-on and casts no footprint.
        frames.append(paste_with_pivot(
            blank_canvas(), resized, anchor_point, pivot_frac,
            shadow=config.OBJECT_SHADOW_STRENGTH * scale,
        ))
    return frames


def slide_reveal(img, n_frames, x, y_start, y_end, bg_start, bg_end=None, ease=ease_in_out_cubic):
    """img's top edge translates from y_start to y_end (horizontally centered
    on x), mimicking the card sliding up out of the envelope. The background
    crossfades from bg_start (the open envelope) to bg_end (plain leather) over
    the slide, so the tall open envelope dissolves away as the card emerges
    rather than popping out at the following hold. bg_end defaults to
    bg_start (no fade)."""
    if bg_end is None:
        bg_end = bg_start
    frames = []
    for i in range(n_frames):
        t = i / (n_frames - 1) if n_frames > 1 else 1.0
        te = ease(t)
        y = round(y_start + (y_end - y_start) * te)
        background = Image.blend(bg_start, bg_end, te)
        frame = paste_with_pivot(
            background, img, (x, y), pivot_frac=(0.5, 0.0),
            shadow=config.OBJECT_SHADOW_STRENGTH,
        )
        frames.append(frame)
    return frames


def feather_alpha(mask_img, radius):
    return mask_img.filter(ImageFilter.GaussianBlur(radius))


def _lerp(a, b, t):
    return a + (b - a) * t


def _compose(cx, layers):
    """Alpha-composite (rgba, top_y) layers, bottom-first, centered at cx, on a
    fresh canvas. Returns RGB."""
    frame = blank_canvas().convert("RGBA")
    for rgba, top_y in layers:
        frame.alpha_composite(rgba.convert("RGBA"), (round(cx - rgba.width / 2), round(top_y)))
    return frame.convert("RGB")


def _clip_below(rgba, local_y):
    """Copy of rgba with rows at/below local_y made transparent (rows above
    local_y are untouched). Used to hide the part of the card still tucked
    inside the envelope, below the fixed mouth line."""
    out = rgba.copy()
    alpha = np.asarray(out.getchannel("A")).copy()
    cut = max(0, min(out.height, int(round(local_y))))
    alpha[cut:] = 0
    out.putalpha(Image.fromarray(alpha))
    return out


def card_pull(envelope_bg, card, n, cx, mouth_y, card_top0, card_top1, ease=ease_in_out_cubic):
    """The card rises up out of the envelope's mouth while the envelope itself
    stays put -- a real "pulled from the pocket" motion rather than sliding up
    the screen. The envelope's front pocket wall is already the lower part of
    envelope_bg, so the card is simply clipped at the fixed mouth line: only
    the portion that has risen above it is drawn, and z-order does the rest
    (the still-life pocket wall in envelope_bg naturally covers the hidden
    part since we never paint over it there).

    card_top0 should equal mouth_y (card fully hidden, nothing visible yet);
    card_top1 is where the card ends up once fully clear of the envelope.
    """
    frames = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 1.0
        te = ease(t)
        card_top = _lerp(card_top0, card_top1, te)
        visible = _clip_below(card, mouth_y - card_top)
        frames.append(paste_with_pivot(envelope_bg, visible, (cx, card_top), pivot_frac=(0.5, 0.0)))
    return frames


def card_unfold(cover, note_top, note_bottom, n, cx, fold_y, ease=ease_in_out_cubic):
    """The closed cover unfolds around the fold line (top-fold hinge) to
    reveal the note underneath -- physically, not a texture-swap flip:

    First half: the cover foreshortens (shrinks vertically, top-anchored at
    the fixed hinge/fold line) as if lifting away, while note_bottom -- which
    was there the whole time, just hidden underneath -- sits fully visible
    beneath it the entire half, progressively uncovered by the shrinking
    cover starting from its free (bottom) edge. That's the physically correct
    order for a top-hinged lid lifting off, viewed from directly above.

    Second half: with the cover fully gone, note_top (the lid's interior
    face, blank) grows in above the same hinge line, bottom-anchored, exactly
    mirroring the cover's own shrink -- as if the lid has continued its
    rotation and settled open above the hinge. At the end, note_top + fixed
    note_bottom together exactly reproduce the true, fully-open card photo.
    """
    frames = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 1.0
        if t <= 0.5:
            local_t = ease(t / 0.5) if n > 1 else 1.0
            h = max(1, round(cover.height * (1 - local_t)))
            shrinking = cover.resize((cover.width, h), Image.LANCZOS)
            layers = [(note_bottom, fold_y), (shrinking, fold_y - h)]
        else:
            local_t = ease((t - 0.5) / 0.5)
            h = max(1, round(note_top.height * local_t))
            growing = note_top.resize((note_top.width, h), Image.LANCZOS)
            layers = [(note_bottom, fold_y), (growing, fold_y - h)]
        frames.append(_compose(cx, layers))
    return frames
