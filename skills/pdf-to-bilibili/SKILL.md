---
name: pdf-to-bilibili
description: |
  Full pipeline: PDF paper → MinerU → Beamer slides → narrated MP4 → Bilibili upload.
  Three modes: slides, video, bilibili. Each paper processed by one subagent
  for maximum KV cache hit rate. Main agent coordinates only — never writes content.
user-invocable: true
argument-hint: "<mode> <pdf_path>"
---

# PDF → Bilibili Full Pipeline

Single unified pipeline from a paper PDF to Bilibili upload. Designed for one
subagent per paper — the agent reads this one file and follows the phases for
the requested mode.

**Python path**: ALWAYS use `python` (Python 3.10+; if `python` is missing, use `py -3`).

---

## Modes

- `slides` — Phase 1→2→3→3.5. Output: compiled Beamer PDF.
- `video` — Phase 1→2→3→3.5→4a. Output: `% NARRATION:` comments in annotated .tex. Main agent does TTS+assembly.
- `bilibili` — Phase 1→2→3→3.5→4a→5. Output: Bilibili BV号.

---

## Phase 1 — Setup directory

1. Accept `<pdf_path>` as input.
2. Derive a short directory name from the PDF filename or paper title:
   - Strip `.pdf`, extract venue + year + short title.
   - Convention: `{VENUE} - {SHORT_TITLE}` or `arXiv {YEAR} - {SHORT_TITLE}`.
3. Create `$PP_ROOT/论文分享/<DIR_NAME>/` and copy the PDF there.
4. Store `<DIR_NAME>` for all subsequent phases.

---

## Phase 2 — MinerU

Run MinerU to extract markdown from the PDF:

```bash
"$MINERU_PYTHON" \
  "<SKILLS_DIR>/pdf-to-markdown/convert.py" \
  "$PP_ROOT/论文分享/<DIR_NAME>/<pdf_filename>.pdf" \
  "$PP_ROOT/论文分享/<DIR_NAME>/md_output" \
  --lang en
```

Output lands at `md_output/<pdf_basename>/auto/<pdf_basename>.md`.
~3 min for a 12-page paper. Serial only — GPU OOM if parallel.

---

## Phase 3 — Beamer slides

### 3.1 Copy template
```bash
git clone --depth 1 https://github.com/yhbcode000/sustech-slides-template.git \
  "$PP_ROOT/论文分享/<DIR_NAME>/slides-template"
rm -rf "$PP_ROOT/论文分享/<DIR_NAME>/slides-template/.git"
```

### 3.2 Create slides-beamer
```bash
mkdir -p "$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/figures"
cp -r "$PP_ROOT/论文分享/<DIR_NAME>/slides-template/sustech-theme" \
  "$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/"
cp "$PP_ROOT/论文分享/<DIR_NAME>/slides-template/latexmkrc" \
  "$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/"
cp "$PP_ROOT/论文分享/<DIR_NAME>/slides-template/main_template.tex" \
  "$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/main.tex"
```

### 3.3 Fill main.tex
Read `md_output/<pdf_basename>/auto/<pdf_basename>.md` for paper content.
Fill ALL sections of the template: title, authors, venue, abstract, background,
related work, method (2 frames), experiment design, results (2-3 frames),
limitations, takeaways, references, Q&A. Add 3-8 appendix slides.

**Style reference**: `<TEMPLATE_DIR>/main_template.tex`

Critical rules:
- `aspectratio=1610` (16:10, NOT 16:9)
- **No two-column layouts** — figures are large/detailed; every figure on its own `[plain,c]` slide with `\fitfigure`
- **Figures on own slides** — NEVER inside `\begin{columns}`, `\begin{block}`, or next to bullets
- Write telegraphic — keyword phrases, not full sentences
- Use `\shl{…}`, `\keyword{…}`, `\brandemph{…}` for emphasis
- No overlays (`\pause`, `\onslide`)
- No `\tiny` font — minimum `\small`
- Copy figures from `md_output/<name>/auto/images/` to `slides-beamer/figures/` with semantic names

### 3.4 Compile
```bash
cd "$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer"
latexmk -xelatex main.tex
```
Copy `main.pdf` → `../<DIR_NAME>.pdf`.

Post-compile checks: grep for `Overfull \hbox`, `Undefined control sequence`. Report count.

---

## Phase 3.5 — Venue rename

Many papers are published at venues (ICML, RSS, CoRL, etc.) not obvious from the filename.
Extract the real venue from `\setsource{Venue}{Year}` in the compiled .tex preamble.

If the extracted venue differs from the current directory prefix (e.g. "arXiv" → "ICML 2023"):
```bash
mv "$PP_ROOT/论文分享/<OLD>" "$PP_ROOT/论文分享/<VENUE> <YEAR> - <SHORT>"
```
Also rename `<DIR_NAME>.pdf` to match.

**Short title must be recognizable** — 4+ chars, paper acronym or 2+ keywords.
Never use fragments like "AI", "R1", "WM".

---

## Phase 4a — Write narrations (subagent, no TTS)

Only for `video` and `bilibili` modes. The subagent writes `% NARRATION:` comments
but does NOT run TTS or ffmpeg. The main agent batch-processes those later.

### 4a.1 Set up video directory
```bash
mkdir -p "$PP_ROOT/论文分享/<DIR_NAME>/video/video_frames"
cp "$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/main.tex" \
  "$PP_ROOT/论文分享/<DIR_NAME>/video/main_with_narration.tex"
```

