# PDF to Bilibili — Skill Suite Adaptation Guide

This directory contains 7 skills + 1 template for the `paper-to-bilibili` pipeline.
Every skill was authored for a specific machine and institution. To use it
on your own setup, update the items below before running any pipeline phase.

---

## Install for your agent

Each skill is a plain directory holding `SKILL.md` (YAML frontmatter: `name` +
`description`) plus its scripts/assets — the layout all three agents share:

| Agent | Install location | Command (from this repo root) |
|-------|------------------|-------------------------------|
| Claude Code | `~/.claude/skills/<name>/` or project `.claude/skills/` | `cp -r skills/* ~/.claude/skills/` |
| Codex CLI | `~/.codex/skills/<name>/` or project `.codex/skills/` | `cp -r skills/* ~/.codex/skills/` |
| OMP (Oh My Pi) | `<working root>/.omp/skills/<name>/` (see P2 below) | `cp -r skills/* .omp/skills/` |

Notes:
- Extra frontmatter keys (`user-invocable`, `argument-hint`) are ignored by
  agents that don't define them.
- Several SKILL.md files reference `.omp/skills/<name>/scripts/...` relative to
  the working root (P2); after copying to that location they resolve as written.
- On Windows, copy with Explorer / `xcopy /E /I skills <target>`; symlinks need
  admin rights, so prefer copies unless your agent resolves symlinks.

---

## Quick-reference personalization matrix

