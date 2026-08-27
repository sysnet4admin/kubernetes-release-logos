#!/usr/bin/env python3
"""Emit github-markdown.css with one prefers-color-scheme theme baked in.

Headless Chrome does not report a colour-scheme preference reliably, so for
screenshots each theme is flattened into its own stylesheet: the chosen media
block's declarations are hoisted to the top level and both media blocks removed.
Usage: _theme_css.py <path-to-github-markdown.css> [light|dark]

With no theme (or an empty one) the stylesheet passes through unchanged, so the
served page still follows the viewer's own theme.
"""
import pathlib
import re
import sys

CSS = pathlib.Path(sys.argv[1]).read_text()
want = sys.argv[2] if len(sys.argv) > 2 else ""

if not want:
    sys.stdout.write(CSS)
    raise SystemExit

pattern = re.compile(r"@media \(prefers-color-scheme: (dark|light)\) \{(.*?)\n\}\n", re.S)
blocks = {m.group(1): m.group(2) for m in pattern.finditer(CSS)}
if want not in blocks:
    sys.exit(f"no prefers-color-scheme block for {want!r} in github-markdown.css")

sys.stdout.write(blocks[want] + "\n" + pattern.sub("", CSS))
