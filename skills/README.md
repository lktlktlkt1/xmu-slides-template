# PDF to Bilibili — Skill Suite

6 skills + 1 template for the `paper-to-bilibili` pipeline:

```
PDF paper → MinerU Markdown → SUSTech Beamer slides → narrated MP4 → Bilibili upload
```

Every skill is a plain directory holding `SKILL.md` (YAML frontmatter: `name` +
`description`) plus its scripts/assets — the layout shared by all three agents:

| Agent | Install location | Command (from this repo root) |
|-------|------------------|-------------------------------|
| Claude Code | `~/.claude/skills/<name>/` or project `.claude/skills/` | `cp -r skills/* ~/.claude/skills/` |
| Codex CLI | `~/.codex/skills/<name>/` or project `.codex/skills/` | `cp -r skills/* ~/.codex/skills/` |
| OMP (Oh My Pi) | `<working root>/.omp/skills/<name>/` | `cp -r skills/* .omp/skills/` |

Notes:

- Extra frontmatter keys (`user-invocable`, `argument-hint`) are ignored by
  agents that don't define them.
- Several SKILL.md files reference `<SKILLS_DIR>/<name>/scripts/...`, where
  `<SKILLS_DIR>` is the directory that contains the installed skill folders.
- On Windows, copy with Explorer / `xcopy /E /I skills <target>`; symlinks need
  admin rights, so prefer copies unless your agent resolves symlinks.

---

## Configuration

No file editing needed to change machines — all machine-specific values are
controlled by environment variables:

| Env var | Meaning | Default |
|---------|---------|---------|
| `PP_ROOT` | Pipeline working root (contains `论文分享/`) | current working directory |
| `MINERU_PYTHON` | Python interpreter with MinerU installed | `python` |
| `PP_PYTHON` | Python interpreter for pipeline scripts | `python` |
| `LUALATEX` | Full path to `lualatex` | resolved from PATH |
| `POPPLER_DIR` | Directory containing `pdftoppm` | resolved from PATH |
| `PRESENTER` | Presenter name for slide `\author` | ask the user |
| `INSTITUTE` | Institute string for slide `\institute` | ask the user |

Example:

```bash
export PP_ROOT=/path/to/my/pipeline          # contains 论文分享/
export MINERU_PYTHON=/path/to/mineru-env/bin/python
export PRESENTER="Jane Doe"
export INSTITUTE="Example University, China"
```

---

## Requirements

- **Python 3.10+** (`python` on PATH; if missing, use `py -3` on Windows)
- **TeX Live** (or MiKTeX) with `lualatex` and `pdftoppm` on PATH
- **ffmpeg** (video assembly)
- **edge-tts** — `python -m pip install edge-tts`
- **biliup** (uploader only) — `python -m pip install biliup`
- **MinerU** venv (`pdf-to-markdown`, `paper-to-beamer`, `pdf-to-bilibili`):

  ```bash
  uv venv --python 3.12 "<your-env>"
  uv pip install --python "<your-env>/Scripts/python.exe" torch torchvision --index-url https://download.pytorch.org/whl/cu124
  uv pip install --python "<your-env>/Scripts/python.exe" -U "mineru[core]"
  "<your-env>/Scripts/mineru-models-download.exe" -s huggingface -m pipeline
  export MINERU_PYTHON="<your-env>/Scripts/python.exe"   # Windows
  # export MINERU_PYTHON="<your-env>/bin/python"          # macOS / Linux
  ```

  No NVIDIA GPU? Install CPU torch (`uv pip install --python ... torch torchvision`
  without `--index-url`) — the pipeline still runs, just slower.

- **Bilibili cookies**: stored at `~/.bilibili/cookies.json` (cross-user).
  First upload triggers a QR-code login — scan with the Bilibili mobile app.

---

## Pipeline skills (in order)

| Skill | Role |
|-------|------|
| `pdf-to-markdown` | PDF → clean Markdown (MinerU, GPU pipeline) |
| `paper-to-beamer` | Markdown → compiled SUSTech Beamer slides |
| `pdf-slides-to-video` | PDF slides → narrated MP4 (edge-tts) |
| `bilibili-video-uploader` | MP4 + metadata → Bilibili upload (biliup) |
| `pdf-to-bilibili` | Orchestrator: `slides` / `video` / `bilibili` modes |
| `sustech-beamer-theme-fix` | Fix stale template copies missing `\setsource` etc. |

---

## Verification

```bash
# 1. Python works
python -c "print('OK')"

# 2. Working root
ls "$PP_ROOT/"

# 3. MinerU importable
$MINERU_PYTHON -c "import torch, mineru; print('OK')"

# 4. TeX tools
lualatex --version
pdftoppm -v

# 5. ffmpeg
ffmpeg -version

# 6. edge-tts / biliup
python -c "import edge_tts; print('OK')"
python -c "import biliup; print('OK')"
```

---

## Deployment layout

```
<PP_ROOT>/
+- .omp/skills/                     # OMP install target (or ~/.claude/skills, ~/.codex/skills)
|   +- pdf-to-bilibili/
|   +- paper-to-beamer/
|   +- pdf-slides-to-video/
|   +- bilibili-video-uploader/
|   +- pdf-to-markdown/
|   +- sustech-beamer-theme-fix/
+- sustech-slides-template/         # this repository (template checkout)
|   +- main_template.tex
|   +- sustech-theme/
|   +- latexmkrc
+- 论文分享/                        # pipeline output lands here
    +- <VENUE> - <TITLE>/
        +- slides-beamer/
        +- video/
        +- poster/
        +- md_output/
```

---

## Rebranding (optional)

The template ships with SUSTech branding (`sustech-slides-template/`). To
rebrand for another institution:

1. **Name** — in `main_template.tex`: `\institute[...]` → your institution.
2. **Logo** — replace `sustech-theme/assets/sustech_logo.png` (PNG with alpha,
   ~1600px wide, keep the filename) or update `\logo{}` in
   `beamerthemesustech.sty`.
3. **Colors** — edit `sustech-theme/beamercolorthemesustech.sty`
   (`sustechorange` primary, `sustechdark` header, `sustechgrey` subtle,
   `sustechlight` table rows). New palettes can also be registered as
   `\sustechscheme{<name>}` schemes.
4. **Presenter / institute** — set `PRESENTER` / `INSTITUTE` (see
   Configuration); `paper-to-beamer` reads them for `\author` / `\institute`.
