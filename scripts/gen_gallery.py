#!/usr/bin/env python3
"""Regenerate thumbnails and the README gallery from logos.tsv.

Usage:  python3 scripts/gen_gallery.py [--width 400] [--cols 3]

logos.tsv is the source of truth: one row per release, newest first is not
required (this script sorts by version descending). Thumbnails are written to
thumbs/vX.YY.png and are only rebuilt when missing or older than the source.

Requires: rsvg-convert (SVG sources) and sips (macOS, raster sources).
"""
import argparse
import collections
import csv
import html
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TSV = ROOT / "logos.tsv"
README = ROOT / "README.md"
THUMBS = ROOT / "thumbs"
START, END = "<!-- gallery:start -->", "<!-- gallery:end -->"


def load_rows():
    with TSV.open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        r["file"] = r["file"].strip()
        r["codename"] = r["codename"].strip()
        src = ROOT / r["file"]
        if not src.exists():
            sys.exit(f"missing image: {r['file']} (referenced by {r['version']})")
    def key(r):
        major, minor = r["version"].lstrip("v").split(".")
        return (int(major), int(minor))
    return sorted(rows, key=key, reverse=True)


def make_thumb(src: pathlib.Path, dst: pathlib.Path, width: int) -> bool:
    """Return True if the thumbnail was (re)built."""
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return False
    dst.parent.mkdir(exist_ok=True)
    if src.suffix.lower() == ".svg":
        if not shutil.which("rsvg-convert"):
            sys.exit("rsvg-convert not found (brew install librsvg)")
        subprocess.run(
            ["rsvg-convert", "-w", str(width), str(src), "-o", str(dst)], check=True
        )
    else:
        if not shutil.which("sips"):
            sys.exit("sips not found (this path expects macOS)")
        subprocess.run(
            ["sips", "-s", "format", "png", "-Z", str(width), str(src), "--out", str(dst)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return True


def strip_flat_background(path: pathlib.Path, tol: int = 26, light: int = 150,
                          min_removed: float = 0.15, max_dark: float = 0.50,
                          keyline: int = 5) -> str:
    """Lift a thumbnail off the flat white it was flattened onto upstream.

    Most release logos ship with an alpha channel; a few are baked onto opaque
    white, which reads as a bright box on GitHub's dark theme.

    The background is found by flooding inward from the border through *light*
    pixels only, so white inside the artwork (Elli's sailor hat, the capybara's
    cap) is never reached. Each pixel in that region is un-matted rather than
    simply cleared: treating it as the artwork composited over white,
    `a = 1 - min(r,g,b)/255` recovers the coverage and the colour is
    un-premultiplied. That keeps anti-aliased edges soft instead of leaving the
    pale fringe a hard cut-out produces.

    Three outcomes:

    - "stripped": the background is gone and the artwork still reads.
    - "keyline": the artwork is mostly near-black, so it would disappear on a
      dark canvas. The background is cleared except for a white band hugging the
      silhouette, giving the die-cut sticker look.
    - "": nothing was changed. The border is not white (v1.14 and v1.20 sit on
      dark navy), the artwork fills the frame (v1.11's pencil sketch covers all
      but 55% of the border), or the flood barely moved (v1.12's grid lines
      block it at 2.7%).

    The full-resolution original is never touched, only the generated thumbnail.
    """
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return ""

    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()

    edge = ([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
            + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    white_edge = [xy for xy in edge if px[xy][3] >= 250 and min(px[xy][:3]) >= 255 - tol]
    if not any(px[xy][3] >= 250 for xy in edge):
        return ""                          # already transparent
    if len(white_edge) < len(edge) * 0.6:
        return ""                          # coloured backdrop, or art fills the frame

    original = im.copy()
    seen = bytearray(w * h)
    dq = collections.deque(white_edge)
    region = []
    while dq:
        x, y = dq.popleft()
        i = y * w + x
        if seen[i]:
            continue
        r, g, b, a = px[x, y]
        if a < 250 or min(r, g, b) < light:
            continue                       # artwork blocks the flood
        seen[i] = 1
        region.append((x, y))
        if x > 0: dq.append((x - 1, y))
        if x < w - 1: dq.append((x + 1, y))
        if y > 0: dq.append((x, y - 1))
        if y < h - 1: dq.append((x, y + 1))

    if len(region) < w * h * min_removed:
        return ""                          # flood blocked; leave the thumbnail as built

    for x, y in region:
        r, g, b, _ = px[x, y]
        a = 1.0 - min(r, g, b) / 255.0     # coverage of art over white
        if a <= 0.02:
            px[x, y] = (r, g, b, 0)
        else:
            inv = (1.0 - a) * 255.0
            px[x, y] = (min(255, max(0, round((r - inv) / a))),
                        min(255, max(0, round((g - inv) / a))),
                        min(255, max(0, round((b - inv) / a))),
                        round(a * 255))

    opaque = dark = 0
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] >= 200:
                opaque += 1
                if 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] < 60:
                    dark += 1

    if opaque and dark / opaque > max_dark:
        # Near-black artwork: keep a white band around the silhouette so it still
        # reads on a dark canvas, and clear the rest.
        art = im.getchannel("A").point(lambda v: 255 if v > 8 else 0)
        band = art.filter(ImageFilter.MaxFilter(keyline * 2 + 1))
        out = original.copy()
        op = out.load()
        bp = band.load()
        cleared = 0
        for x, y in region:
            if not bp[x, y]:
                r, g, b, _ = op[x, y]
                op[x, y] = (r, g, b, 0)
                cleared += 1
        if cleared < w * h * min_removed:
            # The band covers nearly everything, so the die-cut changes nothing
            # visible (v1.12's grid spans the whole canvas). Leave it alone.
            return ""
        out.save(path)
        return "keyline"

    im.save(path)
    return "stripped"


def render(rows, cols, display_width):
    out = ["<table>"]
    for i in range(0, len(rows), cols):
        out.append("  <tr>")
        chunk = rows[i:i + cols]
        for r in chunk:
            name = html.escape(r["codename"], quote=False)
            alt = html.escape(r["codename"], quote=True)
            ver = html.escape(r["version"], quote=False)
            out.append(
                f'    <td align="center" width="{100 // cols}%">'
                f'<a href="{r["file"]}">'
                f'<img src="thumbs/{ver}.png" width="{display_width}" alt="{alt}">'
                f"</a><br><b>{ver}</b><br>{name}</td>"
            )
        for _ in range(cols - len(chunk)):
            out.append(f'    <td align="center" width="{100 // cols}%"></td>')
        out.append("  </tr>")
    out.append("</table>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=400, help="thumbnail pixel width")
    ap.add_argument("--cols", type=int, default=3, help="gallery columns")
    ap.add_argument("--display-width", type=int, default=240, help="<img width> in README")
    ap.add_argument("--keep-background", action="store_true",
                    help="do not make flat white thumbnail backgrounds transparent")
    args = ap.parse_args()

    rows = load_rows()
    built = stripped = keylined = 0
    for r in rows:
        dst = THUMBS / f"{r['version']}.png"
        if make_thumb(ROOT / r["file"], dst, args.width):
            built += 1
            if not args.keep_background:
                mode = strip_flat_background(dst)
                if mode == "stripped":
                    stripped += 1
                elif mode == "keyline":
                    keylined += 1

    text = README.read_text()
    if START not in text or END not in text:
        sys.exit(f"README.md is missing the {START} / {END} markers")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{render(rows, args.cols, args.display_width)}\n{END}{tail}")

    print(f"{len(rows)} releases, {built} thumbnail(s) rebuilt, "
          f"{stripped} background(s) removed, {keylined} die-cut with a keyline")


if __name__ == "__main__":
    main()
