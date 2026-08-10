---
name: bilibili-video-uploader
description: |
  Login to Bilibili and upload a narrated MP4 video using biliup (Python CLI v1.2+).
  Reads video_meta.json from a paper directory (output of pdf-slides-to-video)
  and fills title, description, tags, category, cover, and copyright.
  Trigger on: "upload to bilibili", "bilibili upload", "发布到B站",
  "上传到B站", "bilibili投稿".
user-invocable: true
argument-hint: "<paper_directory>"
---

# Bilibili Video Uploader

Given a paper directory containing `video/` (output of `pdf-slides-to-video`),
upload the narrated MP4 to Bilibili using `biliup` Python CLI (v1.2.1+), which
replaces the archived biliup-rs v0.2.4.

**Python**: ALWAYS use the direct path on this machine — `py` routes through broken WSL:
`C:/Users/disco/AppData/Local/Programs/Python/Python310/python.exe`
**Cookie store**: `%USERPROFILE%\.bilibili\cookies.json`
**CLI wrapper**: `.omp/skills/bilibili-video-uploader/scripts/upload.py` — always use this script for uploads.

---


## Phase 0 — Diagnostics & Recovery

When an upload fails with "another process waiting for rate limit" or a lock-related
error, or if you suspect a stuck biliup daemon, use the diagnostic and recovery commands:

### Diagnose

```bash
py "D:/Envs/Paper_Survey_Env/.omp/skills/bilibili-video-uploader/scripts/upload.py" --diagnose
```

This reports:
- **Lock files** in `%LOCALAPPDATA%\bilibili\locks\` — each marked `[STALE]` (safe to remove)
  or `[ACTIVE]` (held by a running process).
- **Running biliup processes** — PID, port, and HTTP health check.
- **Recent upload log** — last 15 `biliup_cli` lines from `download.log`.

### Kill all biliup processes and clean locks

```bash
py "D:/Envs/Paper_Survey_Env/.omp/skills/bilibili-video-uploader/scripts/upload.py" --kill-all
```

Prompts for confirmation before killing processes and removing stale lock files.
Use `--kill-all --force` to skip the confirmation prompt.

**What it does:**
1. Runs `--diagnose` to show current state
2. Kills every Python process with `biliup` in its command line via `taskkill /F`
3. Removes lock files where no process holds them open (stale locks)
4. With `--force`: also removes active lock files after killing their processes

## Phase 1 — Preflight

1. Check Python biliup:
   ```bash
   py -c "import biliup; print('biliup OK')" 2>/dev/null || echo "biliup MISSING"
   ```
   If missing:
   ```bash
   py -m pip install biliup
   ```

2. Check cookie status:
   ```bash
   ls -la "%USERPROFILE%\.bilibili\cookies.json"
   ```
   If missing, proceed to login (Phase 3).

3. Verify ffmpeg not needed — biliup Python uses direct HTTP upload.

---

## Phase 2 — Resolve input

Accept `$ARGUMENTS` — a paper directory matching the `pdf-slides-to-video` layout:

```
论文分享/<VENUE> - <TITLE>/
  video/
    <paper>_narrated.mp4    # narrated video
    cover.png               # 1920x1200 cover (optional: auto-generated from poster)
    video_meta.json         # Bilibili metadata
  poster/
    poster.png              # from markdown-to-video-cover skill (auto-resized as cover)
```

The CLI wrapper (`scripts/upload.py`) handles all resolution automatically.

**Cover resolution priority:**
1. `video/cover.png` — primary cover (now generated from poster by upstream skills
   when available; falls back to first-slide letterbox otherwise).
2. `poster/poster.png` — fallback if `video/cover.png` is missing but the poster exists;
   auto-resized to 1920×1200 via ffmpeg and saved as `video/cover.png`.
3. Neither — warn and upload without cover.

Validate:
- If `video_meta.json` is missing → error: "No video_meta.json found. Run pdf-slides-to-video first."
- If no `.mp4` in `VIDEO_DIR/` → error: "No MP4 video found. Run pdf-slides-to-video first."
- **Title format validation**: video_meta.json `title` MUST start with `【Venue Year】` and include a short paper name/acronym between the venue prefix and the title (e.g. `【ICML 2023】PaLM-E — ...`). If not, auto-fix by prepending the venue+year from `frames_data.json` preamble or directory name.


## Phase 3 — Login

If `%USERPROFILE%\.bilibili\cookies.json` exists, assume valid (biliup handles expiration).

If missing, use the CLI wrapper:

```bash
py "D:/Envs/Paper_Survey_Env/.omp/skills/bilibili-video-uploader/scripts/upload.py" --login
```

This displays a QR code in the terminal. **Instruct the user to scan it with the
Bilibili mobile app and confirm login.** Wait for user confirmation before proceeding.

Note: Python biliup saves cookies to `cookies.json` in cwd by default.
After login, move it:
```bash
cp cookies.json "%USERPROFILE%\.bilibili\cookies.json"
```

---

## Phase 3.5 — Finalize metadata for Bilibili

Before uploading, optimize `video_meta.json` for Bilibili's content style.
Reads `frames_data.json` for paper context, rewrites title/tags/desc/dynamic.

**Title**: `【Venue Year】ShortName — Chinese Title — Hook`, capped at 80 chars. ShortName is the paper's well-known acronym (e.g. PaLM-E, MT3, PG-TS) or 1-2 distinctive keywords.
**Tags**: first tag always `论文分享`, then domain keywords, then venue, then broad tags (max 10).
**Desc**: structured with `【论文信息】→【核心亮点】→【内容概要】→ links`.
**Dynamic**: short engaging feed post with `#hashtags`, ≤256 chars.

