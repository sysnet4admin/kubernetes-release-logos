# AGENTS.md

Guidance for AI coding agents working in this repository.
This is the single source of truth; `CLAUDE.md` only imports this file.

## What this repository is

A collection of Kubernetes release logos. Each minor release has one image file
in `logos/` named `vX.YY.<ext>` (`.png`, `.svg`, or `.jpeg`), and `README.md`
shows every release newest-first as a thumbnail gallery.

There is no test suite and no package manifest. The only tooling is
`scripts/gen_gallery.py`. Do not add a package manager or a framework.

The README gallery is a generated HTML table, not hand-written markdown. Full
logos total about 31 MB, so the README links to them rather than embedding them;
it embeds the 400px thumbnails (about 3.8 MB total) instead.

## Layout

| Path | Purpose |
|---|---|
| `logos.tsv` | Source of truth: one row per release (`version`, `codename`, `file`). |
| `README.md` | Generated gallery. Newest release first. Do not hand-edit the gallery block. |
| `scripts/gen_gallery.py` | Builds `thumbs/` and rewrites the README gallery from `logos.tsv`. |
| `thumbs/vX.YY.png` | 400px thumbnail, generated. Committed so the README renders. |
| `logos/vX.YY.<ext>` | Full-resolution logo for one minor release. Added by hand. |
| `kubernetes_release_logos.pdf` | Combined PDF of the collection. |
| `CONTRIBUTING.md` | Human-facing contribution guide. |
| `.github/workflows/pr-author-check.yml` | Fails a PR when commits are authored by a bot account. |

## Adding a release logo

This repo tracks every Kubernetes minor release, so this is a recurring task.
Nothing detects a new release for you; watch https://kubernetes.io/blog/.

### 1. Find the release blog post

The post URL follows `https://kubernetes.io/blog/<YYYY>/<MM>/<DD>/kubernetes-v<major>-<minor>-release/`
and its title is `Kubernetes v<X.YY>: <Codename>`. The publish date is not
predictable, so locate the post rather than guessing the URL:

```bash
minor=1.37
slug=$(echo "$minor" | tr '.' '-')
blog_url=$(curl -sL https://kubernetes.io/blog/ \
  | grep -oE "/blog/[0-9]+/[0-9]+/[0-9]+/kubernetes-v${slug}-release/?" \
  | head -1 | sed 's|^|https://kubernetes.io|')
echo "$blog_url"
```

Read the post title there to get the codename.

### 2. Download the logo

The logo lives next to the post as `k8s-v<X.YY>.svg`:

```bash
curl -sSL -o "logos/v${minor}.svg" "${blog_url%/}/k8s-v${minor}.svg"
```

Confirm it downloaded as SVG and not an HTML error page:

```bash
file "logos/v${minor}.svg"   # expect: SVG Scalable Vector Graphics image
```

