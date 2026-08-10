---
name: paper-to-beamer
description: |
  Automated pipeline: PDF paper → Markdown (MinerU) → filled SUSTech Beamer slides (11-section 论文分享 structure) → compiled PDF.
  Use when the user asks to create Beamer slides from an academic paper PDF, or says "论文分享", "paper to slides", "make beamer from paper".
  Invoke with an absolute or relative path to a PDF.
user-invocable: true
argument-hint: "<input.pdf>"
---

# Paper → Beamer Slides Pipeline

Given a paper PDF, produce a compiled SUSTech-themed Beamer presentation under
`论文分享/<VENUE> - <SHORT_TITLE>/`.

**Theme variant**: `\usetheme{sustech}` (lowercase, Variant A), from
`https://github.com/yhbcode000/sustech-slides-template.git`.
Do NOT use `\usetheme{SUSTech}` (Variant B, used in MT3) — it has different
macros and no section-separator pages.

**Default aspect ratio**: `aspectratio=1610` (16:10). Do NOT use 169 (16:9) —
1610 is preferred for laptop/projector compatibility and gives slightly more
vertical space for dense content.

**Bash runtime**: All shell commands run under the session's `bash` tool,
which on this Windows system is Git Bash. Unix-style `rm -rf`, `cp -r`,
`mkdir -p` are available. Working directory is set per-block via `cwd`.

---

## Phase 1 — Setup directory

1. Accept `$ARGUMENTS` (PDF path; absolute or relative from session cwd).
2. Derive a short directory name `<VENUE> - <SHORT_TITLE>`:
   - Strip `.pdf`, replace spaces/hyphens/special chars.
   - Ask the user for the name if venue/title are not inferrable from the
     filename.
   - Convention: existing examples are `SCIENCE ROBOTICS - HIL SERL`,
     `SCIENCE ROBOTICS - MT3`.
3. Create `论文分享/<DIR_NAME>/` and copy the PDF there.

---

## Phase 2 — PDF → Markdown

Run MinerU in-process on CUDA via the existing convert wrapper:

```
"C:\Users\disco\.mineru-env\Scripts\python.exe" \
  "C:\Users\disco\.claude\skills\pdf-to-markdown\convert.py" \
  "论文分享/<DIR_NAME>/<pdf_filename>.pdf" \
  "论文分享/<DIR_NAME>/md_output" \
  --lang en
```

- English papers: `--lang en`.  Chinese/mixed: `--lang ch`.
- The wrapper prints `DONE -> ...md` on success.
- Output lands at `md_output/<name>/auto/<name>.md`.

If MinerU env is missing, stop and tell the user to install it per the
`pdf-to-markdown` skill preflight.

---

## Phase 3 — Clone template

```bash
# cwd: D:\Envs\Paper_Survey_Env
git clone --depth 1 https://github.com/yhbcode000/sustech-slides-template.git \
  "论文分享/<DIR_NAME>/slides-template"
rm -rf "论文分享/<DIR_NAME>/slides-template/.git"
```

This gives the pristine `main_template.tex` + `sustech-theme/` + `latexmkrc`.

**Fallback if `git clone` fails (network)**: copy `sustech-theme/` +
`latexmkrc` + `main_template.tex` from an existing paper directory
(e.g. `论文分享/SCIENCE ROBOTICS - HIL SERL/slides-template/`).

---

## Phase 4 — Create working dir and copy essentials

```bash
# cwd: D:\Envs\Paper_Survey_Env
mkdir -p "论文分享/<DIR_NAME>/slides-beamer"
cp -r "论文分享/<DIR_NAME>/slides-template/sustech-theme" \
  "论文分享/<DIR_NAME>/slides-beamer/"
cp "论文分享/<DIR_NAME>/slides-template/latexmkrc" \
  "论文分享/<DIR_NAME>/slides-beamer/"
cp "论文分享/<DIR_NAME>/slides-template/main_template.tex" \
  "论文分享/<DIR_NAME>/slides-beamer/main.tex"
mkdir -p "论文分享/<DIR_NAME>/slides-beamer/figures"
```

**All subsequent edits target `slides-beamer/` only.**
`slides-template/` is kept pristine as a reference.

---

## Phase 5 — Read and extract content from Markdown

Read `md_output/<name>/auto/<name>.md`. Extract these data points:

| Data | Source in MD | Target in `.tex` |
|---|---|---|
| Paper title | First `#` heading or "Title:" line | `\title`, `\subtitle` |
| Authors | Author list (usually near top) | `\author`; `作者介绍` frame |
| Venue + year | Journal/conference name + year | `\institute`, `\date`; `论文信息` frame |
| Abstract / motivation | First paragraphs after title | `研究背景与动机` section |
| Problem definition | Problem statement or intro section | Fold into 背景 or a dedicated frame |
| Method | Method/approach section | `方法` section (2 frames: overview + details) |
| Experimental setup | Experiments section (datasets, baselines, protocol) | `实验设计` section |
| Results | Results section (tables, numbers, analysis) | `实验结果` section (main table + analysis) |
| Contributions | Conclusion or contributions section | `要点总结` section |
| Limitations | Limitations/discussion/future work | `局限性` section |
| Key references | References / bibliography | `参考文献` frame (`bibitem` entries) |