Edit `hook`, `domain_keywords`, `authors`, `venue_extra`, and paper-specific content
in the script below. All other fields are sourced from `frames_data.json` and `video_meta.json`:

```python
import json, os

PAPER_DIR = r"<PAPER_DIR>"
VIDEO_DIR = os.path.join(PAPER_DIR, "video")
META_PATH = os.path.join(VIDEO_DIR, "video_meta.json")
FRAMES_PATH = os.path.join(VIDEO_DIR, "frames_data.json")

with open(META_PATH, "r", encoding="utf-8") as f:
    meta = json.load(f)

preamble = {}
if os.path.exists(FRAMES_PATH):
    with open(FRAMES_PATH, "r", encoding="utf-8") as f:
        preamble = json.load(f).get("preamble", {})

venue = preamble.get("venue", "")
year = preamble.get("year", "")
cn_title = preamble.get("title", meta.get("title", ""))
authors = preamble.get("author", "")
subtitle = preamble.get("subtitle", "")

short_name = "ELEGNT"                               # paper acronym or short name (1-8 chars)
hook = "表达性运动让用户感知评分翻倍"                 # one-line hook in 简体中文 (≤50 chars) — English prohibited: too long for Bilibili title
domain_keywords = ["人机交互", "机器人", "运动设计"]  # 2-4 domain tags
authors_short = "Hu et al. (Apple)"                # short author credit
venue_extra = "Funchal, Madeira"                   # venue location
arxiv_id = "2501.12493"                            # arXiv ID if any
highlight_1 = "提出 ELEGNT 框架，将功能性效用与表达性效用结合"
highlight_2 = "台灯机器人：6-DOF 机械臂 + LED + 投影仪 + 摄像头"
highlight_3 = "用户研究（n=21）：表达性运动评分 56.16 vs 纯功能 28.77（p<0.0001）"
highlight_4 = "社交型任务收益最显著，功能型任务差异不显著"
summary = "本文提出 ELEGNT 框架，将机器人的运动设计从纯功能性拓展到同时包含表达性目标..."
# ────────────────────────────────────────────────────────────

# 1. Title: 【Venue Year】ShortName — Chinese Title — Hook (≤80 chars)
meta["title"] = f"【{venue} {year}】{short_name} — {cn_title} — {hook}"
if len(meta["title"]) > 80:
    meta["title"] = meta["title"][:77] + "..."

# 2. Tags (max 10, first = 论文分享)
optimized = ["论文分享"] + domain_keywords + [venue, "人工智能"]
meta["tag"] = list(dict.fromkeys(optimized))[:10]

# 3. Description: structured sections
arxiv_link = f"\n论文链接：https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
meta["desc"] = (
    f"【论文信息】\n"
    f"标题：{subtitle or cn_title}\n"
    f"作者：{authors_short}\n"
    f"会议：{venue} {year}, {venue_extra}\n"
    f"{arxiv_link.strip()}\n"
    f"\n【核心亮点】\n"
    f"{highlight_1}\n{highlight_2}\n{highlight_3}\n{highlight_4}\n"
    f"\n【内容概要】\n"
    f"{summary}\n"
    f"\n本视频由 AI 自动生成，仅供学术交流使用。"
)

# 4. Dynamic: engaging feed post (≤256 chars)
meta["dynamic"] = (
    f"新一期论文分享来啦！\n\n"
    f"【{venue} {year}】{short_name}：{cn_title} — {hook}\n\n"
    + " ".join(f"#{t}" for t in optimized[:5])
)
meta["dynamic"] = meta["dynamic"][:256]

with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"Polished: {meta['title'][:60]}...")
print(f"Tags ({len(meta['tag'])}): {meta['tag']}")
```

