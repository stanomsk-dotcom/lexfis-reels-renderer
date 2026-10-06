#!/usr/bin/env python3
"""Create five clean, Cyrillic vector scenes without external image APIs."""
from __future__ import annotations
import html
import re
import subprocess
from pathlib import Path


def _segments(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    if len(parts) < 4:
        words = text.split()
        step = max(1, (len(words) + 4) // 5)
        parts = [" ".join(words[i:i + step]) for i in range(0, len(words), step)]
    return parts[:6]


def _wrap(text: str, width: int = 26) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        if current and len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip(" ,;:") + "…"
    return lines


def _svg(title: str, segment: str, index: int, total: int, prompt: str) -> str:
    colors = [("#102035", "#244760", "#E9C77D"), ("#12283A", "#28605E", "#9BD4C3"), ("#1A2438", "#50516B", "#F0C17A")]
    bg, accent_bg, gold = colors[(index - 1) % len(colors)]
    safe_title = html.escape(title[:72])
    safe_prompt = html.escape((prompt or "ЮРИДИЧЕСКИЙ РАЗБОР")[:64])
    copy = "".join(f'<text x="90" y="850" class="copy">{html.escape(line)}</text>' for line in _wrap(segment))
    # Alternate legal document, balance scales, and clock line art.
    if index % 3 == 1:
        icon = f'<path d="M610 360h260l90 90v360H610zM870 360v100h90M665 530h230M665 590h190M665 650h220" fill="none" stroke="{gold}" stroke-width="12" stroke-linecap="round"/><circle cx="880" cy="770" r="58" fill="{accent_bg}" stroke="{gold}" stroke-width="9"/>'
    elif index % 3 == 2:
        icon = f'<g fill="none" stroke="{gold}" stroke-width="12" stroke-linecap="round"><path d="M540 520h440M760 390v370M620 500l-90 180h180zM900 500l-90 180h180zM650 790h220"/></g>'
    else:
        icon = f'<g fill="none" stroke="{gold}" stroke-width="12" stroke-linecap="round"><circle cx="760" cy="590" r="190"/><path d="M760 460v140l100 65"/></g>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="{accent_bg}"/></linearGradient></defs><rect width="1080" height="1920" fill="url(#g)"/><path d="M0 1200Q500 950 1080 1180V1920H0Z" fill="#07131f" opacity=".35"/><style>.brand{{font:700 30px 'DejaVu Sans';letter-spacing:5px;fill:white}}.tag{{font:600 23px 'DejaVu Sans';letter-spacing:2px;fill:{gold}}}.small{{font:400 25px 'DejaVu Sans';fill:white;opacity:.7}}.copy{{font:700 48px 'DejaVu Sans';fill:white}}</style><text x="86" y="112" class="brand">LEXFIS</text><text x="86" y="168" class="tag">ПРАВО · ПРАКТИКА · РЕШЕНИЯ</text><text x="86" y="280" class="small">{safe_prompt}</text>{icon}<rect x="70" y="760" width="940" height="340" rx="28" fill="#091522" opacity=".88" stroke="{gold}" stroke-opacity=".55" stroke-width="3"/>{copy}<text x="86" y="1190" class="small">{safe_title}</text><rect x="86" y="1790" width="908" height="5" fill="white" opacity=".2"/><rect x="86" y="1790" width="{908 * index / total}" height="5" fill="{gold}"/><text x="86" y="1848" class="small">LEXFIS.RU</text><text x="994" y="1848" text-anchor="end" class="small">{index:02}/{total:02}</text></svg>'''


def generate_scenes(title: str, voiceover: str, prompt: str, work: Path) -> list[Path]:
    chunks = _segments(voiceover)
    if len(chunks) < 4:
        raise ValueError("Voiceover must support at least four scene captions")
    result = []
    for i, chunk in enumerate(chunks, 1):
        src, img = work / f"scene_{i:02}.svg", work / f"scene_{i:02}.png"
        src.write_text(_svg(title, chunk, i, len(chunks), prompt), encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", "1080", "-h", "1920", "-o", str(img), str(src)], check=True, capture_output=True)
        result.append(img)
    return result
