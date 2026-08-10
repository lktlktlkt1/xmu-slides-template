---
name: pdf-slides-to-video
description: |
  Convert PDF slides (or Beamer .tex source) into a narrated MP4 video.
  Each slide gets a detailed spoken explanation — self-contained so a listener
  understands the paper without watching. Uses edge-tts for lightweight,
  cloud-free speech synthesis. Trigger on: "slides to video", "paper to video",
  "make video from slides", "narrate slides", "convert slides to mp4".
user-invocable: true
argument-hint: "<paper_directory>"
---

# PDF Slides → Narrated Video Pipeline

Given a paper directory containing `slides-beamer/` (with `main.tex` and `main.pdf`)
and optionally `md_output/` (MinerU markdown), create a `video/` subdirectory with
the narrated MP4, `cover.png`, and `video_meta.json` for Bilibili upload.

**Directory layout**:
```
论文分享/<VENUE> - <TITLE>/
  slides-beamer/      input: main.tex, main.pdf, figures/
  md_output/          input (optional): markdown for richer narration context
  video/              output (created by this skill)
    video_frames/     intermediate PNGs + MP3s + TXTs (kept for debugging)
    <paper>_narrated.mp4
    cover.png
    video_meta.json
```
**Python runtime**: Python 3.12, managed via `uv`.
**Bash runtime**: Git Bash. Working directory set per-block via `cwd`.

---

## Phase 1 — Preflight

1. Check ffmpeg: `ffmpeg -version`. If missing (install via admin PowerShell):
   ```powershell
   Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -Command "choco install ffmpeg -y"'
   ```

2. Check edge-tts: `py -c "import edge_tts"`. If missing: `py -m pip install edge-tts`

3. Verify `pdftoppm`: `C:\texlive\2024\bin\windows\pdftoppm.exe`

4. Verify Python packages: `fitz` (PyMuPDF), `pdf2image`, `PIL` (Pillow) — all pre-installed.
## Phase 2 — Resolve input

1. Accept `$ARGUMENTS` — a paper directory containing `slides-beamer/main.tex` + `main.pdf`.
2. Set paths:
   - `PAPER_DIR` = `$ARGUMENTS`
   - `TEX_PATH` = `<PAPER_DIR>/slides-beamer/main.tex`
   - `PDF_PATH` = `<PAPER_DIR>/slides-beamer/main.pdf`
   - `VIDEO_DIR` = `<PAPER_DIR>/video/`
   - `FRAME_DIR` = `<VIDEO_DIR>/video_frames/`
   - `<paper_name>` from dir basename: `RSS 2026 - LDA-1B` -> `LDA-1B`
3. Create output directory: `mkdir -p "<VIDEO_DIR>/video_frames"`
4. If `main.pdf` missing, compile: `cd <PAPER_DIR>/slides-beamer && latexmk -xelatex main.tex`

---

## Phase 3 — Extract slides to images

```bash
# cwd: D:\Envs\Paper_Survey_Env
py -c "
import sys; sys.path.insert(0, r'.omp\skills\pdf-slides-to-video\scripts')
from slides_to_video import render_slides
paths = render_slides(r'<PDF_PATH>', r'<FRAME_DIR>', dpi=200)
print(f'Rendered {len(paths)} slides')
"
```

---

## Phase 4 — Copy .tex and author narrations

Parse frames for context, copy `main.tex` to `<VIDEO_DIR>/main_with_narration.tex`,
then **directly write** Chinese narration as `% NARRATION:` comments after each `\end{frame}`.
**Do NOT use `completion()`** — write narrations yourself from paper knowledge.

```bash
# cwd: D:\Envs\Paper_Survey_Env
# 1. Parse frames to understand slide content
py -c "
import sys, json
sys.path.insert(0, r'.omp\skills\pdf-slides-to-video\scripts')
from slides_to_video import parse_beamer_frames, parse_beamer_preamble
preamble = parse_beamer_preamble(r'<TEX_PATH>')
frames = parse_beamer_frames(r'<TEX_PATH>')
for f in frames:
    print(f'Slide {f[\"page_num\"]}: [{f.get(\"is_plain\",\"\")}] {f[\"title\"][:60]}')
    for item in f.get('items', []):
        print(f'  {item[:80]}')
    if f.get('callout'): print(f'  CALL: {f[\"callout\"][:80]}')
with open(r'<VIDEO_DIR>/frames_data.json', 'w', encoding='utf-8') as f:
    json.dump({'preamble': preamble, 'frames': frames}, f, ensure_ascii=False)
"

# 2. Copy .tex source
cp "<TEX_PATH>" "<VIDEO_DIR>/main_with_narration.tex"
```

3. Read the frames output and `md_output/<name>.md` (if available) for paper context.
4. For each frame, write a Chinese narration **directly into the .tex file** as `% NARRATION: <text>` on the line after `\end{frame}`.

