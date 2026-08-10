"""
slides_to_video.py — PDF slides to narrated MP4 video pipeline.

Functions:
  parse_beamer_frames(tex_path) -> list[dict]
  parse_beamer_preamble(tex_path) -> dict
  get_page_plan(tex_path) -> list[dict]
  extract_narrations_from_tex(tex_path) -> dict
  write_narrations_to_files(frame_dir, tex_path, annotated_tex_path=None) -> dict
  extract_pdf_text(pdf_path) -> list[str]
  render_slides(pdf_path, output_dir, dpi=200) -> list[str]
  generate_cover(png_path, output_path) -> str
  generate_metadata(preamble, frames, cover_path, output_path) -> str
  tts_slide(text, output_path, lang='zh') -> bool
  assemble_video(frame_dir, output_path, fps=30) -> None

Usage:
  py -c "from slides_to_video import render_slides; render_slides('main.pdf', 'frames')"
  py slides_to_video.py main.tex   (runs full pipeline)
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# ─── LaTeX parsing utilities ───────────────────────────────────────────────

def _strip_latex_macros(text: str) -> str:
    """Strip LaTeX macros keeping their inner text content.

    Handles: \\shl{...}, \\hlbox{...}, \\keyword{...}, \\brandemph{...},
    \\textbf{...}, \\emph{...}, \\textit{...}, \\textsuperscript{...},
    \\cite{...}, \\href{url}{text} -> text, \\metric{val}{label} -> val (label),
    \\domaintag{...}, \\cmark, \\xmark, \\tightgap, \\deckgap, \\smallskip,
    \\medskip, \\figcap{...}{...}, \\setlength{...}{...}, \\renewcommand{...}{...}.
    """
    # Remove comments
    text = re.sub(r'(?<!\\)%.*$', '', text, flags=re.MULTILINE)

    # \\href{url}{text} -> text
    text = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', text)

    # \\cite{...} -> empty (citations add nothing to spoken narration)
    text = re.sub(r'\\cite\{[^}]*\}', '', text)

    # Strip wrapper macros keeping inner content (handle nested braces)
    wrapper_macros = [
        r'\shl', r'\hlbox', r'\keyword', r'\brandemph',
        r'\textbf', r'\emph', r'\textit', r'\textsuperscript',
        r'\domaintag', r'\thc',
    ]
    for macro in wrapper_macros:
        # Match macro{...} with balanced braces
        text = _strip_balanced_brace_macro(text, macro)

    # \\metric{val}{label} -> val (label)
    text = re.sub(r'\\metric\{([^}]*)\}\{([^}]*)\}', r'\1 (\2)', text)

    # Remove standalone symbols and spacing commands
    text = re.sub(r'\\cmark\b', '', text)
    text = re.sub(r'\\xmark\b', '', text)
    text = re.sub(r'\\tightgap\b', '', text)
    text = re.sub(r'\\deckgap\b', '', text)
    text = re.sub(r'\\smallskip\b', '', text)
    text = re.sub(r'\\medskip\b', '', text)
    text = re.sub(r'\\figcap\{[^}]*\}\{[^}]*\}', '', text)
    text = re.sub(r'\\setlength\{[^}]*\}\{[^}]*\}', '', text)
    text = re.sub(r'\\renewcommand\{\\secblurb\}\{([^}]*)\}', '', text)
    text = re.sub(r'\\begin\{[^}]*\}', '', text)
    text = re.sub(r'\\end\{[^}]*\}', '', text)

    # Remove inline math $...$
    text = re.sub(r'\$[^$]*\$', '', text)

    # Remove \\[dimension] and \vspace{...}
    text = re.sub(r'\\\\\[\d+[a-z]*\]', '', text)
    text = re.sub(r'\\vspace\{[^}]*\}', '', text)

    # Remove \\ alone at line end (but not line breaks in general)
    text = re.sub(r'\\\\$', '', text, flags=re.MULTILINE)

    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def _strip_balanced_brace_macro(text: str, macro: str) -> str:
    """Strip \\macro{...} where braces are balanced, keeping inner content."""
    pattern = re.escape(macro) + r'\{'
    result = []
    i = 0
    while i < len(text):
        m = re.search(pattern, text[i:])
        if not m:
            result.append(text[i:])
            break
        start = i + m.start()
        brace_start = start + len(macro) + 1  # after {
        result.append(text[i:start])

        # Find matching closing brace
        depth = 1
        j = brace_start
        while j < len(text) and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            if depth > 0:
                j += 1

        inner = text[brace_start:j]
        result.append(inner)
        i = j + 1  # skip past }
    return ''.join(result)


def _extract_braced_arg(text: str) -> str:
    """Extract content inside the first pair of balanced braces."""
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start:i]
    return ''


def _extract_bracketed_arg(text: str) -> str:
    """Extract optional [...] argument content."""
    m = re.match(r'\s*\[([^\]]*)\]', text)
    return m.group(1) if m else ''


# ─── Preamble parsing ──────────────────────────────────────────────────────

_CONFERENCE_TID_MAP = {
    # AI / Robotics → 209 (人工智能)
    'RSS': 209,
    'ICRA': 209,
    'IROS': 209,
    'CoRL': 209,
    'RA-L': 209,
    'Science Robotics': 209,
    'Robotics: Science and Systems': 209,
    # CS / CV / ML → 208 (计算机技术)
    'CVPR': 208,
    'ICCV': 208,
    'ECCV': 208,
    'NeurIPS': 208,
    'ICML': 208,
    'ICLR': 208,
    'ACL': 208,
    'EMNLP': 208,
    'AAAI': 208,
    'IJCAI': 208,
    'SIGGRAPH': 208,
    'CHI': 208,
    # General science → 124 (科学科普)
    'Nature': 124,
    'Science': 124,
    'PNAS': 124,
    'arXiv': 124,
}


def _lookup_tid(venue: str) -> tuple:
    """Return (tid, tid_name) for a conference/journal venue."""
    for key, tid in _CONFERENCE_TID_MAP.items():
        if key.lower() in venue.lower():
            tid_names = {124: '科学科普', 208: '计算机技术', 209: '人工智能', 210: '软件应用'}
            return tid, tid_names.get(tid, '计算机技术')
    return 208, '计算机技术'


def parse_beamer_preamble(tex_path: str) -> dict:
    """Extract {title, subtitle, author, venue, year, domains, urls} from Beamer preamble.

    Parses: \\title, \\subtitle, \\author, \\setsource{venue}{year},
    \\setdomains{\\domaintag{...}...}, and \\href{url}{text} in 论文信息 frame.
    """
    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {
        'title': '', 'short_title': '', 'subtitle': '',
        'author': '', 'venue': '', 'year': '',
        'domains': [], 'source_url': '', 'code_url': '', 'project_url': '',
    }

    # \\title[short]{full}
    m = re.search(r'\\title(?:\[([^\]]*)\])?\{((?:[^{}]|\{[^{}]*\})*)\}', content)
    if m:
        result['short_title'] = m.group(1) or ''
        result['title'] = _strip_latex_macros(m.group(2))

    # \\subtitle{...}
    m = re.search(r'\\subtitle\{((?:[^{}]|\{[^{}]*\})*)\}', content)
    if m:
        result['subtitle'] = _strip_latex_macros(m.group(1))

    # \\author[short]{full}
    m = re.search(r'\\author(?:\[([^\]]*)\])?\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', content)
    if m:
        result['author'] = _strip_latex_macros(m.group(2))

    # \\setsource{venue}{year}
    m = re.search(r'\\setsource\{([^}]*)\}\{([^}]*)\}', content)
    if m:
        result['venue'] = m.group(1).strip()
        result['year'] = m.group(2).strip()

    # \\setdomains{\\domaintag{...}\\domaintag{...}...} — handles nested braces
    m = re.search(r'\\setdomains\{', content)
    if m:
        start = m.end()
        depth = 1
        pos = start
        while pos < len(content) and depth > 0:
            if content[pos] == '{':
                depth += 1
            elif content[pos] == '}':
                depth -= 1
            pos += 1
        domains_text = content[start:pos-1]
        for dm in re.finditer(r'\\domaintag\{([^}]*)\}', domains_text):
            result['domains'].append(dm.group(1))

    # Extract URLs from 论文信息 frame: \\href{url}{text}
    # Look for the frame: \\begin{frame}{论文信息} ... \\end{frame}
    info_frame = re.search(
        r'\\begin\{frame\}\{论文信息\}(.*?)\\end\{frame\}', content, re.DOTALL)
    if info_frame:
        frame_text = info_frame.group(1)
        hrefs = re.findall(r'\\href\{([^}]*)\}\{([^}]*)\}', frame_text)
        for url, label in hrefs:
            if 'github' in url.lower():
                result['code_url'] = url
            elif 'huggingface' in url.lower() or 'project' in label.lower() or 'website' in label.lower():
                result['project_url'] = url
            elif 'arxiv' in url.lower() or 'paper' in label.lower():
                result['source_url'] = url
            elif result['project_url']:
                pass  # already set
            elif not result['source_url']:
                result['source_url'] = url
            else:
                result['project_url'] = url

    return result


# ─── Frame parsing ─────────────────────────────────────────────────────────

def parse_beamer_frames(tex_path: str) -> list:
    """Parse Beamer .tex into structured frame data.

    Returns list of dicts: {
        page_num: int, title: str, section: str, blurb: str,
        items: [str], callout: str, block_text: str,
        has_figure: bool, is_plain: bool, metrics: [(str, str)]
    }
    Pages are numbered from 1 following the frame order in the .tex file.
    """
    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    frames = []
    current_section = ''
    current_blurb = ''
    page_num = 0

    # Track \\renewcommand{\\secblurb}{...}
    blurb_positions = list(re.finditer(
        r'\\renewcommand\{\\secblurb\}\{((?:[^{}]|\{[^{}]*\})*)\}', content))
    blurb_map = {}  # char position -> blurb text
    for m in blurb_positions:
        blurb_map[m.start()] = _strip_latex_macros(m.group(1))

    # Track \\section{...}
    section_positions = list(re.finditer(r'\\section\{([^}]*)\}', content))
    sections = [(m.start(), m.group(1)) for m in section_positions]

    # Find all frames
    # Match \begin{frame}[opts]{title} or \begin{frame}[opts] (titleless, e.g. \titlepage)
    frame_starts = list(re.finditer(
        r'\\begin\{frame\}(?:\[([^\]]*)\])?(?:\{([^}]*)\})?', content))

    for idx, fm in enumerate(frame_starts):
        page_num += 1
        frame_opts = fm.group(1) or ''
        frame_title = _strip_latex_macros(fm.group(2) or '')

        # Find the matching \end{frame}
        # \end{frame} = 11 chars, \begin{frame} = 13 chars
        depth = 1
        pos = fm.end()
        while pos < len(content) and depth > 0:
            if content[pos:pos+11] == '\\end{frame}':
                depth -= 1
                if depth == 0:
                    break
                pos += 11
            elif content[pos:pos+13] == '\\begin{frame}':
                depth += 1
                pos += 13
            else:
                pos += 1
        frame_body = content[fm.end():pos]

        # Determine section context for this frame
        frame_char_start = fm.start()
        for s_start, s_name in reversed(sections):
            if s_start < frame_char_start:
                current_section = s_name
                break
        # Find most recent blurb before this frame
        for b_start in sorted(blurb_map.keys(), reverse=True):
            if b_start < frame_char_start:
                current_blurb = blurb_map[b_start]
                break

        # Extract items
        items = []
        item_matches = re.findall(r'\\item\s+(.*?)(?=\\item|\\(?:begin|end)\{|$)',
                                  frame_body, re.DOTALL)
        for item_text in item_matches:
            cleaned = _strip_latex_macros(item_text).strip()
            if cleaned and len(cleaned) > 2:
                items.append(cleaned)

        # Extract callout
        callout_text = ''
        callout_m = re.search(
            r'\\begin\{callout\}(?:\[([^\]]*)\])?\s*(.*?)\\end\{callout\}',
            frame_body, re.DOTALL)
        if callout_m:
            callout_text = _strip_latex_macros(callout_m.group(2)).strip()

        # Extract block/exampleblock text
        block_text = ''
        for block_env in ['block', 'exampleblock']:
            for block_m in re.finditer(
                    rf'\\begin\{{{block_env}\}}\{{[^}}]*\}}\s*(.*?)\\end\{{{block_env}\}}',
                    frame_body, re.DOTALL):
                block_text += _strip_latex_macros(block_m.group(1)) + '\n'

        # Extract metrics
        metrics = []
        for mm in re.finditer(r'\\metric\{([^}]*)\}\{([^}]*)\}', frame_body):
            metrics.append((mm.group(1).strip(), mm.group(2).strip()))

        # Detect figures
        has_figure = bool(re.search(r'\\includegraphics', frame_body))

        # Detect plain figure frames
        is_plain = 'plain' in frame_opts

        # Detect special frames to potentially skip
        is_titlepage = '\\titlepage' in frame_body
        is_toc = '\\tableofcontents' in frame_body
        is_qa = 'Q&A' in frame_title or 'Q\\&A' in frame_title

        frames.append({
            'page_num': page_num,
            'title': frame_title,
            'section': current_section,
            'blurb': current_blurb,
            'items': items,
            'callout': callout_text,
            'block_text': block_text.strip(),
            'has_figure': has_figure,
            'is_plain': is_plain,
            'is_titlepage': is_titlepage,
            'is_toc': is_toc,
            'is_qa': is_qa,
            'metrics': metrics,
        })

    return frames


def extract_narrations_from_tex(tex_path: str) -> dict:
    """Extract % NARRATION: comments from an annotated .tex file.

    Matches each narration to its nearest preceding \\end{frame} line,
    keyed by that frame's 1-indexed position among all frames.
    This correctly handles missing/extra narrations — each narration
    stays aligned to its intended frame by position, not by count.
    """
    with open(tex_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find all \\end{frame} positions with their 1-indexed frame numbers
    frame_ends = []  # (line_index, frame_number)
    frame_count = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('\\end{frame}'):
            frame_count += 1
            frame_ends.append((i, frame_count))

    # Match each % NARRATION: to its nearest preceding \\end{frame}
    narrations = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('% NARRATION:'):
            text = stripped[len('% NARRATION:'):].strip()
            # Walk backward to find the nearest preceding \\end{frame}
            nearest_frame = None
            for fe_line, fe_num in reversed(frame_ends):
                if fe_line < i:
                    nearest_frame = fe_num
                    break
            if nearest_frame is not None:
                narrations[nearest_frame] = text

    return narrations

# ─── Page plan (PDF-to-frame mapping) ──────────────────────────────────────

def get_page_plan(tex_path: str) -> list:
    """Parse .tex to predict PDF page order, accounting for \\section{} pages.

    Beamer themes (Madrid, sustech) insert a section divider frame via
    \\AtBeginSection before each \\section{}. This function tracks both
    explicit \\begin{frame} blocks and implicit section frames.

    Returns a list where each entry is:
      {'type': 'frame', 'frame_idx': N, 'title': str}
      {'type': 'section', 'section_name': str}
    in document (PDF page) order.
    """
    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    plan = []
    frame_idx = 0
    in_appendix = False

    # Find all \section{...} and \begin{frame} in document order
    # Pattern matches \section{name} (possibly with leading whitespace)
    section_pat = re.compile(r'(?<!\\)\\section\{([^}]*)\}')
    # Pattern matches \begin{frame}[opts]{title} or \begin{frame}[opts]
    frame_pat = re.compile(
        r'(?<!\\)\\begin\{frame\}(?:\[([^\]]*)\])?(?:\{([^}]*)\})?')
    # Track \appendix
    appendix_pat = re.compile(r'(?<!\\)\\appendix\b')

    # Find all occurrences and sort by position
    events = []
    for m in section_pat.finditer(content):
        # Check if line is a comment
        line_start = content.rfind('\n', 0, m.start()) + 1
        if content[line_start:line_start+1] != '%':
            events.append((m.start(), 'section', m.group(1)))
    for m in frame_pat.finditer(content):
        line_start = content.rfind('\n', 0, m.start()) + 1
        if content[line_start:line_start+1] != '%':
            events.append((m.start(), 'frame', m.group(2) or ''))
    for m in appendix_pat.finditer(content):
        line_start = content.rfind('\n', 0, m.start()) + 1
        if content[line_start:line_start+1] != '%':
            events.append((m.start(), 'appendix', ''))

    events.sort(key=lambda x: x[0])

    for _pos, kind, arg in events:
        if kind == 'appendix':
            in_appendix = True
        elif kind == 'section':
            if not in_appendix:
                # Only pre-appendix sections generate section pages
                plan.append({'type': 'section', 'section_name': arg})
        elif kind == 'frame':
            frame_idx += 1
            plan.append({'type': 'frame', 'frame_idx': frame_idx, 'title': arg})

    return plan


def write_narrations_to_files(frame_dir: str, tex_path: str,
                              annotated_tex_path: str = None) -> dict:
    """Extract narrations and write .txt files at correct PDF page positions.

    Handles the mismatch between frame numbering and PDF page numbering
    caused by \\AtBeginSection section divider pages.

    Args:
        frame_dir: Directory to write slide_NNN.txt files.
        tex_path: Path to the original .tex (for get_page_plan).
        annotated_tex_path: Path to the annotated .tex with % NARRATION:
            comments. Defaults to tex_path.

    Returns:
        dict with keys 'count', 'frame_count', 'section_pages', 'files'
    """
    if annotated_tex_path is None:
        annotated_tex_path = tex_path
    page_plan = get_page_plan(tex_path)
    narrations = extract_narrations_from_tex(annotated_tex_path)

    # Build frame_idx -> pdf_page mapping
    frame_to_pdf = {}
    section_pages = []
    for pdf_page, entry in enumerate(page_plan, start=1):
        if entry['type'] == 'frame':
            frame_to_pdf[entry['frame_idx']] = pdf_page
        elif entry['type'] == 'section':
            section_pages.append(pdf_page)

    # Write .txt files at correct PDF page positions
    written = []
    for frame_idx, text in narrations.items():
        pdf_page = frame_to_pdf.get(int(frame_idx))
        if pdf_page is None:
            print(f'  [WARN] Narration for frame {frame_idx} has no PDF page mapping')
            continue
        path = os.path.join(frame_dir, f'slide_{pdf_page:03d}.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        written.append(pdf_page)

    return {
        'count': len(written),
        'frame_count': len(narrations),
        'section_pages': section_pages,
        'files': written,
    }
# ─── PDF utilities ─────────────────────────────────────────────────────────

def extract_pdf_text(pdf_path: str) -> list:
    """Extract text from each page of a PDF using PyMuPDF.

    Returns list of strings, one per page.
    """
    import fitz
    doc = fitz.open(pdf_path)
    texts = []
    for page in doc:
        texts.append(page.get_text('text'))
    doc.close()
    return texts


def render_slides(pdf_path: str, output_dir: str, dpi: int = 200) -> list:
    """Render PDF pages to numbered PNG images.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save PNGs (created if not exists).
        dpi: Rendering resolution (default 200).

    Returns:
        List of output PNG paths, sorted by page number.
    """
    from pdf2image import convert_from_path

    os.makedirs(output_dir, exist_ok=True)

    poppler_path = r'C:\texlive\2024\bin\windows'
    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)

    paths = []
    for i, img in enumerate(images):
        out_path = os.path.join(output_dir, f'slide_{i+1:03d}.png')
        img.save(out_path, 'PNG')
        paths.append(out_path)

    return paths


# ─── Cover image ───────────────────────────────────────────────────────────

def generate_cover(png_path: str, output_path: str, poster_path: str = None) -> str:
    """Create cover image directly from first slide PNG (no scaling).

    Poster generation is handled separately by markdown-to-video-cover skill.
    Cover is always the raw first slide for Bilibili upload.
    """
    import shutil
    shutil.copy(png_path, output_path)
    return os.path.abspath(output_path)


# ─── Bilibili metadata ─────────────────────────────────────────────────────

def generate_metadata(preamble: dict, frames: list, cover_path: str, output_path: str) -> str:
    """Generate video_meta.json for Bilibili upload.

    Args:
        preamble: Dict from parse_beamer_preamble().
        frames: List from parse_beamer_frames().
        cover_path: Relative path to cover.png (e.g. 'cover.png').
        output_path: Path to save video_meta.json.

    Returns:
        Absolute path to the generated JSON file.
    """
    venue = preamble.get('venue', '')
    year = preamble.get('year', '')
    title = preamble.get('title', 'Unknown Paper')
    title_en = preamble.get('subtitle', '')
    if not title_en:
        title_en = title  # fallback

    tid, tid_name = _lookup_tid(venue)

    # Tags from domains + venue + paper name
    tags = preamble.get('domains', [])
    if venue:
        tags.append(f'{venue} {year}'.strip())
    tags.append('论文分享')
    # Add paper short name if any
    short_title = preamble.get('short_title', '')
    if short_title and short_title not in tags:
        # Truncate to fit
        if len(short_title) <= 20:
            tags.insert(0, short_title)
    # Max 10 tags
    tags = tags[:10]

    # Find the 一句话概括 callout from 论文信息 frame
    one_line_summary = ''
    highlights_items = []
    links = {}

    for f in frames:
        if f['title'] == '论文信息':
            one_line_summary = f.get('callout', '')
        if '研究背景' in f.get('title', '') or '在做什么' in f.get('title', ''):
            highlights_items = f.get('items', [])[:5]

    # Extract links from preamble
    if preamble.get('source_url'):
        links['论文链接'] = preamble['source_url']
    if preamble.get('code_url'):
        links['代码'] = preamble['code_url']
    if preamble.get('project_url'):
        links['项目网站'] = preamble['project_url']

    # Build description
    desc_lines = []
    desc_lines.append(f"【论文分享】{title_en} ({venue} {year}) — {one_line_summary}" if one_line_summary
                      else f"【论文分享】{title_en} ({venue} {year})")

    if highlights_items:
        desc_lines.append('')
        for item in highlights_items[:5]:
            desc_lines.append(f"- {item}")

    if links:
        desc_lines.append('')
        for label, url in links.items():
            desc_lines.append(f"{label}：{url}")

    desc_lines.append('')
    desc_lines.append('本视频由 AI 自动生成，仅供学术交流使用。')
    desc = '\n'.join(desc_lines)

    # Dynamic feed text
    short_for_dynamic = preamble.get('short_title', title_en)
    if len(short_for_dynamic) > 50:
        short_for_dynamic = short_for_dynamic[:47] + '...'
    summary_short = one_line_summary[:100] if one_line_summary else ''
    dynamic = f"新一期论文分享：{short_for_dynamic} ({venue} {year}) — {summary_short}"
    if len(dynamic) > 256:
        dynamic = dynamic[:253] + '...'

    # Title with venue prefix: 【Venue Year】ShortName — Title
    # SURVEY GUARD: if this is a survey deck, use Chinese default to avoid
    # the English \title{} text blowing past Bilibili's 80-char cap.
    # Phase 8 of deep-survey-to-video will refine this further.
    _domains = preamble.get('domains', [])
    _is_survey = any('survey' in d.lower() for d in _domains)
    venue_prefix = f"【{venue} {year}】" if venue and year else ""
    if _is_survey:
        # Use venue+year prefix only; the descriptive hook must be Chinese
        meta_title = f"{venue_prefix}调研报告" if venue_prefix else title[:80]
    else:
        meta_title = (venue_prefix + title)[:80]

    meta = {
        'title': meta_title,
        'title_en': title_en,
        'tid_name': tid_name,
        'tag': tags,
        'desc': desc,
        'copyright': 1,
        'source': '',
        'dynamic': dynamic,
        'no_reprint': 0,
        'cover_path': cover_path,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return os.path.abspath(output_path)


# ─── TTS ───────────────────────────────────────────────────────────────────
# edge-tts (lightweight, no GPU needed).

import asyncio

_EDGE_VOICES = {
    'zh': 'zh-CN-XiaoxiaoNeural',
    'en': 'en-US-AriaNeural',
}

def _split_text_at_sentences(text: str, max_chars: int = 180) -> list:
    """Split text at sentence boundaries to keep chunks under max_chars.
    Chinese: splits at 。！？ English: splits at . ! ?
    Falls back to mid-sentence split if no boundary found within max_chars."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    remaining = text
    while len(remaining) > max_chars:
        candidates = []
        for sep in ['。', '！', '？', '. ', '! ', '? ']:
            idx = remaining[:max_chars].rfind(sep)
            if idx > max_chars // 2:
                candidates.append(idx + len(sep))
        if candidates:
            split_at = max(candidates)
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()
        else:
            for sep in ['，', ', ', '；', '; ', ' ']:
                idx = remaining[:max_chars].rfind(sep)
                if idx > max_chars // 2:
                    chunks.append(remaining[:idx + len(sep)])
                    remaining = remaining[idx + len(sep):].lstrip()
                    break
            else:
                chunks.append(remaining[:max_chars])
                remaining = remaining[max_chars:]
    if remaining:
        chunks.append(remaining)
    return chunks