| # | What | Where | Original value | Your value |
|---|------|-------|---------------|------------|
| P1 | Python 3.10 path | All SKILL.md files | `C:/Users/disco/AppData/Local/Programs/Python/Python310/python.exe` | `...` |
| P2 | Working directory | paper-to-beamer, pdf-slides-to-video, pdf-to-bilibili, bilibili-video-uploader | `D:/Envs/Paper_Survey_Env` | `...` |
| P3 | MinerU venv | pdf-to-markdown, paper-to-beamer, pdf-to-bilibili | `C:\Users\disco\.mineru-env` | `...` |
| P4 | Claude skills path | pdf-to-markdown, paper-to-beamer | `C:\Users\disco\.claude\skills` | `...` |
| P5 | OMP skills path | markdown-to-video-cover, pdf-slides-to-video, bilibili-video-uploader | `.omp/skills/` (relative to P2) | `...` |
| P6 | TeX Live | markdown-to-video-cover, pdf-slides-to-video | `C:\texlive\2024\bin\windows\` | `...` |
| I1 | Institution name | main_template.tex, paper-to-beamer | `SUSTech, China` | `...` |
| I2 | Institution logo | sustech-theme/assets/sustech_logo.png | SUSTech logo (1630x757 PNG) | Replace file |
| I3 | Theme colors | sustech-theme/beamercolorthemesustech.sty | Orange #E36E2D + dark #00343F | Edit hex values |
| I4 | Theme name | beamerthemesustech.sty, all SKILL.md | `sustech` -> `\usetheme{sustech}` | Keep or rename |
| B1 | Bilibili cookies | bilibili-video-uploader | `%USERPROFILE%\.bilibili\cookies.json` | Same (cross-user) |
| R1 | Presenter name | paper-to-beamer | `Haobo Yang` | `...` |

---

## Category P -- Paths and machine setup

### P1 -- Python 3.10 path

Used by `bilibili-video-uploader`, `markdown-to-video-cover`, and `pdf-to-bilibili`.
These skills hardcode a direct `.exe` path because `py` launcher routes through
broken WSL on the original machine.

**To update**: find-replace across all SKILL.md files:
- Old: `C:/Users/disco/AppData/Local/Programs/Python/Python310/python.exe`
- Old (backslash): `C:\Users\disco\AppData\Local\Programs\Python\Python310\python.exe`
- New: your Python 3.10+ path, or just `python` / `py` if your PATH is clean.

Affected files: `bilibili-video-uploader/SKILL.md`, `markdown-to-video-cover/SKILL.md`,
`pdf-to-bilibili/SKILL.md`.

### P2 -- Working directory (paper output root)

All pipeline output lands under this directory (convention: `<root>/论文分享/<VENUE> - <TITLE>/`).

**To update**: find-replace across all SKILL.md files:
- Old: `D:/Envs/Paper_Survey_Env`
- Old (backslash): `D:\Envs\Paper_Survey_Env`
- New: your own project root.

Also update the `bilibili-video-uploader` upload.py path references
(e.g. `D:/Envs/Paper_Survey_Env/.omp/skills/bilibili-video-uploader/scripts/upload.py`
-> `<your_root>/.omp/skills/bilibili-video-uploader/scripts/upload.py`).

### P3 -- MinerU virtual environment

The `pdf-to-markdown` skill needs a dedicated Python 3.12 venv with MinerU installed.

**To create**:
```
uv venv --python 3.12 "C:\Users\<YOU>\.mineru-env"
uv pip install --python "C:\Users\<YOU>\.mineru-env\Scripts\python.exe" torch torchvision --index-url https://download.pytorch.org/whl/cu124
uv pip install --python "C:\Users\<YOU>\.mineru-env\Scripts\python.exe" -U "mineru[core]"
"C:\Users\<YOU>\.mineru-env\Scripts\mineru-models-download.exe" -s huggingface -m pipeline
```

Then update all references from `C:\Users\disco\.mineru-env` to your path in:
- `pdf-to-markdown/SKILL.md`
- `paper-to-beamer/SKILL.md`
- `pdf-to-bilibili/SKILL.md`

If you don't have an NVIDIA GPU, install the CPU-only torch:
`uv pip install --python "..." torch torchvision` (omit `--index-url`).

### P4 -- Claude skills path

Some skills reference `C:\Users\disco\.claude\skills\pdf-to-markdown\convert.py`.
This is the old Claude-internal skills directory.

**To update**: copy `pdf-to-markdown/convert.py` and `pdf-to-markdown/SKILL.md`
to wherever your agent reads skills from (e.g. `~/.claude/skills/`,
`~/.omp/skills/`, or your framework's equivalent). Then update references in:
- `pdf-to-markdown/SKILL.md`
- `paper-to-beamer/SKILL.md`
- `pdf-to-bilibili/SKILL.md`

### P5 -- OMP skills path

The pipeline's sub-skills are invoked via relative paths from the working directory:
`.omp/skills/pdf-slides-to-video/scripts/`, `.omp/skills/bilibili-video-uploader/scripts/`, etc.

Place the extracted skill directories under `<P2>/.omp/skills/` to match.
If your agent framework uses a different layout, update the `sys.path.insert` lines
in `pdf-slides-to-video/SKILL.md` and the `upload.py` paths in
`bilibili-video-uploader/SKILL.md`.

### P6 -- TeX Live

Used by `markdown-to-video-cover` (lualatex, pdftoppm) and `pdf-slides-to-video` (pdftoppm).

**To update**: find your TeX Live install:
```
where lualatex
where pdftoppm
```
Update the paths in:
- `markdown-to-video-cover/SKILL.md` -- lualatex version check, pdftoppm fallback
- `pdf-slides-to-video/SKILL.md` -- pdftoppm path

If you use MiKTeX instead of TeX Live, update the paths and verify `lualatex --version` works.
On macOS/Linux, the tools are typically on PATH -- remove the hardcoded Windows paths.

---

## Category I -- Institution branding

The Beamer template uses SUSTech branding. To rebrand for another institution:

### I1 -- Institution name

Edit `sustech-slides-template/main_template.tex`, find the `\institute` line:
```latex
\institute[SUSTech]{Southern University of Science and Technology}
```
Replace with your institution.

### I2 -- Logo

Replace `sustech-slides-template/sustech-theme/assets/sustech_logo.png` with your
institution's logo. Requirements:
- PNG format with transparency (alpha channel)
- ~1600px wide (the original is 1630x757)
- Keep the filename `sustech_logo.png` or update the `\logo{}` macro in
  `beamerthemesustech.sty` to reference your filename.

The logo appears on the title page and section divider slides.

### I3 -- Theme colors

Edit `sustech-slides-template/sustech-theme/beamercolorthemesustech.sty`.
The SUSTech palette:
```
Orange (primary):   HTML #E36E2D   --   \definecolor{sustechorange}{HTML}{E36E2D}
Dark (header bg):   HTML #00343F   --   \definecolor{sustechdark}{HTML}{00343F}
Grey (subtle):      HTML #75787B   --   \definecolor{sustechgrey}{HTML}{75787B}
Light grey (rows):  HTML #EBEBEB   --   \definecolor{sustechlight}{HTML}{EBEBEB}
```

Replace with your institution's brand colors. Common palettes:

| Institution | Primary | Dark | Notes |
|-------------|---------|------|-------|
| MIT | #A31F34 | #000000 | Cardinal red + black |
| Stanford | #8C1515 | #2E2D29 | Cardinal + dark grey |
| Berkeley | #003262 | #FDB515 | Blue + California gold |
| ETH Zurich | #215CAF | #000000 | Blue + black |
| Tsinghua | #660874 | #000000 | Purple + black |
| PKU | #8B0012 | #000000 | Dark red + black |
| CMU | #990000 | #000000 | Carnegie red + black |

If your institution has no official LaTeX theme, pick 4 colors:
1. **Primary** -- used for `\shl{}`, `\keyword{}`, `\brandemph{}`, progress bar
2. **Dark** -- used for header bar, footer, `\section` titles
3. **Grey** -- used for subtle text, `\figcap{}` labels
4. **Light** -- used for alternating table rows

### I4 -- Theme name (optional)

If you want to rename the theme from `sustech` to your institution's abbreviation:
1. Rename files:
   - `beamerthemesustech.sty` -> `beamertheme<short>.sty`
   - `beamercolorthemesustech.sty` -> `beamercolortheme<short>.sty`
   - `beamerthemesustech-elements.sty` -> `beamertheme<short>-elements.sty`
   - Directory: `sustech-theme/` -> `<short>-theme/`
2. Inside `beamertheme<short>.sty`, update the `\usecolortheme{sustech}` line
   and `\useinnertheme{sustech}` / `\useoutertheme{sustech}` references.
3. In `beamercolortheme<short>.sty`, rename color definitions if desired
   (e.g. `sustechorange` -> `<short>primary`).
4. Update all SKILL.md references from `sustech-theme/` to `<short>-theme/`.
5. In `main_template.tex`, change `\usetheme{sustech}` -> `\usetheme{<short>}`.
6. Update `paper-to-beamer/SKILL.md` references to the theme name.

---

## Category B -- Bilibili

### B1 -- Cookies

Cookies are stored at `%USERPROFILE%\.bilibili\cookies.json` -- this is already
cross-user (uses the Windows env var). On macOS/Linux the path convention differs.

**First upload attempt** will trigger a QR-code login flow. Scan with the Bilibili
mobile app. The CLI wrapper at `bilibili-video-uploader/scripts/upload.py` handles
this via `--login`.

**Prerequisites**: Python 3.10+ with `biliup` installed:
```
pip install biliup
```

No personalization needed if you use the wrapper script -- it auto-resolves paths.

---

## Category R -- Reporter/presenter

### R1 -- Presenter name

The `paper-to-beamer` skill defaults the presenter to "Haobo Yang" in the
`\author` field of generated Beamer slides.

**To update**: edit `paper-to-beamer/SKILL.md` line 136, change the default:
Replace `"Haobo Yang"` with your name.

Also update the Q&A slide presenter info (in the template filling instructions,
around line 242-243 of paper-to-beamer/SKILL.md).

---

## Verification after personalization

Run these checks to confirm the adaptation succeeded:

```bash
# 1. Python path works
<P1> -c "print('OK')"

