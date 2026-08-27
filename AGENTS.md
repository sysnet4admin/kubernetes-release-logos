# AGENTS.md

Guidance for AI coding agents working in this repository.
This is the single source of truth; `CLAUDE.md` only imports this file.

## What this repository is

A flat collection of Kubernetes release logos. Each minor release has one image
file at the repo root named `vX.YY.<ext>` (`.png`, `.svg`, or `.jpeg`), and
`README.md` lists every release newest-first.

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
| `vX.YY.<ext>` | Full-resolution logo for one minor release, at the repo root. |
| `kubernetes_release_logos.pdf` | Combined PDF of the collection. |
| `CONTRIBUTING.md` | Human-facing contribution guide. |
| `.github/workflows/check-new-release.yml` | Daily job that opens a draft PR when a new k8s minor ships. |
| `.github/workflows/pr-author-check.yml` | Fails a PR when commits are authored by a bot account. |

## Adding a release logo

This repo tracks every Kubernetes minor release, so this is a recurring task.

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
curl -sSL -o "v${minor}.svg" "${blog_url%/}/k8s-v${minor}.svg"
```

Confirm it downloaded as SVG and not an HTML error page:

```bash
file "v${minor}.svg"   # expect: SVG Scalable Vector Graphics image
```

If the blog does not ship an SVG, fall back to the PNG on the post or to
[`sig-release`](https://github.com/kubernetes/sig-release/tree/master/releases)
under `releases/release-<X.YY>/`, and name the file with the matching extension.

### 3. Add the row and regenerate

Add one row to `logos.tsv`, directly under the header line:

```
vX.YY<TAB><Codename><TAB>vX.YY.<ext>
```

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

Requirements: `rsvg-convert` (`brew install librsvg`) for SVG sources, and `sips`
for raster sources, which ships with macOS.

### Where the best asset lives (audited 2026-08-27)

Two upstream repositories carry release logos, and neither is complete:

- `kubernetes/sig-release` under `releases/release-X.YY/`. Early releases keep a
  bare file at the top of that directory; from v1.24 on the good assets sit in a
  `logo/` (or `logos/`) subdirectory, which is easy to miss. This is where the
  highest-resolution and vector masters usually are.
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

- v1.21 is capped at 250x260 (`logos/globe_250px.png`, 40 KB), designed by Aravind
  Sekar. It is the only asset in either repository, and the Wayback Machine shows
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

### Known quirks

- Logo SVGs can be large (v1.37 is 2.5 MB, animated day/night). Commit the
  original as published; the thumbnail is what the README displays.
- `check-new-release.yml` writes a placeholder row with a `.svg` extension and
  does not commit an image. `gen_gallery.py` fails with `missing image: ...`
  until the real file lands, which is the intended signal, not a bug.
- Thumbnail generation is not wired into CI. The raster path uses `sips`, which
  is macOS-only, so a CI step would need an ImageMagick fallback first.

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
