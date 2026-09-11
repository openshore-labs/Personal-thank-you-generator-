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
"""

import argparse

from thankyou_gif.pipeline import render


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
        "--out", default=None,
        help="Output .gif path (default: output/thank_you.gif)",
    )
    args = parser.parse_args()

    path = render(note_path=args.note, address_path=args.address, output_path=args.out)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
