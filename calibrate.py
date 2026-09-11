#!/usr/bin/env python3
"""Draws the measured bboxes, the flap triangle, and the note quad on top of
the source photos, at a viewable size, so you can eyeball whether
thankyou_gif/config.py's geometry still lines up. Writes PNGs to
output/calibration/.

Run this any time you tweak config.py, before spending time on a full GIF
render.
"""

import os

from PIL import Image, ImageDraw

from thankyou_gif import compositing, config, imaging

OUT_DIR = os.path.join(config.OUTPUT_DIR, "calibration")
PREVIEW_WIDTH = 700


def _preview(img, overlays_fn, name):
    img = img.copy()
    draw = ImageDraw.Draw(img)
    overlays_fn(draw, img)
    scale = PREVIEW_WIDTH / img.width
    img = img.resize((PREVIEW_WIDTH, round(img.height * scale)), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"{name}.png")
    img.save(out_path)
    print(f"wrote {out_path}")


def main():
    for name in ("envelope_front", "envelope_back", "card_cover", "card_open"):
        img = imaging.load_source(name)

        def draw_bbox(draw, img, name=name):
            x0, y0, x1, y1 = imaging.bbox_px(name, img.size)
            draw.rectangle((x0, y0, x1, y1), outline=(255, 0, 0), width=6)

        _preview(img, draw_bbox, f"bbox_{name}")

    envelope_back = imaging.load_source("envelope_back")

    def draw_flap(draw, img):
        triangle = compositing.flap_triangle_px(img)
        draw.polygon(triangle, outline=(0, 200, 255), width=6)

    _preview(envelope_back, draw_flap, "flap_triangle")

    envelope_front = imaging.load_source("envelope_front")
    patched = compositing.envelope_with_flap_removed(envelope_back, envelope_front)
    _preview(patched, lambda d, i: None, "envelope_flap_removed")

    card_open = imaging.load_source("card_open")

    def draw_write_rect(draw, img, name="card_open", frac=config.CARD_WRITE_RECT_FRAC):
        draw.rectangle(compositing._rect_in_bbox(img, name, frac), outline=(0, 220, 0), width=6)

    _preview(card_open, draw_write_rect, "card_write_rect")

    envelope_front2 = imaging.load_source("envelope_front")
    _preview(
        envelope_front2,
        lambda d, i: d.rectangle(
            compositing._rect_in_bbox(i, "envelope_front", config.ENVELOPE_ADDRESS_RECT_FRAC),
            outline=(0, 220, 0), width=6,
        ),
        "envelope_address_rect",
    )


if __name__ == "__main__":
    main()