**Narration rules** (audio-only audience, self-contained):
+- OUTPUT: 简体中文. English technical terms (MT3, BC, alignment, open-loop replay, etc.) kept inline.
+- NEVER say "这一页/如图所示/本页" — listener cannot see slides.
+- Expand bullet points into complete explanatory sentences.
+- Figure slides: describe sub-panels, axes, trends, numbers — translate English markdown captions into Chinese.
+- Title slide: 40-60 words. TOC: 40-60 words. Content: 150-250 words. Figures: 120-200 words. References: 40-60 words. Closing: 20-40 words.

**Figure slide context from markdown** (read `<PAPER_DIR>/md_output/<name>/auto/<name>.md`):
Extract figure captions and surrounding paragraphs for each figure slide — sub-panel labels, experimental numbers, trends, failure-cause percentages. The markdown is in English; translate into natural Chinese.

5. After editing, the `.tex` file should have `% NARRATION:` comments after every `\end{frame}`.
6. **VALIDATION GATE — Narration coverage**: Before Phase 5, verify EVERY frame has a narration.
   A missing narration causes ALL subsequent frames to get wrong audio (off-by-one shift).
   This is a silent bug — video assembles without error but appendix A plays appendix B's audio.

   ```bash
   py -c "
   import sys; sys.path.insert(0, r'.omp\skills\pdf-slides-to-video\scripts')
   from slides_to_video import parse_beamer_frames
   frames = parse_beamer_frames(r'<TEX_PATH>')
   with open(r'<VIDEO_DIR>/main_with_narration.tex', 'r', encoding='utf-8') as f:
       n = sum(1 for line in f if line.strip().startswith('% NARRATION:'))
   print(f'Frames: {len(frames)}, Narrations: {n}')
   assert len(frames) == n, f'MISMATCH: {len(frames)} frames but {n} narrations! Fix missing narrations before continuing.'
   "
   If assertion fails, re-read the .tex and add the missing `% NARRATION:` comment.
   NEVER proceed to TTS with a mismatch — the off-by-one bug is unrecoverable after assembly.

7. Then extract narrations into JSON and `.txt` files (see Phase 5).
## Phase 5 — Extract narrations to JSON and .txt files

Parse `% NARRATION:` comments from the annotated `.tex` and write individual `.txt` files
at the CORRECT PDF page positions. The `extract_narrations_from_tex` function now uses
**position-based matching** — each narration is matched to its nearest preceding
`\end{frame}` line, so missing/extra narrations don't shift subsequent frame mappings.
Section divider pages from `\AtBeginSection` are accounted for by `get_page_plan()`.

```bash
# cwd: D:\Envs\Paper_Survey_Env
py -c "
import sys, json
sys.path.insert(0, r'.omp\skills\pdf-slides-to-video\scripts')
from slides_to_video import extract_narrations_from_tex, write_narrations_to_files

orig_tex = r'<TEX_PATH>'
anno_tex = r'<VIDEO_DIR>/main_with_narration.tex'
frame_dir = r'<FRAME_DIR>'

# Extract narrations for JSON
narrations = extract_narrations_from_tex(anno_tex)
with open(r'<VIDEO_DIR>/narrations.json', 'w', encoding='utf-8') as f:
    json.dump(narrations, f, ensure_ascii=False, indent=2)

# Write .txt files at correct PDF page positions (handles section pages)
result = write_narrations_to_files(frame_dir, orig_tex, annotated_tex_path=anno_tex)
print(f'Extracted {result[\"count\"]} narrations to {result[\"frame_count\"]} frame pages')
if result['section_pages']:
    print(f'Section pages (will be silent): {result[\"section_pages\"]}')
"
```

The `write_narrations_to_files` function uses `get_page_plan()` to determine which PDF pages are section dividers (from `\AtBeginSection`) and which are content frames. `.txt` files are written ONLY for content frame pages, at their correct PDF page numbers. Section divider pages get no `.txt` file — they will be silent in the final video.

Verify: `<FRAME_DIR>/` now has `.txt` files at the correct PDF page numbers (e.g. `slide_005.txt` instead of `slide_004.txt` if a section page intervenes), plus `<VIDEO_DIR>/narrations.json`.
## Phase 6 — Parallel TTS batch

Uses **edge-tts** (Microsoft Edge TTS, free, no API key needed).
Run all slides in parallel with `ThreadPoolExecutor` — each edge-tts call is I/O-bound and independent.

**Voices**:
+- Chinese: `zh-CN-XiaoxiaoNeural` (young female, clear articulation)
+- English: `en-US-AriaNeural` (neutral female, professional)

**Parallel TTS** (8 workers, ~3× speedup vs sequential):

```bash
# cwd: D:\Envs\Paper_Survey_Env
py -c "
import sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, r'.omp\skills\pdf-slides-to-video\scripts')
from slides_to_video import tts_slide
frame_dir = r'<FRAME_DIR>'
tasks = []
for i in range(1, 23):
    txt = os.path.join(frame_dir, f'slide_{i:03d}.txt')
    mp3 = os.path.join(frame_dir, f'slide_{i:03d}.mp3')
    if os.path.exists(txt) and not os.path.exists(mp3):
        with open(txt, 'r', encoding='utf-8') as f:
            tasks.append((i, f.read(), mp3))
