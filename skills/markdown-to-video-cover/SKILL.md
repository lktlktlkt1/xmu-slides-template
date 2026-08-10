---
name: markdown-to-video-cover
description: |
  Generate a 16:10 video-cover poster from a paper's MinerU markdown output.
  Auto-extracts title, figures, and key metrics; produces .tex, .pdf, .png.
  NOT for research/conference posters — use the gemini-poster skill instead.
  Trigger on: user asks to "make video cover", "generate poster from markdown",
  "create Bilibili cover", "md to poster", "制作视频封面", "markdown转封面",
argument-hint: "<paper_dir>"
---

# Markdown → Video Cover Poster

Converts a paper directory with `md_output/` (MinerU output) into a 16:10
video-cover poster — Gemini beamerposter theme, SUSTech colors, result-card
style with large title and bold metrics. Generates `.tex`, `.pdf`, and `.png`.

## When to use

- The user asks to "make a video cover" or "create a Bilibili cover" for a paper.
- The paper has a `md_output/` directory with MinerU markdown and images.
- Output goes into `poster/` under the paper directory.
- Best for: robotics, AI, CV, ML papers with figures and quantitative results.
- **NOT for research/conference posters** — those need structured text, references,
  and detailed methodology. Use the `gemini-poster` skill instead.

## How to run

The generator lives at `.omp/skills/markdown-to-video-cover/scripts/generate_poster.py`
and uses only Python stdlib — no dependencies.

```
C:/Users/disco/AppData/Local/Programs/Python/Python310/python.exe \
  .omp/skills/markdown-to-video-cover/scripts/generate_poster.py \
  "<paper_dir>" [--data data.json] [--title-font N] [--no-png]
```

- `paper_dir` — path to paper directory (e.g., `论文分享/CVPR 2025 - GROVE/`).
- `--data data.json` — optional JSON config with manual overrides for title, cards, figure mapping.
- `--title-font N` — override title font size in pt (default: auto-selected based on title length).
- `--no-png` — skip PNG render, only produce `.tex` + `.pdf`.

Script prints progress and the final output paths on success.

### Output layout

```
<paper_dir>/poster/
  poster.tex          # generated LaTeX source
  poster.pdf          # compiled PDF (16:10, 160×100cm)
  poster.png          # rendered PNG (150 DPI)
  figures/            # copied paper figures (fig1.jpg, fig2.jpg, ...)
  beamerthemegemini.sty
  beamercolorthemesustech.sty
```

### Auto-extraction

The script parses the MinerU markdown to extract:

- **Title**: first `# ` heading in the `.md` file.
- **Figures**: finds all `Figure N` and `Fig. N` captions (case-insensitive)
  and maps them to image files. Copies the first 6 figures to
  `poster/figures/` as `fig1.jpg`–`fig6.jpg`. Distributes across 2 columns
  (odd-numbered figures → col1, even-numbered → col2).
- **Key metrics**: regex searches the abstract and experiments for percentage
  improvements (e.g., "+25.7%") and multipliers (e.g., "8.4×"). Builds
  2-3 result cards from the top findings.
- **Project URL**: extracts any HTTP URL from the markdown header.
- **QR code**: generated from the project URL.

If auto-extraction misses data, use `--data` for manual overrides.

### JSON data format

```json
{
  "title": "Override Title",
  "venue": "CVPR 2025",
  "project_url": "https://example.com",
  "title_font": 160,
  "figures": {
    "col1": ["fig1", "fig2", "fig3"],
    "col2": ["fig4", "fig5", "fig6"]
  },
  "cards_col1": [
    { "title": "Core Idea", "lines": ["line 1", "line 2"], "after": "fig1" }
  ],
  "cards_col2": [
    { "title": "Results", "lines": ["line 1", "line 2"], "after": "fig4" }
  ],
  "figure_map": {
    "fig1": "md_output/2501.12493/auto/images/a1b2c3d4e5f6....jpg",
    "fig2": "md_output/2501.12493/auto/images/g7h8i9j0k1l2....jpg"
  }
}
```

