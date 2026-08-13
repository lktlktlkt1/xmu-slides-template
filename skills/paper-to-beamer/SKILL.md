---
name: paper-to-beamer
description: Create a complete Chinese XMU-themed LaTeX Beamer presentation and compiled PDF from an arXiv paper with TeX source. Use when the user asks to turn an arXiv paper into 论文分享、组会汇报、中文讲解幻灯片、Beamer slides, or a final presentation PDF. This fork ends at the verified PDF and does not include MinerU, PPTX, narration, video, Bilibili upload, or publishing.
---

# arXiv Paper to XMU Beamer PDF

Produce a source-grounded Chinese academic presentation, compile it with
XeLaTeX, visually inspect every page, and deliver the final PDF. This is a
paper-to-PDF workflow, not a paper-to-video workflow.

## Scope

Supported input:

- an arXiv abs/PDF/e-print URL;
- an arXiv DOI such as `https://doi.org/10.48550/arXiv.2502.12110`;
- a bare arXiv ID.

Required output:

- editable Beamer source and copied paper figures in a work directory;
- one compiled, visually checked PDF named `<PAPER_NAME>_讲解.pdf` at the
  user-requested path.

### Output filename contract

Use `<PAPER_NAME>_讲解.pdf` for the delivered PDF unless the user explicitly
requests a different filename. Prefer the paper's established acronym or short
name, for example `SAGE_讲解.pdf` or `A-MEM_讲解.pdf`; otherwise use a concise,
filesystem-safe form of the paper title.

Do not add the venue, year, institution, theme, or template name to the delivered
filename. In particular, never append `XMU`, `论文讲解_XMU`, or similar branding.
The XMU identity belongs inside the slides, not in the output filename.

Out of scope: arbitrary PDF parsing, MinerU, PPTX, narration, video, cover
generation, Bilibili upload, and social-media metadata.

## Prerequisites

Before starting, verify:

```bash
command -v python3
command -v latexmk
command -v xelatex
command -v pdftoppm
```

Use the companion `paper-download-arxiv-paper-source` skill first. Prefer the
maintained XMU template repository at `~/xmu-slides-template`. If it is absent,
the copier uses the packaged `templates/xmu/` snapshot.

## Workflow

### 1. Create an isolated work directory

Create a paper-specific directory. Do not write generated sources into the
template repository or the skill directory.

Suggested layout:

```text
<work>/
├── paper_src/          # downloaded arXiv source
├── slides/             # generated Beamer project
│   ├── main.tex
│   ├── figures/
│   ├── xmu-theme/
│   └── latexmkrc
└── render/             # page images used for QA
```

### 2. Download and inspect the TeX source

Invoke `paper-download-arxiv-paper-source`. If it reports `PDF_ONLY`, stop and
explain that this fork intentionally has no PDF/MinerU fallback.

Find the real root document by inspecting `\documentclass`, `\input`,
`\include`, and bibliography commands. Read enough of the source to extract:

- exact title, authors, affiliations, and paper date;
- the research problem, motivation, and gap;
- method components, equations, and assumptions;
- datasets, baselines, metrics, ablations, and limitations;
- the strongest result and the evidence that supports it;
- original figure files and their captions.

Never infer a number, claim, or citation that is absent from the paper.

### 3. Copy the XMU template

Run:

```bash
python3 <skill-dir>/scripts/copy_template.py \
  --output "<absolute-work-directory>/slides"
```

Use `--force` only when intentionally replacing copied template assets. Rename
`main_template.tex` to `main.tex` for the generated deck. Keep `xmu-theme/` and
`latexmkrc` beside it.

The template is the branding source of truth. Do not reintroduce SUSTech logos,
colors, or the former Bilibili/GitHub credit line.

### 4. Design the presentation story

Build a coherent talk rather than a page-by-page paper summary. Use this order
when the paper supports it:

1. title page;
2. talk roadmap;
3. author and venue context;
4. motivation and research question;
5. related work and the missing capability;
6. method overview;
7. method details and key equations;
8. experimental setup;
9. main results;
10. ablations, qualitative evidence, or case study;
11. contributions, limitations, and takeaways;
12. references;
13. Q&A;
14. appendix for dense supporting material.

Adapt the number of slides to the paper. Give important paper figures their own
slide when possible. Use Chinese for explanation and preserve standard English
technical terms where translation would reduce precision.

### 5. Build readable slides

Follow these constraints:

- one main message per slide;
- concise bullets, not manuscript paragraphs;
- visible source citations for borrowed claims and figures;
- no placeholders such as `TODO`, `待补`, or dummy references;
- no invented author biographies or venue status;
- figures remain legible at presentation distance;
- large tables are simplified or split rather than shrunk to unreadable size;
- all dates and presenter fields are explicit and user-overridable.

When current external facts such as acceptance venue or author role matter,
verify them from primary sources. Clearly separate verified external context
from claims stated in the paper.

### 6. Compile and correct

Compile inside `slides/`:

```bash
latexmk -xelatex main.tex
```

Treat compilation errors, missing figures, undefined references, and serious
overfull boxes as defects. Search the log after every substantial revision:

```bash
rg -n "Overfull|Undefined|LaTeX Warning|Missing|Error" main.log
```

Do not stop at a successful exit code.

### 7. Render every page and review visually

Render the deck:

```bash
mkdir -p ../render
pdftoppm -png -r 140 main.pdf ../render/page
```

Inspect every page, not only the title page. Correct:

- clipped or overlapping text;
- unreadable equations, tables, legends, or captions;
- stretched, cropped, or pixelated figures;
- isolated headings or unbalanced empty areas;
- inconsistent typography, spacing, and XMU branding;
- claims that are not supported by the source.

Recompile and rerender after corrections.

### 8. Deliver the PDF

Copy the final PDF to the exact location requested by the user. If the user says
“放桌面”, use their Desktop directory and name the file
`<PAPER_NAME>_讲解.pdf`. Keep the editable slide project in the work directory.
Report both paths and the page count. If a differently named intermediate or
root-level PDF exists, do not reuse that name for delivery.

## Completion criteria

The task is complete only when:

- the final PDF exists and opens;
- all pages were visually inspected after the last compile;
- no placeholders or obsolete SUSTech/Bilibili branding remain;
- title, authors, methods, metrics, and results match the paper;
- the delivered filename follows `<PAPER_NAME>_讲解.pdf` and contains no `XMU`
  suffix unless the user explicitly requested a different filename;
- the user receives the exact final PDF path.