# 2. Output directory exists
ls "<P2>/"

# 3. MinerU is importable
<P3>/Scripts/python.exe -c "import mineru; print('OK')"

# 4. TeX Live is on PATH (or verify hardcoded path)
lualatex --version
pdftoppm -v

# 5. ffmpeg is available
ffmpeg -version

# 6. edge-tts is importable
python -c "import edge_tts; print('OK')"

# 7. biliup is importable
python -c "import biliup; print('OK')"
```

## Directory layout after deployment

Expected layout after extracting this zip and personalizing:

```
<P2>/                           # your working directory
+- .omp/
|   +- skills/
|       +- pdf-to-bilibili/
|       +- paper-to-beamer/
|       +- markdown-to-video-cover/
|       +- pdf-slides-to-video/
|       +- bilibili-video-uploader/
+- sustech-slides-template/    # (or <short>-theme/ after I4)
|   +- main_template.tex
|   +- sustech-theme/
|   |   +- beamerthemesustech.sty
|   |   +- beamercolorthemesustech.sty
|   |   +- beamerthemesustech-elements.sty
|   |   +- assets/sustech_logo.png
|   +- latexmkrc
|   +- ...
+- 论文分享/                   # pipeline output lands here
    +- <VENUE> - <TITLE>/
        +- slides-beamer/
        +- video/
        +- poster/
        +- md_output/
```

The `pdf-to-markdown` skill (convert.py + SKILL.md) should also be copied to
`<P4>/pdf-to-markdown/` (or wherever your agent reads skills from).