def tts_slide(text: str, output_path: str, lang: str = 'zh') -> bool:
    """Convert text to speech via edge-tts (chunked to avoid ~60s server limit)."""
    if not text or not text.strip():
        return False
    voice = _EDGE_VOICES.get(lang, _EDGE_VOICES['zh'])
    chunks = _split_text_at_sentences(text, max_chars=180)
    async def _run():
        import edge_tts
        if len(chunks) == 1:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
        else:
            import tempfile
            tmp_files = []
            for i, chunk in enumerate(chunks):
                tmp = tempfile.mktemp(suffix='.mp3')
                tmp_files.append(tmp)
                communicate = edge_tts.Communicate(chunk, voice)
                await communicate.save(tmp)
            concat_list = tempfile.mktemp(suffix='.txt')
            with open(concat_list, 'w') as f:
                for tmp in tmp_files:
                    f.write(f"file '{tmp}'\n")
            proc = await asyncio.create_subprocess_exec(
                'ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'concat', '-safe', '0', '-i', concat_list,
                '-c', 'copy', output_path,
            )
            await proc.wait()
            for tmp in tmp_files:
                try: os.unlink(tmp)
                except OSError: pass
            try: os.unlink(concat_list)
            except OSError: pass
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(_run())
        if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
            print(f'  [OK] edge-tts ({voice}) -> {os.path.basename(output_path)}')
            return True
        else:
            print(f'  [FAIL] edge-tts empty -> {os.path.basename(output_path)}')
            return False
    except Exception as e:
        print(f'  [FAIL] edge-tts -> {os.path.basename(output_path)}: {e}')
        if os.path.exists(output_path):
            try: os.unlink(output_path)
            except OSError: pass
        return False