If the blog does not ship an SVG, fall back to the PNG on the post or to
[`sig-release`](https://github.com/kubernetes/sig-release/tree/master/releases)
under `releases/release-<X.YY>/`, and name the file with the matching extension.

### 3. Add the row and regenerate

Add one row to `logos.tsv`, directly under the header line:

```
vX.YY<TAB><Codename><TAB>logos/vX.YY.<ext><TAB>
```

The fourth field is the `treatment` column, described under "Thumbnail
backgrounds" below. Leave it empty unless the thumbnail needs it.

Then regenerate the thumbnail and the README gallery:

```bash
python3 scripts/gen_gallery.py
```

The script sorts by version descending, so the row's position in the TSV does not
matter; newest always renders first. It only rebuilds a thumbnail when it is
missing or older than its source, and it is idempotent, so running it twice
changes nothing the second time.

Use the plain ASCII codename from the post title. Some releases carry a
non-Latin gloss in the post body (v1.37 "Garhwal (गढ़वाल)"); `logos.tsv` uses the
Latin form only, matching every existing entry.

Requirements: Pillow, plus `rsvg-convert` (`brew install librsvg`) for SVG
sources. Raster sources go through Pillow alone, so this path is portable.

### Where the best asset lives (audited 2026-08-27)

Two upstream repositories carry release logos, and neither is complete:

- `kubernetes/sig-release` under `releases/release-X.YY/`. Early releases keep a
  bare file at the top of that directory; from v1.24 on the good assets sit in
  that release's own `logo/` (sometimes `logos/`) subdirectory upstream, which is
  easy to miss. That is where the highest-resolution and vector masters usually
  are. Not to be confused with this repository's `logos/`.
- `kubernetes/website` under `static/images/blog/<date>-...` for older posts, and
  inside the post's own page-bundle directory for v1.32 and later.

Check both, and check the `logo/` subdirectory. A full sweep is:

```bash
gh api "repos/kubernetes/sig-release/git/trees/master?recursive=1" \
  --jq '.tree[] | select(.path|test("(?i)\\.(svg|png|jpe?g)$")) | "\(.size)  \(.path)"'
```

Places that were checked and hold nothing useful: `cncf/artwork` (certification
and project marks only), `kubernetes/kubernetes` `logo/` (the project mark),
`kubernetes/community` (KubeCon event logos), `kubernetes/release`, and
`kubernetes/enhancements`.

**v1.10 is the first release with a logo, and there is nothing earlier.** Three
independent checks agree. `release-1.3` through `release-1.9` carry no theme, no
codename and no image, only schedule tables. The v1.3 to v1.13 announcement blog
posts embed no images at all. And the v1.10 README states where the practice
started:

> Code name "*Left Shark*" because it's been my favorite meme of the release
> cycle (Thanks [Christoph](https://github.com/cblecker))

The file was committed on 2018-03-26 with the message `Official "Left Shark" logo`.

**Nothing was ever deleted or downgraded upstream.** A full-history scan of both
repositories (`git log --all --diff-filter=AMRD --name-only`) shows every release
logo was added once and never replaced, so there is no better version hiding in
an old commit.

**Upstream ceilings, not collection gaps:**

- v1.21 is capped at 250x260 (upstream `release-1.21/logos/globe_250px.png`,
  40 KB), designed by Aravind Sekar. It is the only asset in either repository, and the Wayback Machine shows
  kubernetes.io never served anything larger.
- v1.14 and v1.15 are JPEG upstream, and their announcement posts carry no images
  at all. No PNG or vector master exists.
- v1.32 and v1.34 ship PNG only. No SVG was ever published.

**Traps when swapping a file in.** Compare artwork and dimensions first:

- v1.26's 14 MB `electrifying-wallpaper.png` is a 4320x2430 desktop wallpaper,
  not the logo.
- v1.23's sig-release copy is a 500px reduction of the larger blog asset.
- v1.20's sig-release `blepurrnetes.png` (318 KB) is a different image from the
  blog's `laser.png` (4.4 MB), which is the one this repo uses.
- v1.29's designer published an SVG at `psaggu.com/assets/k8s-logo/k8s129.svg`.
  It is not a real vector: it wraps one 4200x4800 base64 PNG on a single 11 MB
  line, which exceeds libxml2's text-node limit and so fails in `rsvg-convert`.
  Its Devanagari numerals sit outside the viewBox and never render. The official
  300dpi PNG is kept instead, for provenance and because the script can process it.

### Thumbnail backgrounds

`gen_gallery.py` adjusts `thumbs/` so logos read on GitHub's dark theme as well
as its light one. It never touches the full-resolution original.

**Background removal is automatic, and runs at full resolution.** A few logos are
flattened onto opaque white upstream, which reads as a bright box on a dark
canvas. The script floods inward from the border through light pixels only, so
the artwork's own outline stops it and white inside the drawing survives.

Order matters here, and getting it wrong is subtle. Stripping the 400px
thumbnail instead of the original punched holes in the artwork: downscaling
thins dark outlines and lightens them by averaging, which opened a one-pixel
leak in v1.31's dog, and the flood poured through and ate the white chest fur
and part of the sailor hat. Strip first, resize second. The resize then
anti-aliases the cut edge for free.

Pixels in the background region are un-matted rather than cleared: treating each
as artwork composited over white, `a = 1 - min(r,g,b)/255` recovers the coverage
and the colour is un-premultiplied. A binary cut-out instead leaves a pale
fringe along every edge, which on dark is worse than the white box.

It backs out on its own when the border is not white (v1.14 and v1.20 sit on
dark navy that is part of the illustration) or when the artwork fills the frame
(v1.11 is a pencil sketch whose paper is the drawing, leaving only 55% of the
border white).

**Keylines are opt-in, per release.** `treatment=keyline` lays a white band under
the silhouette, the way a die-cut sticker keeps one; on the light theme it is
white on white and reads as a plain cut-out. Two reasons to use it: near-black
line art that would otherwise vanish on dark (v1.13, v1.15), and logos that
simply look better with the sticker edge (v1.17, v1.31).

The band must be a *round* offset of the silhouette, built before the downscale,
for the same reason the strip is. Two things go wrong otherwise, and both are
visible on v1.31:

- `ImageFilter.MaxFilter` dilates with a square window, so corners come out
  square and the outline stair-steps. Blurring the alpha and thresholding it is
  isotropic, so the offset follows the shape evenly.
- A binary threshold on the 400px thumbnail leaves a band a few hard pixels
  wide. Building it at full resolution with a soft threshold, then downscaling,
  gives a clean anti-aliased edge.

Width is `--keyline`, a fraction of the logo's longest side, default 0.04. That
lands near the 5.5% of the reference sticker this was modelled on. The canvas is
padded first so the band is not clipped where artwork reaches the edge, as
v1.13's wingtips do. SVG sources are rendered at 4x before the band is added.

This is a judgement call, not a measurement. v1.13 is 100% low-contrast against
GitHub's dark canvas and v1.33 is 95.5%, yet v1.33 reads fine because its lit
windows and dragon carry the shape while v1.13's dark blue wings do not. Any
automatic threshold that catches v1.13 also catches v1.33, so the decision lives
in the data.

The `treatment` column in `logos.tsv`:

| Value | Meaning |
|---|---|
| *(empty)* | Automatic handling. The script warns if the result is mostly near-black. |
| `keyline` | Automatic handling plus the white band. Currently v1.13, v1.15, v1.17 and v1.31. |
| `reviewed` | Automatic handling; the warning has been looked at and dismissed. Currently v1.12, v1.14, v1.24, v1.33. |

When a new logo lands, run the script and read what it prints. If it warns, open
the thumbnail on a dark background and decide between `keyline` and `reviewed`.
Composite the thumbnail over magenta as well: a hole punched in the artwork is
invisible on white and easy to miss on dark, but obvious against a colour the
logo does not contain.
Use `--keyline N` to change the band width (default 5px) and `--keep-background`
to skip all of this.

### Known quirks

- Logo SVGs can be large (v1.37 is 2.5 MB, animated day/night). Commit the
  original as published; the thumbnail is what the README displays.
- `gen_gallery.py` exits with `missing image: ...` when `logos.tsv` names a file
  that is not committed yet. That is the intended signal, not a bug.
- Nothing runs in CI. There used to be a scheduled job that opened a draft PR
  when a new minor shipped; it was removed on 2026-08-27 after 64 runs that
  opened no PRs. GitHub stops scheduled workflows after 60 days without a commit,
  and this repo goes about four months between releases, so it was reliably
  asleep exactly when a release landed. It missed v1.37 that way. Watch
  https://kubernetes.io/blog/ instead.
- Thumbnail generation could run in CI if that is ever wanted: the raster path is
  pure Pillow, and only SVG sources need `rsvg-convert`.

## Rules for agents

- One logo per change. Do not bundle unrelated cleanups (header normalization,
  `.gitignore` edits, README rewording) into a logo PR; those go in separate PRs.
- Do not hand-edit the README gallery block between the `<!-- gallery:start -->`
  and `<!-- gallery:end -->` markers. Edit `logos.tsv` and rerun the script.
- Do not rewrite existing codenames. Older entries use varied wording on purpose,
  since they match the official release names.
- Do not re-encode, resize, or optimize the full-resolution image files. The
  committed original should be the official asset as published. Thumbnails are
  the only derived images, and the script owns them.
- Do not touch `kubernetes_release_logos.pdf` unless asked. It is regenerated
  manually, not per release.
- Rebase on the latest `main` before opening a PR. New entries belong at the top,
  and a stale base puts the entry in the wrong position.

## Commit authorship

Commits must be authored by the human contributor, not by an AI tool's bot
account. Bot identities that land in `main` leak into the repository's
Contributors list and can only be removed by a manual cache rebuild through
GitHub Support.

Before pushing, re-author AI-generated commits:

```bash
git commit --amend --reset-author --no-edit
# multiple commits:
git rebase <base> --exec 'git commit --amend --reset-author --no-edit'
```

Verify with `git log --format='%an <%ae>' -n 5`. `pr-author-check.yml` fails the
PR and posts a comment when it finds a `[bot]` author outside the allowlist
(`dependabot`, `github-actions`, `renovate`).
