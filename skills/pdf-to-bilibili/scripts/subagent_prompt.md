# Subagent Dispatch Template

Use this template when dispatching subagents via the `task` tool.
One subagent per paper for maximum KV cache hit rate.

## Mode: slides

```
# Target
Create Beamer slides for paper {arxiv_id} ("{title}").
PDF: {pdf_path}
Output: D:\Envs\Paper_Survey_Env\论文分享\{dir_name}\
Mode: slides

# Change
Read skill://pdf-to-bilibili and follow Phase 1→2→3→3.5.
Stop after compiled PDF is verified (0 errors, 1610 aspect ratio, 3-8 appendix slides).
If venue is discovered in Phase 3.5, rename the directory.

# Acceptance
- slides-beamer/main.pdf compiles with latexmk -xelatex (0 errors)
- Copy main.pdf → ../{dir_name}.pdf
- Report: slide count, appendix count, any warnings
```

## Mode: video

```
# Target
Write Chinese narrations for paper {arxiv_id} ("{title}").
Slides already exist at: D:\Envs\Paper_Survey_Env\论文分享\{dir_name}\slides-beamer\
Output: D:\Envs\Paper_Survey_Env\论文分享\{dir_name}\
Mode: video

# Change
Read skill://pdf-to-bilibili and follow Phase 4a ONLY.
Write % NARRATION: comments after each \end{frame} in video/main_with_narration.tex.
Validate coverage: frame count == narration count.
IMPORTANT: Do NOT run TTS or ffmpeg — the main agent handles Phase 4b.

# Acceptance
- video/main_with_narration.tex has % NARRATION: after every \end{frame}
- Assert: frames == narrations (validation gate passed)
- frames_data.json written for metadata
```

## Mode: bilibili

```
# Target
Process paper {arxiv_id} ("{title}") from PDF to Bilibili upload.
PDF: {pdf_path}
Output: D:\Envs\Paper_Survey_Env\论文分享\{dir_name}\
Mode: bilibili

# Change
Read skill://pdf-to-bilibili and follow Phase 1→2→3→3.5→4a→5.
Write narrations (Phase 4a) then upload (Phase 5).
For Phase 5, use direct Python path:
"C:/Users/disco/AppData/Local/Programs/Python/Python310/python.exe" "D:/Envs/Paper_Survey_Env/.omp/skills/bilibili-video-uploader/scripts/upload.py" "D:/Envs/Paper_Survey_Env/论文分享/{dir_name}"

# Acceptance
- slides-beamer/main.pdf compiles (0 errors)
- video/{short}_narrated.mp4 exists with cover + metadata
- Bilibili upload successful, BV号 returned
- URL: https://www.bilibili.com/video/{BV号}
```
