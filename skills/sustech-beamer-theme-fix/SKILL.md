---
name: sustech-beamer-theme-fix
description: Fix for undfined \setsource/\setdomains/\setpresenter/\setvenue commands when compiling SUSTech Beamer slides from the standard template. Copy the extended beamerthemesustech.sty from HIL-SERL reference.
---

# SUSTech Beamer Theme \setsource Fix

## Problem

When filling `main.tex` from the standard `slides-template`, `latexmk -xelatex` fails with:
```
! Undefined control sequence.
l.23 \setsource{...}{...}
```
Also: `\setdomains`, `\setpresenter`, `\setvenue`. These are used in the HIL-SERL style reference but NOT defined in the template version of `beamerthemesustech.sty`.

## Root cause

The template `beamerthemesustech.sty` is ~60 lines, ending with `\mode<all>`. The HIL-SERL extended version continues to ~100+ lines with:
- `\paperfrom{venue}{year}` — formats the source line
- `\setsource{venue}{year}` — calls `\paperfrom`
- `\setdomains{...}` — sets domain tags
- `\setpresenter{name}` — sets presenter name
- `\setvenue{location}` — sets venue location
- `\titlemetaline` — formats the title page bottom line

## Fix

After copying the template, replace `beamerthemesustech.sty` with the extended version:

```bash
cp "D:/Envs/Paper_Survey_Env/论文分享/SCIENCE ROBOTICS 2025 - HIL SERL/slides-beamer/sustech-theme/beamerthemesustech.sty" \
  "<TARGET>/slides-beamer/sustech-theme/beamerthemesustech.sty"
```

Do this BEFORE first compile. The `beamerthemesustech-elements.sty` and `beamercolorthemesustech.sty` files are identical between template and HIL-SERL — only `beamerthemesustech.sty` differs.
