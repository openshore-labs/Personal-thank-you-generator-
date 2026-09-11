#!/usr/bin/env python3
"""Build the animated thank-you GIF from the assets in assets/source/,
optionally writing a photographed handwritten note onto the card and a
photographed address onto the envelope front (the ink is lifted off the
paper so it reads as penned on the card / envelope).

Usage:
    python generate_gif.py
    python generate_gif.py --note assets/notes/note_body.jpg
    python generate_gif.py --note assets/notes/note_body.jpg \\
        --address assets/notes/envelope_address.jpg --out output/for_natalie.gif

If a photo caught more than the handwriting you want (a desk, a keyboard, the
sheet underneath -- or another note's writing further up the page), restrict
what gets lifted with --note-crop / --address-crop, as x0,y0,x1,y1 fractions
of that photo:
    python generate_gif.py --note assets/notes/laura_note_body.jpg \\
        --note-crop 0.02,0.14,0.98,0.835
"""

import argparse

from thankyou_gif.pipeline import render


def _crop(value):
    """Parse an 'x0,y0,x1,y1' fractions argument into a tuple."""
    if value is None:
        return None
    parts = [float(p) for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop must be four comma-separated fractions: x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise argparse.ArgumentTypeError("crop fractions must satisfy 0 <= x0 < x1 <= 1, 0 <= y0 < y1 <= 1")
    return (x0, y0, x1, y1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--note", default=None,
        help="Path to a photo of the handwritten note to write into the card. "
             "Omit to render the sequence with the blank card interior.",
    )
    parser.add_argument(
        "--address", default=None,
        help="Path to a photo of the handwritten address to write, centered, "
             "on the envelope front. Omit to leave the envelope blank.",
    )
    parser.add_argument(
        "--note-crop", type=_crop, default=None,
        help="Restrict the note photo to this region before lifting the ink, "
             "as x0,y0,x1,y1 fractions. Use when the shot caught anything "
             "other than the note itself.",
    )
    parser.add_argument(
        "--address-crop", type=_crop, default=None,
        help="Same, for the address photo.",
    )
    parser.add_argument(
        "--out", default=None,
        help="Output .gif path (default: output/thank_you.gif)",
    )
    args = parser.parse_args()

    path = render(
        note_path=args.note, address_path=args.address, output_path=args.out,
        note_crop=args.note_crop, address_crop=args.address_crop,
    )
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
