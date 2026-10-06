#!/usr/bin/env python3
"""Create topic-aware, caption-safe motion-graphic plates for vertical Reels."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path


def _segments(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    if len(parts) < 4:
        words = text.split()
        size = max(1, (len(words) + 4) // 5)
        parts = [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
    while len(parts) < 4:
        parts.append(parts[-1] if parts else text)
    return parts[:6]


def _theme(title: str, prompt: str) -> tuple[str, str, str, str]:
    text = (title + " " + prompt).lower()
    themes = [
        (("налог", "вычет", "ндфл", "декларац", "штраф"), ("#0A2638", "#14605F", "#F2C56B", "НАЛОГИ")),
        (("квартир", "недвиж", "аренд", "ипотек", "собствен"), ("#132A45", "#365A81", "#F0BE72", "НЕДВИЖИМОСТЬ")),
        (("труд", "увольн", "работ", "зарплат", "отпуск"), ("#142B37", "#336C68", "#F1C478", "ТРУДОВОЕ ПРАВО")),
        (("долг", "кредит", "банкрот", "взыск", "пристав"), ("#26243A", "#554B73", "#E8B578", "ДОЛГИ И КРЕДИТЫ")),
        (("договор", "подряд", "постав", "контракт"), ("#14293F", "#345C76", "#E7C27B", "ДОГОВОРЫ")),
        (("семейн", "развод", "алим", "наслед"), ("#26303B", "#4D6576", "#E8BD7A", "СЕМЬЯ И НАСЛЕДСТВО")),
    ]
    for words, palette in themes:
        if any(word in text for word in words):
            return palette
    return ("#12283B", "#31566B", "#EFC474", "ЮРИДИЧЕСКАЯ ПРАКТИКА")


def _visual_directions(prompt: str) -> list[str]:
    return [part.strip().lower() for part in re.split(r"[;\n]+", prompt) if part.strip()]


def _art_kind(text: str, fallback: int) -> int:
    if any(word in text for word in ("телефон", "экран", "сайт", "сообщен", "звон", "онлайн")):
        return 1
    if any(word in text for word in ("папк", "архив", "хран", "собран", "пачк")):
        return 3
    if any(word in text for word in ("поиск", "провер", "свер", "найти", "иск")):
        return 2
    if any(word in text for word in ("юрист", "консультац", "клиент", "встреч", "бесед")):
        return 4
    if any(word in text for word in ("срок", "календар", "этап", "график", "результат", "шаг")):
        return 5
    if any(word in text for word in ("документ", "договор", "бумаг", "справк", "чек", "список")):
        return 0
    return fallback % 6


def _art(kind: int, gold: str) -> str:
    stroke = f'fill="none" stroke="{gold}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"'
    icons = [
        f'<g {stroke}><path d="M365 330h270l120 120v590H365zM635 330v130h120M445 570h225M445 660h300M445 750h245"/><path d="m475 880 65 65 140-165"/></g>',
        f'<g {stroke}><rect x="410" y="320" width="330" height="610" rx="50"/><path d="M530 390h90M540 850h70"/><rect x="475" y="485" width="200" height="260" rx="20"/><path d="m510 610 48 48 90-110"/></g>',
        f'<g {stroke}><path d="M350 390h390v470H350zM410 510h270M410 600h180"/><circle cx="665" cy="760" r="140"/><path d="m765 860 125 125"/></g>',
        f'<g {stroke}><path d="M310 540h300l70 80h250v340H310z"/><path d="M410 700h170M410 790h290"/><path d="m700 720 48 48 90-110"/></g>',
        f'<g {stroke}><circle cx="535" cy="475" r="112"/><path d="M330 950c22-190 100-285 205-285s185 95 205 285"/><path d="M730 590h220v175H825l-80 72v-72h-15zM810 655h70"/></g>',
        f'<g {stroke}><path d="M350 920V420h470v500zM440 800l120-160 95 110 95-210"/><circle cx="810" cy="520" r="92"/></g>',
    ]
    return icons[kind]


def _svg(index: int, total: int, theme: tuple[str, str, str, str], kind: int) -> str:
    bg, glow, gold, _label = theme
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="{glow}"/></linearGradient><radialGradient id="orb"><stop stop-color="{gold}" stop-opacity=".3"/><stop offset="1" stop-color="{gold}" stop-opacity="0"/></radialGradient></defs>
<rect width="1080" height="1920" fill="url(#bg)"/><circle cx="840" cy="700" r="520" fill="url(#orb)"/><circle cx="840" cy="700" r="330" fill="none" stroke="white" stroke-opacity=".06" stroke-width="2"/><circle cx="840" cy="700" r="420" fill="none" stroke="white" stroke-opacity=".045" stroke-width="2"/><path d="M0 1250 Q480 1060 1080 1260 V1920 H0Z" fill="#050B13" opacity=".23"/>
<text x="82" y="118" fill="white" font-family="DejaVu Sans" font-size="34" font-weight="700" letter-spacing="7">LEXFIS</text><text x="84" y="174" fill="{gold}" font-family="DejaVu Sans" font-size="22" font-weight="700" letter-spacing="2">ПРАВО · ПРАКТИКА · РЕШЕНИЯ</text>
<g transform="translate(0 330)">{_art(kind, gold)}</g>
<rect x="86" y="1792" width="908" height="5" rx="2" fill="white" opacity=".22"/><rect x="86" y="1792" width="{908 * index / total:.1f}" height="5" rx="2" fill="{gold}"/><text x="86" y="1850" fill="white" opacity=".72" font-family="DejaVu Sans" font-size="24">LEXFIS.RU</text><text x="994" y="1850" fill="white" opacity=".72" font-family="DejaVu Sans" font-size="24" text-anchor="end">{index:02}/{total:02}</text>
</svg>'''


def generate_scenes(title: str, voiceover: str, prompt: str, work: Path) -> list[Path]:
    chunks = _segments(voiceover)
    directions = _visual_directions(prompt)
    theme = _theme(title, prompt)
    result = []
    for i, chunk in enumerate(chunks, 1):
        direction = directions[i - 1] if i <= len(directions) else chunk
        kind = _art_kind(direction + " " + chunk, i - 1)
        src, img = work / f"scene_{i:02}.svg", work / f"scene_{i:02}.png"
        src.write_text(_svg(i, len(chunks), theme, kind), encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", "1080", "-h", "1920", "-o", str(img), str(src)], check=True, capture_output=True)
        result.append(img)
    return result