All fields are optional — only specified fields override auto-extraction.

**`figure_map` paths are relative to the paper directory** and must include
the full MinerU output prefix: `md_output/<arxiv_id>/auto/images/HASH.jpg`.
The auto-extraction produces these via `os.path.relpath(img_path, paper_dir)`.
Do NOT use bare `"images/hash.jpg"` — images live under `md_output/`, not
at the paper root.

### Image-only cover (no text cards)

Set `cards_col1` and `cards_col2` to empty arrays for a pure-figure
cover. The script auto-extracts all figures, titles, and paths — no
`figure_map` or `figures` layout needed:

```json
{"cards_col1": [], "cards_col2": [], "title_font": 200}
```

This is the recommended mode for Bilibili video covers — the figures
carry the visual message, and the script does the rest.

To customize which figures go in which column, add the `figures` key
(but still omit `figure_map` — auto-extracted paths stay intact):

```json
{
  "cards_col1": [],
  "cards_col2": [],
  "figures": { "col1": ["fig1","fig2","fig3"], "col2": ["fig4","fig5"] }
}
```

## Preflight / setup

### 1. Check lualatex

```bash
lualatex --version
```

Expected: LuaTeX 1.18+ (TeX Live 2024). Installed at `C:\texlive\2024\bin\windows\lualatex.exe`.

### 2. Check pdftoppm

```bash
pdftoppm -v
```

If missing, install poppler-utils.

**NOTE**: `pdftoppm` must be on PATH for the script's auto-PNG step.
If the script runs but PNG is missing afterward, use the manual fallback
in Troubleshooting below. On this machine, the TeX Live pdftoppm is at
`C:\texlive\2024\bin\windows\pdftoppm.exe`.

### 3. Check templates

```bash
ls .omp/skills/markdown-to-video-cover/templates/
```


## Troubleshooting

- **"No md_output found"** → the paper directory doesn't have MinerU output.
  Run the paper-to-beamer skill first, or ensure `md_output/` exists.
- **"No figures extracted"** → the markdown doesn't have recognizable
  `Figure N` or `Fig. N` captions near image references. Use `--data`
  with a `figure_map` to specify images manually (see JSON format above).
- **"lualatex: command not found"** → TeX Live not on PATH. Use full path
  `C:\texlive\2024\bin\windows\lualatex.exe`.
- **PDF has no images** → figure paths in the generated `.tex` may be wrong.
  Check `poster/poster.tex` figure paths against `poster/figures/`.
- **Title too long, overflows headline** → reduce with `--title-font 180`.
  Shorter titles auto-use 260pt, longer ones 200pt.
- **vbox overflow** → expected. The video-cover style fills the page
  aggressively. Content below the page edge is clipped in the PDF but
  the poster is designed for thumbnail use where overflow is acceptable.
- **"source not found" warnings for figures in `--data` mode** → the
  `figure_map` paths are wrong. They must include the full MinerU prefix:
  `md_output/<arxiv_id>/auto/images/HASH.jpg`, not bare `images/HASH.jpg`.
  The images live under `md_output/`, not at the paper root. Use
  `ls md_output/*/auto/images/` to find the correct prefix.

- **poster.png missing after script completes** → the auto-PNG step failed
  because `pdftoppm` was not found on PATH or the rename from `poster-1.png`
  failed. **MUST fix this before the bilibili uploader runs** — it requires
  `poster/poster.png` to generate the video cover. Manual fallback:

  ```bash
  # cwd: <paper_dir>/poster/
  "C:/texlive/2024/bin/windows/pdftoppm.exe" -png -r 300 -singlefile poster.pdf poster
  ```

  This produces `poster.png` directly. Verify with `ls -la poster.png`.
  The bilibili uploader auto-resizes `poster/poster.png` to 1920×1200
  as `video/cover.png` before upload — no manual cover step needed.
