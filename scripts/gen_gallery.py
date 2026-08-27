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


def strip_flat_background(path: pathlib.Path, tol: int = 26,
                          min_removed: float = 0.15, max_dark: float = 0.50) -> bool:
    """Make a thumbnail's flat white background transparent.

    Most release logos ship with an alpha channel already; a few are flattened
    onto opaque white upstream, which reads as a bright box on a dark README.
    This floods inward from the border only, so white *inside* the artwork
    (Elli's sailor hat, the capybara's highlights) survives.

    Three cases are deliberately left alone:

    - Backgrounds that are part of the illustration. v1.14 and v1.20 sit on dark
      navy, so the border never qualifies as white.
    - Art that fills the frame. v1.11 is a pencil sketch whose paper is the
      drawing; only 55% of its border is white, under the 60% gate.
    - Fills that do not achieve much, or that would leave dark line art floating
      on a dark canvas. v1.12's grid lines block the flood (2.7% removed) and
      v1.15 is 85% near-black once the white is gone, invisible on GitHub's dark
      theme. Both are reverted by `min_removed` / `max_dark`.

    The full-resolution original is never touched, only the generated thumbnail.
    Returns True if the thumbnail was rewritten.
    """
    try:
        from PIL import Image
    except ImportError:
        return False

    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()

    edge = ([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
            + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])

    def is_white(xy):
        p = px[xy]
        return p[3] >= 250 and min(p[:3]) >= 255 - tol

    white_edge = [xy for xy in edge if is_white(xy)]
    if not any(px[xy][3] >= 250 for xy in edge):
        return False                      # already transparent
    if len(white_edge) < len(edge) * 0.6:
        return False                      # coloured backdrop, or art fills the frame

    seed = px[white_edge[0]][:3]
    seen = bytearray(w * h)
    dq = collections.deque(white_edge)
    removed = 0
    while dq:
        x, y = dq.popleft()
        i = y * w + x
        if seen[i]:
            continue
        r, g, b, a = px[x, y]
        if a < 250 or max(abs(r - seed[0]), abs(g - seed[1]), abs(b - seed[2])) > tol:
            continue
        seen[i] = 1
        px[x, y] = (r, g, b, 0)
        removed += 1
        if x > 0: dq.append((x - 1, y))
        if x < w - 1: dq.append((x + 1, y))
        if y > 0: dq.append((x, y - 1))
        if y < h - 1: dq.append((x, y + 1))

    if removed < w * h * min_removed:
        return False                      # flood blocked; leave the thumbnail as built

    opaque = dark = 0
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] >= 200:
                opaque += 1
                if 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] < 60:
                    dark += 1
    if opaque and dark / opaque > max_dark:
        return False                      # would vanish on a dark background

    im.save(path)
    return True


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
    built = stripped = 0
    for r in rows:
        dst = THUMBS / f"{r['version']}.png"
        if make_thumb(ROOT / r["file"], dst, args.width):
            built += 1
            if not args.keep_background and strip_flat_background(dst):
                stripped += 1

    text = README.read_text()
    if START not in text or END not in text:
        sys.exit(f"README.md is missing the {START} / {END} markers")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{render(rows, args.cols, args.display_width)}\n{END}{tail}")

    print(f"{len(rows)} releases, {built} thumbnail(s) rebuilt, "
          f"{stripped} background(s) made transparent")


if __name__ == "__main__":
    main()