---

## Phase 6 — Fill `slides-beamer/main.tex`

**This is the core creative phase.** Read `main.tex` (copied from template),
then edit it section by section to replace every `\ph{…}` placeholder and
`\phfig` with real content from the Markdown.

Use the **HIL SERL example** as a filled-in style reference:
`论文分享/SCIENCE ROBOTICS - HIL SERL/slides-beamer/main.tex`.

### 6.0 Preamble metadata

Target the `\title`, `\subtitle`, `\author`, `\institute`, `\date` macros:

- `\title[\ph{短标题}]{…}` → `\title[Short Title]{Full Paper Title}`
- `\subtitle{…}` → paper subtitle; set `\subtitle{}` if none
- `\author[\ph{汇报人}]{…}` → presenter name (ask user or default to "Haobo Yang")
- `\institute[机构]{…}` → `SUSTech, China \textperiodcentered\ <venue>, <year>`
- `\date{2026-MM-DD \textperiodcentered\ Singapore}` → current date and location

Delete the placeholder-helper macros `\ph` and `\phfig` — they're no longer needed.

### 6.1 首页 (Title page)

The `\titlepage` frame stays as-is. Preamble metadata drives it.

### 6.2 📄 论文信息页 (Paper info)

The template has no dedicated paper-info frame. **Insert one** after the
TOC frame (i.e. after the `\section{}` line that follows `\tableofcontents`):

```latex
\begin{frame}{论文信息}
  \begin{block}{基本信息}
    \begin{itemize}
      \item \textbf{标题}：<full paper title>
      \item \textbf{作者}：<first author> et al. / full author list
      \item \textbf{期刊/会议}：<venue>
      \item \textbf{年份}：<year>
    \end{itemize}
  \end{block}
  \tightgap
  \begin{callout}[一句话概括]
    <one-sentence paper summary>
  \end{callout}
\end{frame}
```

### 6.3 📋 背景与动机

Map to the `研究背景与动机` section in the template:
- Set `\renewcommand{\secblurb}{…}` (one-sentence summary) before `\section`.
- Fill bullet placeholders with telegraphic motivation from abstract/intro.
- Move the figure to a dedicated `[plain,c]` slide after this content slide: `\fitfigure{fig1_overview.jpg}` + `\figcap{1}{caption}`. Remove the `\begin{columns}` wrapper — this slide stays text-only.
- Fill `\metric{…}{…}` with up to 3 key numbers from the paper.

### 6.4 相关工作

Map to the `相关工作` section:
- Fill research areas from the paper's Related Work section.
- List actual baseline methods and their relationships.
- State the key differentiator in the callout.

If the paper has a clear "Related Work" section, use it. Otherwise
condense from scattered references in the introduction.

### 6.5 🔧 方法

Map to the `方法` section (2 frames: overview + core design).

**Frame 1 (Overview)**:
- List system components from the paper's method section.
- Move the figure to a dedicated `[plain,c]` slide after this content slide: `\fitfigure{fig2_system.jpg}` + `\figcap{2}{caption}`. Remove the `\begin{columns}` wrapper.

**Frame 2 (Core design)**:
- List up to 4 key design elements.
- Add one-line takeaway in the callout.

### 6.6 🧪 实验设计

Map to the `实验设计` section:
- List task categories/datasets.
- State evaluation protocol and baselines.
- Move the figure to a dedicated `[plain,c]` slide after this content slide: `\fitfigure{fig3_tasks.jpg}` + `\figcap{3}{caption}`. Remove the `\begin{columns}` wrapper.

### 6.7 📈 结果与分析

Map to the `实验结果` section (2 frames: main table + analysis).

**Frame 1 (Main table)**:
- Recreate the table with real data from the paper.
- Keep ≤5 columns, ≤6 rows.
- Highlight best results with `\shl{…}`.
- Use `\theadrow`, `\altrow`, `\thc{…}` with `booktabs`.
- One-line conclusion in the callout.

**Frame 2 (Analysis)**:
- Bullet-point analysis (3–4 observations).
- Analysis figure on a dedicated `[plain,c]` slide after the analysis bullets.

### 6.8 💡 要点总结

Map to the `要点总结` section (corresponds to "核心贡献"):
- 3 enumerated key takeaways.
- One-sentence summary in the callout.

### 6.9 ⚠️ 局限与讨论

Map to the `局限性` section:
- 3–4 limitations.
- Author-identified future directions in the callout.

### 6.10 📚 参考文献

Map to the `参考文献` frame:
- Fill `bibitem` entries with actual references from the paper.
- First `bibitem` should be the paper itself (marked `（本文）`).
- Include 3–5 key baselines.

