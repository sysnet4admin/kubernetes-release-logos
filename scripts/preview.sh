#!/usr/bin/env bash
# Render README.md the way github.com does: GitHub's markdown API for the HTML,
# GitHub's own stylesheet for the CSS, served from the repo root so relative
# image paths resolve exactly as they will on github.com.
#
# Usage: scripts/preview.sh [port]          serve at http://localhost:PORT/.preview/
#        scripts/preview.sh --shot [port]   write .preview/shot-{light,dark}.png
#
# Requires: gh (authenticated), python3. --shot also needs Google Chrome.

set -euo pipefail
cd "$(dirname "$0")/.."

SHOT=0
[ "${1:-}" = "--shot" ] && { SHOT=1; shift; }
PORT="${1:-8000}"
OUT=".preview"

command -v gh >/dev/null || { echo "gh not found: https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh is not authenticated. Run: gh auth login"; exit 1; }
mkdir -p "$OUT"

# GitHub's published stylesheet, cached in the ignored preview dir rather than
# vendored into the repo.
CSS="$OUT/github-markdown.css"
if [ ! -s "$CSS" ]; then
  echo "Fetching github-markdown-css..."
  curl -sSfL -o "$CSS" \
    https://raw.githubusercontent.com/sindresorhus/github-markdown-css/main/github-markdown.css
fi
echo "Rendering README.md via GitHub markdown API..."
BODY=$(gh api -X POST /markdown -f mode=gfm -f text="$(cat README.md)")

write_page() {  # $1 = output file, $2 = theme (light | dark | "" for viewer's own)
  {
    echo '<!doctype html>'
    echo '<meta charset="utf-8">'
    echo '<base href="/">'
    echo '<title>README preview</title>'
    echo '<style>'
    python3 scripts/_theme_css.py "$CSS" "$2"
    # github-markdown-css scopes its variables to .markdown-body, so the page
    # background has to be set explicitly rather than inherited.
    case "$2" in
      dark)  echo '  body { margin:0; padding:32px 16px; background:#0d1117; color:#f0f6fc; }' ;;
      light) echo '  body { margin:0; padding:32px 16px; background:#ffffff; color:#1f2328; }' ;;
      *)     echo '  body { margin:0; padding:32px 16px; background:#ffffff; color:#1f2328; }'
             echo '  @media (prefers-color-scheme: dark) { body { background:#0d1117; color:#f0f6fc; } }' ;;
    esac
    echo '  .wrap { max-width:1012px; margin:0 auto; }'
    echo '  .note { color:var(--fgColor-muted,#59636e); font-size:12px; margin:0 0 12px;'
    echo '          font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }'
    echo '  .box { border:1px solid var(--borderColor-default,#d1d9e0); border-radius:6px; padding:32px; }'
    echo '</style>'
    echo '<div class="wrap">'
    echo '<p class="note">Local preview. HTML from GitHub&#39;s markdown API, CSS from github-markdown-css.</p>'
    echo '<article class="markdown-body box">'
    printf '%s\n' "$BODY"
    echo '</article></div>'
  } > "$1"
}

write_page "$OUT/index.html" ""

python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
sleep 2

if [ "$SHOT" = "1" ]; then
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  [ -x "$CHROME" ] || { echo "Google Chrome not found; cannot screenshot"; exit 1; }
  for t in light dark; do
    write_page "$OUT/$t.html" "$t"
    "$CHROME" --headless --disable-gpu --hide-scrollbars \
      --window-size=1100,3600 --screenshot="$PWD/$OUT/shot-$t.png" \
      "http://localhost:$PORT/$OUT/$t.html" >/dev/null 2>&1 || true
    echo "wrote $OUT/shot-$t.png"
  done
  exit 0
fi

echo "Serving http://localhost:${PORT}/${OUT}/  (Ctrl+C to stop)"
wait $SRV