def batch_tts_parallel(frame_dir: str, lang: str = 'zh', max_workers: int = 8) -> int:
    """Run TTS on all slide_NNN.txt files in parallel via ThreadPoolExecutor.

    Args:
        frame_dir: Directory containing slide_NNN.txt files.
        lang: Voice language ('zh' or 'en').
        max_workers: Parallel workers (default 8).

    Returns:
        Number of slides processed.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = []
    for fname in sorted(os.listdir(frame_dir)):
        if not fname.startswith('slide_') or not fname.endswith('.txt'):
            continue
        basename = fname[:-4]
        txt_path = os.path.join(frame_dir, fname)
        mp3_path = os.path.join(frame_dir, f'{basename}.mp3')
        if os.path.exists(mp3_path):
            continue
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
        if text.strip():
            tasks.append((basename, text, mp3_path))

    if not tasks:
        print('  TTS: all MP3s already present, skipping')
        return 0

    def _do(args):
        name, text, mp3 = args
        ok = tts_slide(text, mp3, lang=lang)
        return name, ok

    print(f'  TTS: {len(tasks)} slides, {max_workers} parallel workers...')
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_do, t): t[0] for t in tasks}
        for future in as_completed(futures):
            name, ok = future.result()
            if ok:
                done += 1
    print(f'  TTS complete: {done}/{len(tasks)}')
    return done


# ─── Video assembly ────────────────────────────────────────────────────────

def _encode_one_slide(png_path, frame_dir, vf_filter, pad_sec):
    """Encode one slide: ffmpeg still-image + audio. Called in parallel.
    Assumes .mp3 already exists (TTS done beforehand)."""
    import subprocess as _sp
    basename = os.path.splitext(os.path.basename(png_path))[0]
    mp3_path = os.path.join(frame_dir, f'{basename}.mp3')
    final_mp4 = os.path.join(frame_dir, f'{basename}_final.mp4')
    txt_path = os.path.join(frame_dir, f'{basename}.txt')


    has_audio = os.path.exists(mp3_path)
    if has_audio:
        probe_cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', mp3_path,
        ]
        probe_result = _sp.run(probe_cmd, capture_output=True, text=True)
        try:
            audio_dur = float(probe_result.stdout.strip())
        except ValueError:
            audio_dur = 10.0
        total_dur = audio_dur + pad_sec
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-loop', '1', '-i', png_path, '-i', mp3_path,
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-preset', 'medium', '-crf', '23',
            '-pix_fmt', 'yuv420p', '-t', str(total_dur),
            '-vf', vf_filter,
            '-af', f'aformat=sample_rates=44100:channel_layouts=stereo,volume=2.5,apad=whole_dur={total_dur}',
            '-c:a', 'aac', '-b:a', '128k', final_mp4,
        ]
    else:
        total_dur = 2.0 + pad_sec
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-loop', '1', '-i', png_path,
            '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-c:v', 'libx264', '-tune', 'stillimage',
            '-preset', 'medium', '-crf', '23',
            '-pix_fmt', 'yuv420p', '-t', str(total_dur),
            '-vf', vf_filter, final_mp4,
        ]

    kind = "audio" if has_audio else "silent"
    print(f'  {basename} ({kind}, {total_dur:.1f}s)...')
    result = _sp.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f'  [WARN] ffmpeg failed for {basename}: {result.stderr[-100:]}')
        return None
    return final_mp4


def assemble_video(frame_dir: str, output_path: str, fps: int = 30,
                   pad_sec: float = 0.5, speed: float = 1.0,
                   max_workers: int = None) -> None:
    """Assemble slide PNGs and MP3 audio into a narrated MP4 video.

    Parallel ffmpeg encode per slide via ThreadPoolExecutor.
    TTS must already be done (MP3 files present). Optional speedup via setpts + atempo.

    Args:
        frame_dir: Directory containing slide_NNN.png, .txt, .mp3.
        output_path: Output MP4 path.
        pad_sec: Freeze-frame extension per slide (default 0.5).
        speed: Playback speed multiplier (1.0=normal, 1.25=25% faster).
        max_workers: Parallel ffmpeg workers (default: min(8, cpu_count)).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import glob as glob_mod
    from PIL import Image

    if max_workers is None:
        max_workers = min(8, (os.cpu_count() or 4))

    png_files = sorted(glob_mod.glob(os.path.join(frame_dir, 'slide_*.png')))
    if not png_files:
        raise FileNotFoundError(f'No slide PNGs found in {frame_dir}')

    first_img = Image.open(png_files[0])
    print(f'Source slide dimensions: {first_img.size[0]}x{first_img.size[1]}')

    vf_filter = (
        'scale=1920:1200:force_original_aspect_ratio=decrease,'
        'pad=1920:1200:(ow-iw)/2:(oh-ih)/2:black'
    )
    # --- Parallel TTS (if any .txt files lack .mp3) ---
    batch_tts_parallel(frame_dir)

    # --- Parallel encode each slide ---
    print(f'  Parallel encoding {len(png_files)} slides ({max_workers} workers)...')
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_encode_one_slide, p, frame_dir, vf_filter, pad_sec): p
                   for p in png_files}
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)

    results.sort(key=lambda p: os.path.basename(p))

    # Concat
    concat_list_path = os.path.join(frame_dir, 'filelist.txt')
    with open(concat_list_path, 'w') as f:
        for r in results:
            f.write(f"file '{os.path.abspath(r)}'\n")

    concat_output = output_path.replace('.mp4', '_concat.mp4') if speed != 1.0 else output_path

    print(f'  Concatenating {len(results)} segments...')
    concat_cmd = [
        'ffmpeg', '-y', '-loglevel', 'error',
        '-f', 'concat', '-safe', '0',
        '-i', os.path.abspath(concat_list_path),
        '-c', 'copy', os.path.abspath(concat_output),
    ]
    result = subprocess.run(concat_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg concat failed: {result.stderr}')

    # Speedup
    if speed != 1.0:
        print(f'  Applying {speed}x speedup...')
        speed_cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-i', os.path.abspath(concat_output),
            '-vf', f'setpts=PTS/{speed}',
            '-af', f'atempo={speed}',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            os.path.abspath(output_path),
        ]
        result = subprocess.run(speed_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f'ffmpeg speedup failed: {result.stderr}')
        if os.path.exists(concat_output):
            os.unlink(concat_output)

    import json as _json
    probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'json', os.path.abspath(output_path)]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    try:
        dur = float(_json.loads(probe_result.stdout)['format']['duration'])
        print(f'Video assembled: {os.path.abspath(output_path)} ({dur:.1f}s)')
    except Exception:
        print(f'Video assembled: {os.path.abspath(output_path)}')

