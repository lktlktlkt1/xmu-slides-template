#!/usr/bin/env python3
"""
Bilibili upload CLI — read video_meta.json, upload MP4 + cover via Python biliup v1.2+.

Usage:
  py scripts/upload.py <paper_dir>         # upload from video_meta.json
  py scripts/upload.py --login             # interactive QR-code login

Requires: pip install biliup>=1.2
Cookie store: %USERPROFILE%\.bilibili\cookies.json
"""
import json, os, glob, subprocess, sys, argparse
from pathlib import Path

COOKIE_DIR = Path.home() / ".bilibili"
COOKIE_PATH = COOKIE_DIR / "cookies.json"


def login():
    """Interactive QR-code login."""
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    cmd = ["py", "-m", "biliup", "-u", str(COOKIE_PATH), "login"]
    print("Opening QR-code login in terminal. Scan with Bilibili app.")
    print(f"Cookies saved to: {COOKIE_PATH}")
    subprocess.run(cmd, check=True)

def diagnose():
    """Diagnose biliup lock state and running processes."""
    import re, urllib.request
    lock_dir = os.path.join(os.environ["LOCALAPPDATA"], "biliup", "locks")

    print("=" * 60)
    print("BILIUP DIAGNOSTIC")
    print("=" * 60)

    # ── 1. Lock file analysis ──
    print("\n── Lock Files ──")
    if os.path.isdir(lock_dir):
        locks = [f for f in os.listdir(lock_dir) if f.endswith(".lock")]
        if not locks:
            print("  (no lock files)")
        for lf in locks:
            lock_path = os.path.join(lock_dir, lf)
            m = re.match(r"biliup_upload_(\d+)\.lock", lf)
            uid = m.group(1) if m else "?"
            # Check if any process holds this file open
            result = subprocess.run(
                ["fsutil", "file", "queryProcessesUsing", lock_path],
                capture_output=True, text=True,
            )
            output = result.stdout + result.stderr
            if "not found to be opened" in output.lower():
                print(f"  [STALE]  {lf} (UID={uid}) — safe to remove")
            else:
                # Extract PIDs from "Process 58132" style lines
                pids = re.findall(r"Process\s+(\d+)", output)
                if pids:
                    for pid in pids:
                        info = _proc_info(pid)
                        print(f"  [ACTIVE] {lf} (UID={uid}) — held by PID {pid} ({info})")
                else:
                    print(f"  [STALE?] {lf} (UID={uid}) — fsutil gave unexpected output, assuming stale")
    else:
        print(f"  Lock dir not found: {lock_dir}")

    # ── 2. Running biliup processes ──
    print("\n── Running Biliup Processes ──")
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "processid,commandline"],
        capture_output=True, text=True,
    )
    found = False
    for line in result.stdout.splitlines():
        if "biliup" not in line:
            continue
        # wmic outputs "processid,commandline" — both on same line, PID is last whitespace-delimited token
        stripped = line.strip()
        if not stripped:
            continue
        tokens = stripped.split()
        if len(tokens) < 2:
            continue
        pid = tokens[-1]  # last token is PID
        cmd = " ".join(tokens[:-1])  # everything before it is command line
        if not pid.isdigit():
            continue
        found = True
        # Extract port: -p <port> or --port <port>
        port_m = re.search(r"(?:-p|--port)\s+(\d+)", cmd)
        port = port_m.group(1) if port_m else "?"
        # Health check
        health = "?"
        if port != "?":
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="HEAD")
                resp = urllib.request.urlopen(req, timeout=3)
                health = f"RESPONDING (HTTP {resp.status})"
            except Exception as e:
                health = f"UNRESPONSIVE ({e})"
        print(f"  [RUNNING] PID {pid}  port={port}  {health}")
        print(f"            cmd: {cmd[:120]}")
    if not found:
        print("  (no biliup processes found)")

    # ── 3. Recent upload log ──
    print("\n── Recent Upload Log (download.log) ──")
    log_path = os.path.join(os.getcwd(), "download.log")
    if os.path.exists(log_path):
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            # Filter to biliup_cli lines, show last 15
            biliup_lines = [l.rstrip() for l in lines if "biliup_cli" in l]
            for line in biliup_lines[-15:]:
                print(f"  {line[:150]}")
            if len(biliup_lines) > 15:
                print(f"  ... ({len(biliup_lines)} total biliup_cli log lines)")
        except Exception as e:
            print(f"  Error reading log: {e}")
    else:
        print(f"  No download.log at {log_path}")

    print()