---

## Phase 4 — Upload

Use the CLI wrapper script. It reads `video_meta.json`, validates inputs, builds
the biliup command with `--submit web` (current working API), and handles
error classification.

```bash
"C:/Users/disco/AppData/Local/Programs/Python/Python310/python.exe" "D:/Envs/Paper_Survey_Env/.omp/skills/bilibili-video-uploader/scripts/upload.py" "<PAPER_DIR>"
```

### 4.1 What the script does

1. Reads `video/video_meta.json`
2. Finds the `.mp4` in `video/`
3. Validates cover existence
4. Builds: `py -m biliup -u cookies.json upload <mp4> --title ... --tid ... --tag ... --submit web ...`
5. Runs the command, captures output
6. Extracts `BV[0-9A-Za-z]{10}` from output → constructs `https://www.bilibili.com/video/<BV号>`
7. Classifies errors: auth expiry, duplicate, too-large, rate-limit



### 4.2 Error handling

| Exit code | Condition | Action |
|-----------|-----------|--------|
| 0 + BV号 | Success | Report URL |
| 2 | Cookie expired | Re-login, retry once |
| 3 | Duplicate video | Warn, stop |
| 4 | File too large | Warn, stop |
| 5 | Rate limited | Wait ~1h, retry |
| 1 | Other | Report stderr, stop |

### 4.3 Video metadata reference

| video_meta.json key | biliup flag | Notes |
|---|---|---|
| `title` (≤80 chars) | `--title` | Auto-truncated |
| `tid` (124/208/209/210) | `--tid` | Category ID |
| `tag` (list, ≤10 items) | `--tag` | Comma-joined |
| `desc` | `--desc` | Full text |
| `copyright` (1/2) | `--copyright` | 1=original, 2=reprint |
| `cover_path` | `--cover` | Absolute path to PNG |
| `source` | `--source` | Only when copyright=2 |
| `dynamic` (≤256 chars) | `--dynamic` | Feed post text |
| `no_reprint` (0/1) | `--no-reprint` | 1=禁止转载 |

---

## Phase 5 — Report

Tell the user:

- **Upload status**: success or failure with reason
- **Bilibili URL**: `https://www.bilibili.com/video/<BV号>`
- **Video title**: from meta
- **Cookie location**: `%USERPROFILE%\.bilibili\cookies.json`
- Any warnings encountered:
  - Cover missing → uploaded without custom cover
  - Tags truncated (meta had >10 tags)
  - Title truncated (meta title >80 chars)
  - Dynamic truncated (meta dynamic >256 chars)

If upload failed, include the raw biliup stderr for debugging.

---

## Phase 6 — Post-upload (optional)

If upload succeeds, offer to clean up video frames:

> Video uploaded successfully. Want to delete `video/video_frames/` to save disk space?

Do NOT auto-delete. Only delete if the user explicitly confirms.

---

## Upload flags reference (biliup Python v1.2.1)

```
--submit <app|web|b-cut-android>    提交接口 [default: web — only working option as of 2026-07]
--line <LINE>                        上传线路 [bldsa, cnbldsa, andsa, atdsa, bda2, cnbd, anbd, atbd, tx, cntx, antx, attx, bda, txa, alia]
--limit <LIMIT>                      单视频文件最大并发数 [default: 3]
--copyright <1|2>                    1-自制 2-转载
--source <SOURCE>                    转载来源
--tid <TID>                          投稿分区 [default: 171]
--cover <COVER>                      视频封面路径
--title <TITLE>                      视频标题
--desc <DESC>                        视频简介
--dynamic <DYNAMIC>                  空间动态
--tag <TAG>                          视频标签，逗号分隔
--dtime <DTIME>                      延时发布时间（10位时间戳，距提交>4小时）
--dolby <0|1>                        杜比音效
--hires <0|1>                        Hi-Res
--no-reprint <0|1>                   0-允许转载 1-禁止转载
--charging-pay <0|1>                 开启充电
--up-selection-reply                 开启精选评论（需 --submit app）
--up-close-reply                     关闭评论（需 --submit app）
--up-close-danmu                     关闭弹幕（需 --submit app）
```

Submit endpoint status (2026-07):
- `--submit web`            ✅ working — use this
- `--submit app`            ❌ 21566 "app version too old"
- `--submit b-cut-android`  ❌ -663 "auth failure"

Other differences from biliup-rs v0.2.4:
- `--submit client` removed
- `--open-elec` renamed to `--charging-pay`
- Additional CDN lines available (cnbldsa, andsa, atdsa, etc.)
