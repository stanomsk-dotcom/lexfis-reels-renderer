#!/usr/bin/env python3
"""Build clean, varied legal motion-graphic scenes for vertical Reels."""
from __future__ import annotations
import html
import re
import subprocess
from pathlib import Path


def _segments(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    if len(parts) < 4:
        words = text.split()
        n = min(5, max(4, (len(words) + 11) // 12))
        size = max(1, (len(words) + n - 1) // n)
        parts = [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
    return parts[:6]


def _icon(index: int, gold: str, pale: str) -> str:
    common = f'fill="none" stroke="{gold}" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"'
    icons = [
        f'<g {common}><path d="M400 360h230l110 110v500H400zM630 360v120h110M465 570h210M465 650h250M465 730h175"/><path d="m500 850 55 55 115-135"/></g>',
        f'<g {common}><rect x="435" y="340" width="330" height="590" rx="48"/><path d="M545 405h110M560 845h80"/><rect x="500" y="490" width="200" height="245" rx="18"/><path d="m535 610 45 45 90-105"/><path d="M525 775h150"/></g>',
        f'<g {common}><path d="M390 380h310l95 95v450H390zM700 380v105h95M460 570h220M460 650h170"/><circle cx="720" cy="790" r="125"/><path d="m810 880 115 115"/></g>',
        f'<g {common}><path d="M330 500h280l70 80h240v330H330z"/><path d="m465 690 55 55 105-125M465 825h330"/><rect x="430" y="610" width="430" height="290" rx="20"/></g>',
        f'<g {common}><circle cx="585" cy="470" r="115"/><path d="M370 930c20-195 110-290 215-290s195 95 215 290"/><path d="M735 590h200v175H820l-75 68v-68h-10z"/><path d="M800 655h75"/></g>',
    ]
    return icons[(index - 1) % len(icons)]


def _svg(index: int, total: int) -> str:
    palette = [
        ("#101B2C", "#263E59", "#F2C66D"),
        ("#10242B", "#23564F", "#7FE0C1"),
        ("#211C31", "#4B3A65", "#E7A9FF"),
        ("#172334", "#244A68", "#8FD4FF"),
        ("#241E24", "#604344", "#FFC28B"),
    ]
    bg, glow, gold = palette[(index - 1) % len(palette)]
    icon = _icon(index, gold, "#F7F4ED")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="{glow}"/></linearGradient><radialGradient id="light"><stop stop-color="{gold}" stop-opacity=".18"/><stop offset="1" stop-color="{gold}" stop-opacity="0"/></radialGradient></defs>
<rect width="1080" height="1920" fill="url(#bg)"/><circle cx="820" cy="610" r="510" fill="url(#light)"/><path d="M0 1250 Q420 1040 1080 1230 V1920 H0Z" fill="#050B13" opacity=".24"/>
<g fill="none" stroke="white" stroke-opacity=".08" stroke-width="2"><path d="M80 390h920M80 440h920M80 490h920"/><circle cx="850" cy="500" r="260"/><circle cx="850" cy="500" r="330"/></g>
<text x="86" y="118" fill="white" font-family="DejaVu Sans" font-size="34" font-weight="700" letter-spacing="7">LEXFIS</text>
<text x="86" y="174" fill="{gold}" font-family="DejaVu Sans" font-size="22" font-weight="700" letter-spacing="2">ПРАВО · ПРАКТИКА · РЕШЕНИЯ</text>
<g transform="translate(0 60)">{icon}</g>
<rect x="84" y="1200" width="912" height="3" rx="2" fill="white" opacity=".18"/>
<text x="86" y="1270" fill="white" opacity=".78" font-family="DejaVu Sans" font-size="27">СЦЕНА {index:02} · ПРАКТИЧЕСКИЙ РАЗБОР</text>
<rect x="86" y="1792" width="908" height="5" rx="2" fill="white" opacity=".24"/><rect x="86" y="1792" width="{908 * index / total:.1f}" height="5" rx="2" fill="{gold}"/>
<text x="86" y="1850" fill="white" opacity=".72" font-family="DejaVu Sans" font-size="24">LEXFIS.RU</text><text x="994" y="1850" fill="white" opacity=".72" font-family="DejaVu Sans" font-size="24" text-anchor="end">{index:02}/{total:02}</text>
</svg>'''


def generate_scenes(title: str, voiceover: str, prompt: str, work: Path) -> list[Path]:
    chunks = _segments(voiceover)
    if not 4 <= len(chunks) <= 6:
        raise ValueError("Voiceover must support four to six scenes")
    result = []
    for i, _chunk in enumerate(chunks, 1):
        src, img = work / f"scene_{i:02}.svg", work / f"scene_{i:02}.png"
        src.write_text(_svg(i, len(chunks)), encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", "1080", "-h", "1920", "-o", str(img), str(src)], check=True, capture_output=True)
        result.append(img)
    return result