def _proc_info(pid: str) -> str:
    """Get process name for a PID, or return pid if unknown."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            # CSV: "name.exe","pid","session","session#","mem"
            parts = result.stdout.strip().split(",")
            if len(parts) >= 1:
                return parts[0].strip('"')
    except Exception:
        pass
    return f"pid={pid}"


def kill_all(force: bool = False):
    """Kill biliup processes and clean stale lock files."""
    import re

    print("=" * 60)
    print("BILIUP KILL-ALL")
    print("=" * 60)

    # ── 1. Show current state ──
    diagnose()

    # ── 2. Confirm ──
    if not force:
        print("This will kill all biliup processes and remove stale lock files.")
        resp = input("Proceed? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            print("Aborted.")
            return
        print()

    # ── 3. Kill biliup processes ──
    print("── Killing biliup processes ──")
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "processid,commandline"],
        capture_output=True, text=True,
    )
    killed = 0
    for line in result.stdout.splitlines():
        if "biliup" not in line:
            continue
        tokens = line.strip().split()
        if len(tokens) < 2:
            continue
        pid = tokens[-1]  # last token is PID
        if pid.isdigit():
            print(f"  Killing PID {pid}...")
            kr = subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, text=True)
            if kr.returncode == 0:
                print(f"    ✓ Killed")
                killed += 1
            else:
                print(f"    ✗ Failed: {kr.stderr.strip()}")

    if killed == 0:
        print("  (no biliup processes to kill)")
    else:
        print(f"  Killed {killed} process(es)")

    # ── 4. Remove stale lock files ──
    print("\n── Cleaning lock files ──")
    lock_dir = os.path.join(os.environ["LOCALAPPDATA"], "biliup", "locks")
    cleaned = 0
    if os.path.isdir(lock_dir):
        for lf in os.listdir(lock_dir):
            if not lf.endswith(".lock"):
                continue
            lock_path = os.path.join(lock_dir, lf)
            result = subprocess.run(
                ["fsutil", "file", "queryProcessesUsing", lock_path],
                capture_output=True, text=True,
            )
            output = result.stdout + result.stderr
            if "not found to be opened" in output.lower():
                os.remove(lock_path)
                print(f"  ✓ Removed stale: {lf}")
                cleaned += 1
            elif force:
                os.remove(lock_path)
                print(f"  ✓ Force-removed: {lf}")
                cleaned += 1
            else:
                print(f"  ⚠ Skipped (active): {lf}")
    if cleaned == 0:
        print("  (no stale lock files)")
    else:
        print(f"  Cleaned {cleaned} lock file(s)")

    print("\nDone.")



def _find_or_generate_cover(paper_dir: str, video_dir: Path, meta: dict) -> str:
    """Resolve cover image: use video/cover.png, or generate from poster/poster.png."""
    cover_rel = meta.get("cover_path", "cover.png")
    cover_path = str(video_dir / cover_rel) if cover_rel else ""

    if cover_path and os.path.exists(cover_path):
        return cover_path

    # Fallback: use poster from markdown-to-video-cover skill
    poster_png = Path(paper_dir) / "poster" / "poster.png"
    if poster_png.exists():
        print(f"Found poster ({poster_png.stat().st_size // 1024}KB), generating cover...")
        cover_out = str(video_dir / "cover.png")
        _resize_cover(str(poster_png), cover_out)
        print(f"  Cover saved: {cover_out}")
        return cover_out

    if cover_path:
        print(f"WARNING: No cover found at {cover_path} or poster/poster.png")
    return ""


def _resize_cover(src: str, dst: str, width=1920, height=1200):
    """Resize an image to cover dimensions (1920×1200) using ffmpeg."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
         dst],
        capture_output=True, check=True,
    )