### 6.11 💬 Q&A

Replace placeholder text in the Q&A frame with:
- Presenter name, institution, contact info.
- Keep the `Q&A` styling (`\fontsize{40}{44}` etc.).

### 6.12 Figures handling

For every placeholder that needs a figure:

1. List images from `md_output/<name>/auto/images/`. Each is a hash-named `.jpg`.
2. Pick the relevant figure by inspecting the image content (use `inspect_image`
   or rely on the markdown's `![](images/...)` references).
3. Copy to `slides-beamer/figures/` with a semantic name:
   `fig1_overview.jpg`, `fig2_system.jpg`, `fig3_tasks.jpg`, `fig4_results.jpg`, etc.
4. Reference with `\fitfigure{filename}` (safe width + max-height macro from
   the sustech theme).
5. Place the figure on its own dedicated slide — NEVER inside a `\begin{columns}` block:
   ```latex
   \begin{frame}[plain,c]
     \centering
     \fitfigure{filename}
     \figcap{N}{caption text}
   \end{frame}
   ```


If a figure is missing or uncapturable, insert a placeholder callout instead
(the `\phfig` helper was deleted in 6.0, so do NOT reference it):

```latex
\begin{callout}[Figure]
  [Figure N: <description> — to be added]
\end{callout}
```

Note this in the Phase 8 report so the user knows to source the figure manually.

### 6.13 Writing style

- **Telegraphic**: keyword phrases, not full sentences. Bullets ≤2 lines.

- **No two-column layouts**: AVOID `\begin{columns}…\end{columns}` entirely. Paper figures are large and detailed — side-by-side text+figure makes the figure too small to read. Every figure gets its own `[plain,c]` slide at full size.
- **Figures on own slides**: every figure goes on a dedicated plain slide:
  ```latex
  \begin{frame}[plain,c]
    \centering
    \fitfigure{figN_description.jpg}
    \figcap{N}{caption}
  \end{frame}
  ```
  NEVER put a figure inside a column, `\begin{block}`, or next to bullet points.
- **Emphasis macros** (sustech theme):
  - `\shl{…}` — bold orange highlight (key methods, best results)
  - `\keyword{…}` — orange keyword
  - `\brandemph{…}` — orange italic for brand/concept names
  - `\hlbox{…}` — yellow inline highlight (key numbers)
- **Callout boxes**: `\begin{callout}[Title] … \end{callout}` for takeaways.
- **Metrics**: `\metric{value}{label}` for key numbers.
- **Tables**: `\theadrow`, `\altrow`, `\thc{…}` with `booktabs`. Always `\centering`.
- **Section blurbs**: set `\renewcommand{\secblurb}{…}` before each `\section{}`.
- **No `\tiny`**: minimum `\small` for footnotes/captions.
- **References slide is second-to-last** (before Q&A).

---

## Phase 7 — Compile

```bash
# cwd: D:\Envs\Paper_Survey_Env\论文分享\<DIR_NAME>\slides-beamer
latexmk -xelatex main.tex
```

On success: copy `main.pdf` → `../<DIR_NAME>.pdf` at the paper dir root
(matching the HIL SERL convention).

Post-compile checks (use the **built-in `grep` tool**, not shell `grep`):

- Grep `main.log` for `Overfull \\hbox` — report count.
- Grep for `Undefined control sequence` — flag if any.
- Report: page count, build status.


## Phase 7.5 — Extract venue and rename directory

Many papers are published at venues (ICML, RSS, CoRL, etc.) not listed in
the README. The preamble should already contain `\setsource{Venue}{Year}`.
After compilation, extract this venue and rename the paper directory if it
still uses the default "arXiv" prefix.

**Extract venue** from the compiled `.tex` preamble:
```bash
py -c "
import re, os
tex = r'<PAPER_DIR>/slides-beamer/main.tex'
with open(tex, 'r', encoding='utf-8') as f:
    content = f.read()
- If extracted venue differs from current dir prefix (e.g. "arXiv" → "ICRA 2026"):
  ```bash
  mv "<PAPER_DIR>" "D:/Envs/Paper_Survey_Env/论文分享/<NEW_VENUE> - <SHORT_TITLE>"
  ```
- Also rename `<DIR_NAME>.pdf` at the paper dir root to match.
- **Short title must be recognizable**: use the paper's well-known acronym
  (e.g. "IR-SIM", "PaLM-E", "CoT-VLA") or 2+ meaningful title keywords.
  Never use a 2-3 char fragment like "AI", "R1", "WM" — those are meaningless.
- If batch processing, also update `papers.json` and `state.json` paths.

## Phase 8 — Report

Tell the user:

- Directory: `论文分享/<DIR_NAME>/`
- Output: `slides-beamer/main.pdf` + `../<DIR_NAME>.pdf`
- Slide count
- Any figure placeholders (callout boxes with "to be added")
- Any compilation warnings
