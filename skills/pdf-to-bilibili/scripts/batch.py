"""
Batch orchestrator for pdf-to-bilibili pipeline.
Main agent role: load state, dispatch subagents, monitor, handle failures.

Usage:
  py batch.py <mode> <papers.json>
  mode: slides | video | bilibili
  papers.json: JSON array of {arxiv_id, title, pdf_path, dir_name, dir_path}

The main agent NEVER writes slides, narrations, or runs TTS — only coordinates.
"""
import json, os, time, glob, subprocess, re
from pathlib import Path
from collections import Counter

BASE = Path(r"D:\Envs\Paper_Survey_Env\论文分享")
SKILL_DIR = Path(r"D:\Envs\Paper_Survey_Env\.omp\skills\pdf-to-bilibili")
PYTHON = r"C:\Users\disco\AppData\Local\Programs\Python\Python310\python.exe"
UPLOAD_SCRIPT = r"D:\Envs\Paper_Survey_Env\.omp\skills\bilibili-video-uploader\scripts\upload.py"

# ── State management ──

def load_papers(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def scan_disk_state(papers):
    """Rescan disk and return status for each paper."""
    for p in papers:
        dp = Path(p["dir_path"])
        slides = (dp / "slides-beamer" / "main.pdf").exists()
        mp4s = list(dp.glob("video/*.mp4"))
        anno = dp / "video" / "main_with_narration.tex"
        md = (dp / "md_output" / p["arxiv_id"] / "auto" / f'{p["arxiv_id"]}.md').exists()
        pdf = (dp / f'{p["arxiv_id"]}.pdf').exists()
        
        if mp4s and slides:
            p["_status"] = "video_done"
        elif slides:
            p["_status"] = "slides_done"
        elif anno.exists():
            p["_status"] = "narrations_done"
        elif md:
            p["_status"] = "mineru_done"
        elif pdf:
            p["_status"] = "pdf_downloaded"
        else:
            p["_status"] = "pending"
    return papers

# ── Failure handling ──

def handle_slides_failure(paper):
    """Check if subagent wrote a .tex without compiling."""
    tex = Path(paper["dir_path"]) / "slides-beamer" / "main.tex"
    if not tex.exists():
        return "no_tex"
    with open(tex, "r", encoding="utf-8") as f:
        content = f.read()
    ph_count = len(re.findall(r'\\ph\{', content))
    if ph_count > 20:
        return "empty_template"  # Subagent didn't fill — redispatch
    # Has content — just compile
    pdf = Path(paper["dir_path"]) / "slides-beamer" / "main.pdf"
    if not pdf.exists():
        result = subprocess.run(
            ["latexmk", "-xelatex", "main.tex"],
            cwd=Path(paper["dir_path"]) / "slides-beamer",
            capture_output=True, text=True, timeout=120)
        if pdf.exists():
            return "compiled_ok"
    return "already_compiled"

# ── Progress dashboard ──

def print_dashboard(papers, mode):
    c = Counter(p["_status"] for p in papers)
    target_status = {"slides": "slides_done", "video": "video_done", "bilibili": "uploaded"}
    target = target_status.get(mode, "slides_done")
    done = c.get(target, 0)
    total = len(papers)
    print(f"\n=== [{mode.upper()}] {time.strftime('%H:%M')} ===")
    print(f"  Done: {done}/{total} ({int(done*100/total)}%)")
    for s in ["pending", "mineru_done", "slides_done", "narrations_done", "video_done", "uploaded"]:
        if c.get(s, 0) > 0:
            print(f"  {s}: {c[s]}")
    print()

# ── Batch TTS + Assembly (main agent, for video/bilibili modes) ──

def batch_complete_videos(papers):
    """Run TTS + assembly for all papers with narrations but no video."""
    sys.path.insert(0, str(Path(r".omp/skills/pdf-slides-to-video/scripts")))
    from slides_to_video import write_narrations_to_files, batch_tts_parallel, assemble_video, render_slides
    
    for p in papers:
        if p.get("_status") != "narrations_done":
            continue
        dp = Path(p["dir_path"])
        anno = dp / "video" / "main_with_narration.tex"
        if not anno.exists():
            continue
        
        fd = dp / "video" / "video_frames"
        fd.mkdir(parents=True, exist_ok=True)
        
        # Render PNGs if needed
        if not list(fd.glob("slide_*.png")):
            pdf = dp / "slides-beamer" / "main.pdf"
            if pdf.exists():
                render_slides(str(pdf), str(fd), dpi=200)
        
        try:
            write_narrations_to_files(str(fd), str(dp / "slides-beamer" / "main.tex"),
                                     annotated_tex_path=str(anno))
            batch_tts_parallel(str(fd), lang='zh')  # 8 workers default
            short = p["dir_name"].split(" - ")[-1].replace(" ", "_").replace("-", "_")
            assemble_video(str(fd), str(dp / "video" / f"{short}_narrated.mp4"),
                          pad_sec=0.5, speed=1.25)  # 8 workers default
            print(f"  Video: {p['dir_name']}")
        except Exception as e:
            print(f"  ERR ({p['dir_name']}): {e}")

# ── Batch upload (for bilibili mode) ──

def batch_upload(papers):
    """Upload all papers with videos ready."""
    for p in papers:
        dp = Path(p["dir_path"])
        mp4s = list(dp.glob("video/*.mp4"))
        meta = dp / "video" / "video_meta.json"
        if not mp4s or not meta.exists():
            continue
        print(f"  Uploading: {p['dir_name']}...")
        result = subprocess.run(
            [PYTHON, UPLOAD_SCRIPT, str(dp)],
            capture_output=True, text=True, timeout=120)
        if "BV" in result.stdout:
            bv = re.search(r'BV[0-9A-Za-z]{10}', result.stdout)
            if bv:
                print(f"    BV号: {bv.group()}")
                print(f"    URL: https://www.bilibili.com/video/{bv.group()}")
        else:
            print(f"    FAILED: {result.stderr[-200:]}")
        time.sleep(2)  # Brief gap

# ── Main loop ──

def main(mode, papers_path):
    papers = load_papers(papers_path)
    papers = scan_disk_state(papers)
    print_dashboard(papers, mode)
    
    if mode == "slides":
        print(f"{sum(1 for p in papers if p['_status'] == 'mineru_done')} papers ready for slides dispatch")
        print(f"Dispatch subagents with: skill://pdf-to-bilibili, mode=slides, Phase 1→2→3→3.5")
        print(f"Template: D:/Envs/Paper_Survey_Env/.omp/skills/pdf-to-bilibili/scripts/subagent_prompt.md")
        print(f"Dispatch 3-6 subagents at a time. If any fail with empty template, redispatch.")
        print(f"If .tex exists but no PDF, run: handle_slides_failure(paper)")
    
    elif mode == "video":
        # First, dispatch narration agents
        need_narr = [p for p in papers if p["_status"] == "slides_done"]
        print(f"{len(need_narr)} papers need narrations. Dispatch narration agents (6 at a time):")
        print(f"  skill://pdf-to-bilibili, mode=video, Phase 4a ONLY")
        print(f"After narrators complete, call: batch_complete_videos(papers)")
        print(f"Then run Phase 4b (TTS+assembly) with 8 workers")
        
        # Check if narrations are ready and batch complete
        papers = scan_disk_state(papers)
        ready = [p for p in papers if p.get("_status") == "narrations_done"]
        if ready:
            print(f"\n{len(ready)} papers have narrations ready. Running batch TTS+assembly...")
            batch_complete_videos(papers)
            papers = scan_disk_state(papers)
            print_dashboard(papers, mode)
    
    elif mode == "bilibili":
        # First ensure videos are done, then upload
        papers = scan_disk_state(papers)
        need_vid = [p for p in papers if p["_status"] == "narrations_done"]
        need_up = [p for p in papers if p["_status"] == "video_done"]
        
        if need_vid:
            print(f"{len(need_vid)} papers need TTS+assembly. Running batch...")
            batch_complete_videos(papers)
            papers = scan_disk_state(papers)
        
        need_up = [p for p in papers if p["_status"] == "video_done"]
        if need_up:
            print(f"{len(need_up)} papers ready for upload.")
            print(f"Dispatch upload subagent (10 at a time, no gaps) or call: batch_upload(papers)")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: py batch.py <slides|video|bilibili> <papers.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