### 4a.2 Parse frames for context
Use the Python helper to understand slide structure:
```bash
python -c "
import sys; sys.path.insert(0, r'<SKILLS_DIR>/pdf-slides-to-video/scripts')
from slides_to_video import parse_beamer_frames, parse_beamer_preamble
preamble = parse_beamer_preamble(r'$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/main.tex')
frames = parse_beamer_frames(r'$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/main.tex')
for f in frames:
    print(f'Slide {f[\"page_num\"]}: [{f.get(\"is_plain\",\"\")}] {f[\"title\"][:60]}')
    for item in f.get('items', []):
        print(f'  {item[:80]}')
import json
with open(r'$PP_ROOT/论文分享/<DIR_NAME>/video/frames_data.json', 'w', encoding='utf-8') as f:
    json.dump({'preamble': preamble, 'frames': frames}, f, ensure_ascii=False)
"
```

### 4a.3 Write narrations
For EACH content frame, write a `% NARRATION:` comment directly after the `\end{frame}` line
in `video/main_with_narration.tex`. Edit the file with insertion operations.

**Narration rules** (audio-only audience):
- OUTPUT: 简体中文. English technical terms kept inline.
- NEVER say "这一页/如图所示/本页" — listener cannot see slides.
- Expand bullets into complete explanatory sentences.
- Title: 40-60 words. TOC: 40-60 words. Content: 150-250 words. Figures: 120-200 words.
  References: 40-60 words. Closing: 20-40 words.

### 4a.4 VALIDATION GATE — Narration coverage
Before proceeding, verify EVERY frame has a narration:
```bash
python -c "
import sys; sys.path.insert(0, r'<SKILLS_DIR>/pdf-slides-to-video/scripts')
from slides_to_video import parse_beamer_frames
frames = parse_beamer_frames(r'$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/main.tex')
with open(r'$PP_ROOT/论文分享/<DIR_NAME>/video/main_with_narration.tex', 'r', encoding='utf-8') as f:
    n = sum(1 for line in f if line.strip().startswith('% NARRATION:'))
print(f'Frames: {len(frames)}, Narrations: {n}')
assert len(frames) == n, f'MISMATCH: {len(frames)} frames but {n} narrations! Fix before continuing.'
"
```

A missing narration causes ALL subsequent frames to get wrong audio (off-by-one shift).
This is a silent bug — video assembles without error but appendix A plays appendix B's audio.

---

## Phase 4a.5 — Generate poster (if md_output exists)

Only for `video` and `bilibili` modes. If the paper has `md_output/`, run the
markdown-to-video-cover skill to produce `poster/poster.png`. The video pipeline's
cover generator will automatically use this poster when available.

```bash
ls "$PP_ROOT/论文分享/<DIR_NAME>/md_output/" && (
  echo '{"cards_col1":[],"cards_col2":[],"title_font":100}' > _cover.json
  python \
    <SKILLS_DIR>/markdown-to-video-cover/scripts/generate_poster.py \
    "$PP_ROOT/论文分享/<DIR_NAME>" --data _cover.json
  rm _cover.json
) || echo "No md_output, skipping poster"
```

---

## Phase 4b — TTS + Assembly (main agent only)

The main agent runs this after all narration agents complete. Uses 8 workers by default.

```python
import sys; sys.path.insert(0, r'<SKILLS_DIR>/pdf-slides-to-video/scripts')
from slides_to_video import write_narrations_to_files, batch_tts_parallel, assemble_video, render_slides

frame_dir = r'$PP_ROOT/论文分享/<DIR_NAME>/video/video_frames'
tex = r'$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/main.tex'
anno = r'$PP_ROOT/论文分享/<DIR_NAME>/video/main_with_narration.tex'
pdf = r'$PP_ROOT/论文分享/<DIR_NAME>/slides-beamer/main.pdf'

# 1. Render slides to PNGs
render_slides(pdf, frame_dir, dpi=200)

# 2. Extract narrations to .txt files at correct PDF pages
write_narrations_to_files(frame_dir, tex, annotated_tex_path=anno)

# 3. TTS (8 workers default)
batch_tts_parallel(frame_dir, lang='zh')

# 4. Assemble MP4 (8 workers, 1.25x speedup)
assemble_video(frame_dir, r'$PP_ROOT/论文分享/<DIR_NAME>/video/<SHORT>_narrated.mp4',
               pad_sec=0.5, speed=1.25)
```

Also generate cover.png (prefers poster when available) and video_meta.json.

---

## Phase 5 — Upload to Bilibili

Only for `bilibili` mode. After Phase 4b completes, upload the narrated MP4.

**Python path**: `python` (Python 3.10+; if `python` is missing, use `py -3`):
```bash
python \
  "<SKILLS_DIR>/bilibili-video-uploader/scripts/upload.py" \
  "$PP_ROOT/论文分享/<DIR_NAME>"
```

The upload.py script:
1. Reads `video/video_meta.json` for title, tags, desc, cover
2. Builds biliup command with `--submit web`
3. Uploads MP4 + cover
4. Extracts BV号 → constructs `https://www.bilibili.com/video/<BV号>`

**Title format**: MUST be `【Venue Year】Title` (e.g. `【ICML 2023】PaLM-E`).
The `generate_metadata()` function auto-prepends this prefix from the beamer preamble.

**Error handling**:
- Rate-limit (exit 5 / error 601): wait 1 hour, retry once
- Cookie expired (exit 2): re-login via `upload.py --login`
- TLS handshake EOF: retry once (intermittent)

---

## Main agent role (batch.py)

```python
# Main agent loop
while papers_remain:
    # 1. Load state from papers.json + disk scan
    # 2. Find papers at each stage needing next phase
    # 3. Dispatch subagents (3-6 at a time for slides, 6 for narration, 10 for upload)
    # 4. Wait for completions
    # 5. Rescan disk → update state
    # 6. Handle failures: compile unfilled .tex, redispatch empty templates
    # 7. Print progress dashboard
```

The main agent NEVER writes slides, narrations, or runs TTS — it only coordinates.
