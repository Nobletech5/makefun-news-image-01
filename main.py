#!/usr/bin/env python3
"""The world on Friday 13 November 2026 - a news infographic.

A self-contained, stdlib-only program that draws an infographic
summarising the verified world news of Friday 13 November 2026 and
writes it as a PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR).

The picture is rendered pixel by pixel from an embedded 5x7 bitmap
font and encoded as a PNG by hand with zlib. No network, no clock,
no randomness: two runs write identical bytes.
"""

import os
import struct
import zlib
from binascii import crc32

# ------------------------------------------------------------------ font
# 5x7 bitmap font. Each glyph is 7 rows of 5 characters; '#' is a set
# pixel and '.' is clear. Only the characters the copy uses are listed.

FONT = {
    # Uppercase
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    # Digits
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    # Lowercase
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".###.", "#....", "#....", "#....", ".###."),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "...#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", "#...#", ".####", "....#"),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    # Punctuation and symbols
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "/": ("....#", "....#", "...#.", "...#.", "..#..", ".#...", "#...."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "&": (".###.", "#...#", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
}

# The descenders of g and y sit on the last row as a small hook.
FONT["g"] = (".....", ".....", ".####", "#...#", "#...#", ".####", "##...")
FONT["y"] = (".....", ".....", "#...#", "#...#", "#...#", ".####", ".##..")

# ------------------------------------------------------------------ layout
W, H = 1024, 1024

NAVY = (16, 42, 67)        # header band and headline ink
GOLD = (227, 179, 65)      # header rule and subtitle
WHITE = (255, 255, 255)
INK = (16, 42, 67)         # headline text
BODY = (51, 65, 85)        # detail text
MUTED = (100, 116, 139)    # footer text
BAND = (241, 245, 249)     # alternate row background

# (category, colour, headline, detail line 1, detail line 2)
# Every story was reported on Friday 13 November 2026.
STORIES = [
    ("TECH", (29, 78, 216), "NVIDIA CEO RESIGNS",
     "Jensen Huang steps down; shares fall 16%;",
     "US Senate summons him to testify."),
    ("TECH", (14, 116, 144), "MICROSOFT OUTAGE HITS WORLD",
     "Outlook and Teams go down across the globe",
     "as Microsoft services fail worldwide."),
    ("GULF", (185, 28, 28), "IRAN SAYS IT HIT US RADAR",
     "Tehran claims strike on US radar in Bahrain;",
     "four oil tankers hit in the Strait of Hormuz."),
    ("EUROPE", (124, 58, 237), "EU JOINS UKRAINE PEACE TALKS",
     "Europe to take part in the next peace round;",
     "work starts on the largest prisoner swap."),
    ("USA", (159, 18, 57), "VAN HOLLEN CHALLENGES SCHUMER",
     "Senator seeks Senate Democratic leadership",
     "in a Dec 1 vote after midterm wins."),
    ("MARKETS", (21, 128, 61), "BITCOIN FALLS BELOW $70,000",
     "Crypto falls as US producer prices",
     "rise 6.5% in a year."),
    ("GAZA", (146, 64, 14), "HOSPITAL STRIKE KILLS SIX",
     "Israeli missile hits Nasser hospital in",
     "Khan Younis; a surgeon among the six dead."),
    ("SPORT", (190, 24, 93), "ENGLAND BEAT CROATIA",
     "Kane breaks England caps record as the",
     "Three Lions reach Nations League quarters."),
]


def new_canvas():
    """A white RGB canvas as a flat bytearray."""
    return bytearray([255]) * (W * H * 3)


def put_pixel(img, x, y, colour):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        img[i], img[i + 1], img[i + 2] = colour


def fill_rect(img, x, y, w, h, colour):
    x0 = max(x, 0)
    y0 = max(y, 0)
    x1 = min(x + w, W)
    y1 = min(y + h, H)
    r, g, b = colour
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            img[i], img[i + 1], img[i + 2] = r, g, b


def text_width(text, scale):
    """Pixel width of text at the given scale."""
    return len(text) * 6 * scale - scale


def draw_text(img, x, y, text, scale, colour):
    """Draw text with its top-left corner at (x, y). Returns the x after it."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 6 * scale
            continue
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "#":
                    fill_rect(img, cx + col * scale, y + row * scale,
                              scale, scale, colour)
        cx += 6 * scale
    return cx - scale


def draw_text_centred(img, y, text, scale, colour):
    draw_text(img, (W - text_width(text, scale)) // 2, y, text, scale, colour)

# ------------------------------------------------------------------ render
def render():
    img = new_canvas()

    # Header band.
    fill_rect(img, 0, 0, W, 128, NAVY)
    draw_text_centred(img, 20, "THE WORLD TODAY", 5, WHITE)
    draw_text_centred(img, 70, "FRIDAY 13 NOVEMBER 2026", 3, GOLD)
    fill_rect(img, 0, 118, W, 4, GOLD)

    # Story rows.
    row_y = 148
    row_h = 100
    gap = 6
    for n, (tag, colour, headline, line1, line2) in enumerate(STORIES):
        y = row_y + n * (row_h + gap)
        if n % 2 == 0:
            fill_rect(img, 0, y, W, row_h, BAND)
        fill_rect(img, 20, y, 10, row_h, colour)
        # Headline: coloured tag, then the headline in navy ink.
        x = 48
        x = draw_text(img, x, y + 8, tag, 4, colour)
        draw_text(img, x + 24, y + 8, headline, 4, INK)
        draw_text(img, 48, y + 44, line1, 3, BODY)
        draw_text(img, 48, y + 68, line2, 3, BODY)

    # Footer.
    draw_text_centred(img, 1002, "All stories reported on Friday 13 November 2026.",
                      2, MUTED)
    return img


# ------------------------------------------------------------------ PNG
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", crc32(kind + data) & 0xFFFFFFFF)


def encode_png(img):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw += img[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(encode_png(render()))


if __name__ == "__main__":
    main()