def do_tts(args):
    idx, text, mp3_path = args
    return idx, tts_slide(text, mp3_path, lang='zh')
with ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(do_tts, t): t[0] for t in tasks}
    for f in as_completed(futures):
        idx, ok = f.result()
        print(f'  [{idx:02d}/22] {\"OK\" if ok else \"FAIL\"}')
print(f'Parallel TTS: {len(tasks)} slides done')
"
```

If any slide produces 0-byte MP3, re-run that single slide sequentially.


---

## Phase 7 — Assemble MP4 video

Parallel ffmpeg encode of all slides, then concatenate. `max_workers` should match your CPU cores (default 8).

```bash
# cwd: D:\Envs\Paper_Survey_Env
py -c "
import sys, os
sys.path.insert(0, r'D:\Envs\Paper_Survey_Env\.omp\skills\pdf-slides-to-video\scripts')
from slides_to_video import assemble_video
assemble_video(
    r'<FRAME_DIR>',
    r'<VIDEO_DIR>/<paper_name>_narrated.mp4',
    pad_sec=0.5, speed=1.25, max_workers=8
)
"
```

Produces H.264 1920x1200 with black letterbox padding (any source aspect ratio -> 16:10).
`speed=1.25` applies 25% playback speedup for tighter pacing. `pad_sec=0.5` adds 0.5s freeze-frame after each slide.
## Phase 8 — Generate cover image

Cover is always the raw first slide PNG (no scaling, no letterbox). Poster generation
happens separately via `markdown-to-video-cover`; it is not used for the upload cover.

```bash
# cwd: D:\Envs\Paper_Survey_Env
py -c "
import sys, os
sys.path.insert(0, r'.omp\skills\pdf-slides-to-video\scripts')
from slides_to_video import generate_cover
cover = generate_cover(r'<FRAME_DIR>/slide_001.png', r'<VIDEO_DIR>/cover.png')
print(f'Cover: {cover} (raw first slide)')
"
```
## Phase 9 — Generate Bilibili metadata

```bash
# cwd: D:\Envs\Paper_Survey_Env
py -c "
import sys, json
sys.path.insert(0, r'D:\Envs\Paper_Survey_Env\.omp\skills\pdf-slides-to-video\scripts')
from slides_to_video import parse_beamer_preamble, parse_beamer_frames, generate_metadata
preamble = parse_beamer_preamble(r'<TEX_PATH>')
frames = parse_beamer_frames(r'<TEX_PATH>')
path = generate_metadata(preamble, frames, 'cover.png', r'<VIDEO_DIR>/video_meta.json')
print(f'Metadata: {path}')
"
```

Generates `video_meta.json`. **Title MUST use format `【Venue Year】ShortName — Paper Title`** (e.g. `【ICML 2023】PaLM-E — ...`). The `generate_metadata()` function automatically prepends the venue+year prefix from the beamer preamble. Also includes: title_en, tid (auto-mapped from venue), tags, desc, copyright=1, dynamic, no_reprint=0, cover_path.

---

## Phase 9.5 — Upload to Bilibili

After generating `video_meta.json`, upload using the `bilibili-video-uploader` skill
(Python biliup v1.2.1, `--submit web`):

```bash
py "D:/Envs/Paper_Survey_Env/.omp/skills/bilibili-video-uploader/scripts/upload.py" "<PAPER_DIR>"
```

See `skill://bilibili-video-uploader` for login, metadata finalization, and error handling.
---

## Phase 10 — Report

Tell the user:
- Output: `<VIDEO_DIR>/` with `<paper>_narrated.mp4`, `cover.png`, `video_meta.json`, `video_frames/`
- Total slides: N, duration: HH:MM:SS
- Any warnings (missing models, edge-tts fallback used)
- TTS model used: "edge-tts (zh-CN-XiaoxiaoNeural / en-US-AriaNeural)"
---

## Narration style

All slides get narration — no silent slides. Different strategies per slide type:

| Type | Slides | Words | Strategy |
|------|--------|-------|----------|
| Title | 1 | 40-60 | Welcome, state paper title + authors + venue |
| TOC | 1 | 40-60 | Outline structure, mention key themes |
| Content | 13 | 150-250 | Expand bullets into complete sentences, weave metrics into flow |
| Figure | 5 | 120-200 | Describe sub-panels, axes, trends, numbers — translate English markdown captions into Chinese |
| References | 1 | 40-60 | Mention key cited works and research lineage |
| Closing | 1 | 20-40 | Thank audience, summarize key takeaway, invite questions |

Rules:
- OUTPUT: 简体中文. English technical terms (MT3, BC, alignment, open-loop replay, pose estimation, etc.) kept inline — do NOT translate.
- Self-contained: NEVER reference "this slide", "如图所示", "这一页" — listener cannot see slides.
- Expand bullets into complete explanatory sentences; never just list items.
- Figure slides: use markdown figure captions for rich descriptions — sub-panels (A, B, C...), axes labels, trends, percentages.
- Start with a brief transition from previous slide, end with a forward-looking hook.