def resolve_inputs(paper_dir: str) -> tuple:
    """Resolve MP4, cover, and metadata from a paper directory."""
    video_dir = Path(paper_dir) / "video"
    meta_path = video_dir / "video_meta.json"

    if not meta_path.exists():
        sys.exit(f"ERROR: No video_meta.json at {meta_path}. Run pdf-slides-to-video first.")

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    mp4s = sorted(video_dir.glob("*.mp4"))
    if not mp4s:
        sys.exit(f"ERROR: No MP4 found in {video_dir}")

    mp4_path = str(mp4s[0])
    cover_path = _find_or_generate_cover(paper_dir, video_dir, meta)

    return mp4_path, cover_path, meta

def build_command(mp4_path: str, cover_path: str, meta: dict) -> list:
    """Build biliup upload command from metadata."""
    cmd = [
        "py", "-m", "biliup",
        "-u", str(COOKIE_PATH),
        "upload", mp4_path,
        "--title", meta["title"][:80],
        "--tid", str(meta.get("tid", 124)),
        "--tag", ",".join(meta.get("tag", [])[:10]),
        "--desc", meta.get("desc", ""),
        "--copyright", str(meta.get("copyright", 1)),
        "--no-reprint", str(meta.get("no_reprint", 0)),
        "--submit", "web",
    ]

    if cover_path:
        cmd.extend(["--cover", cover_path])

    if meta.get("copyright") == 2 and meta.get("source"):
        cmd.extend(["--source", meta["source"]])

    dynamic = meta.get("dynamic", "")
    if dynamic:
        cmd.extend(["--dynamic", dynamic[:256]])

    return cmd


def upload(paper_dir: str, extra_args: list[str] = None):
    """Upload video from a paper directory."""
    mp4_path, cover_path, meta = resolve_inputs(paper_dir)

    print(f"=== Bilibili Upload ===")
    print(f"Title:   {meta['title'][:60]}...")
    print(f"Tags:    {meta.get('tag', [])}")
    print(f"File:    {mp4_path} ({os.path.getsize(mp4_path) / 1024 / 1024:.1f} MB)")
    if cover_path:
        print(f"Cover:   {cover_path}")
    print()

    cmd = build_command(mp4_path, cover_path, meta)
    if extra_args:
        cmd.extend(extra_args)

    print("BILIUP COMMAND:")
    print(" \\\n  ".join(f'"{c}"' if " " in c else c for c in cmd))
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)

    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"EXIT: {result.returncode}")

    # Extract BV号
    output = result.stdout + result.stderr
    for line in output.splitlines():
        import re
        m = re.search(r"BV[0-9A-Za-z]{10}", line)
        if m:
            bv = m.group(0)
            print(f"\nBV号: {bv}")
            print(f"URL:  https://www.bilibili.com/video/{bv}")

    # Error classification
    if result.returncode != 0:
        if any(kw in output for kw in ["login", "cookie", "expired", "鉴权", "credential"]):
            print("\nAUTH ERROR: Cookie expired. Re-login: py scripts/upload.py --login")
            sys.exit(2)
        if any(kw in output for kw in ["already exists", "已存在", "duplicate"]):
            print("\nDUPLICATE: Video may already exist. Check your uploads page.")
            sys.exit(3)
        if any(kw in output for kw in ["too large", "过大", "exceeds"]):
            print("\nSIZE ERROR: File exceeds Bilibili size limit.")
            sys.exit(4)
        if any(kw in output for kw in ["过于频繁", "过快"]):
            print("\nRATE LIMIT: Upload too frequent. Wait and retry.")
            sys.exit(5)
        print(f"\nUPLOAD FAILED (exit {result.returncode})")
        sys.exit(1)

    print("\nUpload successful!")


def main():
    parser = argparse.ArgumentParser(description="Bilibili video uploader")
    parser.add_argument("paper_dir", nargs="?", help="Paper directory with video/ subfolder")
    parser.add_argument("--login", action="store_true", help="Interactive QR-code login")
    parser.add_argument("--diagnose", action="store_true", help="Diagnose lock state and running processes")
    parser.add_argument("--kill-all", action="store_true", help="Kill biliup processes and clean stale locks")
    parser.add_argument("--force", action="store_true", help="Skip confirmation for --kill-all")
    args, extra = parser.parse_known_args()

    if args.login:
        login()
    elif args.diagnose:
        diagnose()
    elif args.kill_all:
        kill_all(force=args.force)
    elif args.paper_dir:
        upload(args.paper_dir, extra)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
