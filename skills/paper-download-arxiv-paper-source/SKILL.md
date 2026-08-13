---
name: paper-download-arxiv-paper-source
description: Download and safely unpack the TeX e-print of an arXiv paper from an arXiv abs, PDF, e-print URL, DOI redirect, or bare arXiv ID. Use first when the paper-to-beamer workflow receives an arXiv reference so equations, tables, bibliography, and original figures can be read directly from source instead of parsing a PDF.
---

# Download arXiv Paper Source

Turn an arXiv reference into a local, inspectable TeX source tree for
`paper-to-beamer`.

## Run

Resolve this skill's directory from the active skill location, then run:

```bash
python3 <skill-dir>/scripts/download_source.py \
  "<arxiv-url-or-id>" \
  --output "<absolute-work-directory>"
```

Accepted inputs include:

- `https://arxiv.org/abs/2502.12110`
- `https://arxiv.org/pdf/2502.12110`
- `https://doi.org/10.48550/arXiv.2502.12110`
- `2502.12110` or a versioned ID such as `2502.12110v2`

Use `--force` only when the existing archive must be downloaded again.

## Read the output contract

Do not guess paths. Read the final status line printed by the script:

- `TEX_SOURCES: ...` — use the listed files under `paper_src/`.
- `DOWNLOADED ...tex` — use the single-file submission directly.
- `PDF_ONLY: ...pdf` — stop and tell the user this TeX-source-only workflow
  cannot continue. Do not silently install or invoke MinerU.
- `ERROR: ...` with a nonzero exit — report the specific failure and stop.

The script rejects unsafe archive paths and skips links and special files.

## Hand-off

After a successful TeX download, invoke `paper-to-beamer` with the original
arXiv reference and the absolute work directory. Keep the downloaded source
unchanged; put generated slide files in a separate output directory.
