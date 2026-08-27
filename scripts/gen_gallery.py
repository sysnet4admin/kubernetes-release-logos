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
        r["treatment"] = (r.get("treatment") or "").strip()
        if r["treatment"] not in ("", "keyline", "reviewed"):
            sys.exit(f"{r['version']}: unknown treatment {r['treatment']!r} "
                     f"(expected empty, 'keyline' or 'reviewed')")
        src = ROOT / r["file"]
        if not src.exists():
            sys.exit(f"missing image: {r['file']} (referenced by {r['version']})")
    def key(r):
        major, minor = r["version"].lstrip("v").split(".")
        return (int(major), int(minor))
    return sorted(rows, key=key, reverse=True)


def _strip_flat_background(im, tol: int = 26, light: int = 150,
                           min_removed: float = 0.15) -> bool:
    """Lift an image off the flat white it was flattened onto upstream, in place.

    A few release logos are baked onto opaque white, which reads as a bright box
    on GitHub's dark theme. The background is found by flooding inward from the
    border through *light* pixels only, so the artwork's own outline stops it and
    white inside the drawing is never reached.

    This must run at full resolution. Downscaling first thins dark outlines and
    lightens them by averaging, which opens a one-pixel leak: on the 400px
    version of v1.31 the flood slipped through the dog's outline and ate the
    white chest fur and part of the sailor hat.

    Pixels in the background region are un-matted rather than cleared: treating
    each as artwork composited over white, `a = 1 - min(r,g,b)/255` recovers the
    coverage and the colour is un-premultiplied. Downscaling afterwards then
    anti-aliases the cut edge for free.

    Returns False, changing nothing, when the border is not white (v1.14 and
    v1.20 sit on dark navy that is part of the illustration), when the artwork
    fills the frame (v1.11 is a pencil sketch whose paper is the drawing), or
    when the flood barely moves.
    """
    w, h = im.size
    px = im.load()
    edge = ([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
            + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    white_edge = [xy for xy in edge if px[xy][3] >= 250 and min(px[xy][:3]) >= 255 - tol]
    if not any(px[xy][3] >= 250 for xy in edge):
        return False
    if len(white_edge) < len(edge) * 0.6:
        return False

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
            continue
        seen[i] = 1
        region.append((x, y))
        if x > 0: dq.append((x - 1, y))
        if x < w - 1: dq.append((x + 1, y))
        if y > 0: dq.append((x, y - 1))
        if y < h - 1: dq.append((x, y + 1))

    if len(region) < w * h * min_removed:
        return False

    for x, y in region:
        r, g, b, _ = px[x, y]
        a = 1.0 - min(r, g, b) / 255.0
        if a <= 0.02:
            px[x, y] = (r, g, b, 0)
        else:
            inv = (1.0 - a) * 255.0
            px[x, y] = (min(255, max(0, round((r - inv) / a))),
                        min(255, max(0, round((g - inv) / a))),
                        min(255, max(0, round((b - inv) / a))),
                        round(a * 255))
    return True


def make_thumb(src: pathlib.Path, dst: pathlib.Path, width: int,
               strip: bool = True) -> tuple:
    """Build one thumbnail. Returns (rebuilt, background_stripped).

    SVG sources go through rsvg-convert and are already transparent. Raster
    sources are opened at full resolution, lifted off any flat white background
    there, and only then downscaled, so the resize anti-aliases the cut edge and
    cannot leak through a thinned outline.
    """
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return False, False
    dst.parent.mkdir(exist_ok=True)

    if src.suffix.lower() == ".svg":
        if not shutil.which("rsvg-convert"):
            sys.exit("rsvg-convert not found (brew install librsvg)")
        subprocess.run(["rsvg-convert", "-w", str(width), str(src), "-o", str(dst)],
                       check=True)
        return True, False

    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow is required for raster sources (pip install pillow)")
    im = Image.open(src).convert("RGBA")
    stripped = _strip_flat_background(im) if strip else False
    im.thumbnail((width, width), Image.LANCZOS)
    im.save(dst)
    return True, stripped


def add_keyline(path: pathlib.Path, band: int = 5) -> bool:
    """Lay a white band under the artwork, the way a die-cut sticker keeps one.

    Some logos are near-black line art on a transparent background and all but
    vanish against GitHub's dark canvas. A band hugging the silhouette gives
    them an edge to read against, and on the light theme it is white on white,
    so it looks like a plain cut-out.

    This is opt-in per release via the `treatment` column in logos.tsv, not
    automatic: whether a logo needs it is a judgement about the artwork, and the
    measurements do not separate the cases cleanly. v1.13 is 100% low-contrast
    against the dark canvas and v1.33 is 95.5%, yet v1.33 reads fine because its
    lit windows and dragon carry the shape while v1.13's dark blue wings do not.

    Column values: empty means automatic handling and warn if the result looks
    unreadable, `keyline` adds the band, `reviewed` means automatic handling and
    the warning has already been considered and dismissed.
    """
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return False

    im = Image.open(path).convert("RGBA")
    art = im.getchannel("A").point(lambda v: 255 if v > 8 else 0)
    halo = art.filter(ImageFilter.MaxFilter(band * 2 + 1))
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.paste((255, 255, 255, 255), (0, 0), halo)
    out.alpha_composite(im)
    out.save(path)
    return True


def warn_if_unreadable(path: pathlib.Path, version: str, max_dark: float = 0.60) -> None:
    """Point out artwork that may disappear on GitHub's dark theme."""
    try:
        from PIL import Image
    except ImportError:
        return
    px = [p for p in Image.open(path).convert("RGBA").get_flattened_data() if p[3] >= 200]
    if not px:
        return
    dark = sum(1 for p in px if 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] < 70)
    if dark / len(px) > max_dark:
        print(f"  note: {version} is {dark / len(px):.0%} near-black; check it on a "
              f"dark background, and consider treatment=keyline in logos.tsv")


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
                    help="do not touch thumbnail backgrounds at all")
    ap.add_argument("--keyline", type=int, default=5,
                    help="width in px of the die-cut band for treatment=keyline rows")
    args = ap.parse_args()

    rows = load_rows()
    built = stripped = keylined = 0
    for r in rows:
        dst = THUMBS / f"{r['version']}.png"
        treatment = r["treatment"]
        rebuilt, was_stripped = make_thumb(ROOT / r["file"], dst, args.width,
                                           strip=not args.keep_background)
        if not rebuilt:
            continue
        built += 1
        if was_stripped:
            stripped += 1
        if args.keep_background:
            continue
        if treatment == "keyline":
            add_keyline(dst, args.keyline)
            keylined += 1
        elif not treatment:
            warn_if_unreadable(dst, r["version"])

    text = README.read_text()
    if START not in text or END not in text:
        sys.exit(f"README.md is missing the {START} / {END} markers")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{render(rows, args.cols, args.display_width)}\n{END}{tail}")

    print(f"{len(rows)} releases, {built} thumbnail(s) rebuilt, "
          f"{stripped} background(s) removed, {keylined} keylined")


if __name__ == "__main__":
    main()