# ─── Main (full pipeline) ──────────────────────────────────────────────────

def run_full_pipeline(paper_dir: str) -> dict:
    """Run the full slides-to-video pipeline.

    Args:
        paper_dir: Paper directory containing slides-beamer/ (with main.tex, main.pdf).
                   Example: '论文分享/RSS 2026 - LDA-1B/'

    All video outputs go into <paper_dir>/video/.

    Returns:
        Dict with output paths and stats.
    """
    paper_dir = os.path.abspath(paper_dir)
    tex_path = os.path.join(paper_dir, 'slides-beamer', 'main.tex')
    pdf_path = os.path.join(paper_dir, 'slides-beamer', 'main.pdf')
    video_dir = os.path.join(paper_dir, 'video')
    frame_dir = os.path.join(video_dir, 'video_frames')
    cover_path = os.path.join(video_dir, 'cover.png')
    meta_path = os.path.join(video_dir, 'video_meta.json')
    poster_path = os.path.join(paper_dir, 'poster', 'poster.png')

    paper_name = os.path.basename(paper_dir.rstrip('/\\'))
    paper_name = paper_name.split(' - ')[-1] if ' - ' in paper_name else paper_name
    video_path = os.path.join(video_dir, f'{paper_name}_narrated.mp4')

    os.makedirs(video_dir, exist_ok=True)
    os.makedirs(frame_dir, exist_ok=True)

    print(f'=== Pipeline: {paper_name} ===')
    print(f'Paper dir:  {paper_dir}')
    print(f'Video dir:  {video_dir}')

    # 1. Parse preamble and frames
    print('\n[1/6] Parsing LaTeX...')
    preamble = parse_beamer_preamble(tex_path)
    frames = parse_beamer_frames(tex_path)
    print(f'  Preamble: {preamble["title"][:60]}...')
    print(f'  Frames: {len(frames)}')

    # 2. Render slides
    print('\n[2/6] Rendering slides...')
    slide_paths = render_slides(pdf_path, frame_dir, dpi=200)
    print(f'  Rendered {len(slide_paths)} slides')

    # 3. Generate cover
    print('\n[3/6] Generating cover...')
    cover = generate_cover(slide_paths[0], cover_path, poster_path=poster_path)
    print(f'  Cover: {cover}')

    # 4. Generate metadata
    print('\n[4/6] Generating metadata...')
    meta = generate_metadata(preamble, frames, 'cover.png', meta_path)
    print(f'  Metadata: {meta}')

    # 5. Narration and TTS — done in parallel inside assemble_video
    print('\n[5/6] TTS + Video: parallel encode with Qwen3 TTS (Ono Anna)...')

    # 6. Assemble video (parallel TTS + encode, 1.25x speedup)
    print('\n[6/6] Assembling video (parallel, 1.25x)...')
    assemble_video(frame_dir, video_path, pad_sec=0.5, speed=1.25)

    return {
        'paper_name': paper_name,
        'paper_dir': paper_dir,
        'video_dir': video_dir,
        'video': video_path,
        'cover': cover_path,
        'metadata': meta_path,
        'frames': frame_dir,
        'num_slides': len(slide_paths),
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: py slides_to_video.py <paper_dir>')
        print('  <paper_dir> must contain slides-beamer/main.tex and slides-beamer/main.pdf')
        print('  Example: py slides_to_video.py "论文分享/RSS 2026 - LDA-1B"')
        sys.exit(1)

    paper_dir = sys.argv[1]
    result = run_full_pipeline(paper_dir)
    print(f'\nDone! Output: {result["video"]}')
