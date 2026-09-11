#!/usr/bin/env python3
"""Build the animated thank-you GIF from the assets in assets/source/,
optionally compositing a handwritten note photo from assets/notes/.

Usage:
    python generate_gif.py
    python generate_gif.py --note assets/notes/my_note.jpg
    python generate_gif.py --note assets/notes/my_note.jpg --out output/for_alex.gif
"""

import argparse

from thankyou_gif.pipeline import render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--note", default=None,
        help="Path to a handwritten-note photo to composite into the card. "
             "Omit to render the sequence with the blank card interior.",
    )
    parser.add_argument(
        "--out", default=None,
        help="Output .gif path (default: output/thank_you.gif)",
    )
    args = parser.parse_args()

    path = render(note_path=args.note, output_path=args.out)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
