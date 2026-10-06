#!/usr/bin/env python3
"""Render a vertical LexFis Reel using local FFmpeg and espeak-ng only."""
from __future__ import annotations
import argparse
import ipaddress
import json
import math
import mimetypes
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

W, H, FPS = 1080, 1920, 30

def run(args: list[str]) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()

def download(url: str, path: Path) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use an HTTP(S) media URL without embedded credentials")
    try:
        addresses = {ipaddress.ip_address(x[4][0]) for x in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))}
        if not addresses or any(not x.is_global for x in addresses):
            raise ValueError("Media host must resolve to public internet addresses")
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve media host: {parsed.hostname}") from exc
    req = urllib.request.Request(url, headers={"User-Agent": "LexFis-Reels-Renderer/1.0"})
    with urllib.request.urlopen(req, timeout=90) as response, path.open("wb") as out:
        content_type = response.headers.get_content_type()
        size = 0
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > 80 * 1024 * 1024:
                raise ValueError("Media file exceeds the 80 MiB limit")
            out.write(chunk)
    suffix = Path(parsed.path).suffix.lower()
    valid = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".m4v", ".webm"}
    if suffix not in valid:
        suffix = mimetypes.guess_extension(content_type) or ".mp4"
        if suffix == ".jpe": suffix = ".jpg"
    renamed = path.with_suffix(suffix)
    path.rename(renamed)
    if renamed.stat().st_size == 0:
        raise ValueError("Downloaded empty media file")
    return renamed

def srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def wrap_words(text: str, limit: int = 25) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > limit and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current: lines.append(current)
    return lines

def make_subtitles(voiceover: str, audio_seconds: float, output: Path) -> None:
    words = voiceover.split()
    groups, group = [], []
    for word in words:
        if group and len(" ".join(group + [word])) > 27:
            groups.append(group)
            group = []
        group.append(word)
    if group: groups.append(group)
    weights = [max(1, len(" ".join(g))) for g in groups]
    total = sum(weights) or 1
    lines, cursor = [], 0.0
    for i, (group, weight) in enumerate(zip(groups, weights), 1):
        start = audio_seconds * cursor / total
        cursor += weight
        end = audio_seconds * cursor / total
        text = "\\N".join(wrap_words(" ".join(group)))
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.extend([str(i), f"{srt_time(start)} --> {srt_time(max(start + 0.3, end))}", text, ""])
    output.write_text("\n".join(lines), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    title, voiceover, caption = (str(data.get(k, "")).strip() for k in ("title", "voiceover", "caption"))
    media = data.get("media", [])
    if not title or not voiceover or not caption: raise ValueError("title, voiceover, and caption are required")
    if not isinstance(media, list) or not 4 <= len(media) <= 6: raise ValueError("Provide 4–6 image/video URLs in media[]")
    work = args.output.parent / "work"
    work.mkdir(parents=True, exist_ok=True)
    inputs = [download(str(item.get("url") if isinstance(item, dict) else item), work / f"scene_{i:02}.bin") for i, item in enumerate(media)]
    audio_url = str(data.get("audio_url", "")).strip()
    if audio_url:
        audio_path = download(audio_url, work / "voice_input")
    else:
        audio_path = work / "voice.wav"
        voice_text = work / "voice.txt"
        voice_text.write_text(voiceover, encoding="utf-8")
        run(["espeak-ng", "-v", "ru", "-s", "150", "-p", "48", "-w", str(audio_path), "-f", str(voice_text)])
    audio_seconds = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]))
    if not math.isfinite(audio_seconds) or audio_seconds <= 0: raise ValueError("Could not determine narration duration")
    content_seconds, outro_seconds = max(23.0, audio_seconds), 2.0
    scene_seconds = content_seconds / len(inputs)
    subtitles = work / "captions.srt"
    make_subtitles(voiceover, audio_seconds, subtitles)
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not Path(font).exists(): font = "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    cmd, filters, labels = ["ffmpeg", "-hide_banner", "-y"], [], []
    for path in inputs: cmd += ["-stream_loop", "-1", "-i", str(path)]
    audio_idx = len(inputs)
    cmd += ["-i", str(audio_path)]
    for i in range(len(inputs)):
        filters.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},trim=duration={scene_seconds:.3f},setpts=PTS-STARTPTS,zoompan=z='min(zoom+0.00045,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]")
        labels.append(f"[v{i}]")
    current, elapsed = labels[0], scene_seconds
    for i in range(1, len(labels)):
        overlap, target = min(0.35, scene_seconds / 4), f"[xf{i}]"
        filters.append(f"{current}{labels[i]}xfade=transition=fade:duration={overlap:.3f}:offset={elapsed-overlap:.3f}{target}")
        current, elapsed = target, elapsed + scene_seconds - overlap
    filters.append(f"{current}trim=duration={content_seconds:.3f},setpts=PTS-STARTPTS[montage]")
    title_file = work / "title.txt"
    title_file.write_text("\n".join(wrap_words(title.upper(), 22)), encoding="utf-8")
    esc = lambda p: str(p).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    title_filter = f"drawtext=fontfile='{font}':textfile='{esc(title_file)}':fontcolor=white:fontsize=72:line_spacing=16:x=(w-text_w)/2:y=h*0.34:box=1:boxcolor=0x101820@0.78:boxborderw=32:enable='lt(t,2.7)'"
    style = "FontName=DejaVu Sans,FontSize=48,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BackColour=&H88000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginL=95,MarginR=95,MarginV=380"
    filters.append(f"[montage]{title_filter},subtitles=filename='{esc(subtitles)}':force_style='{style}'[captioned]")
    outro = f"drawtext=fontfile='{font}':text='LexFis — юридическая помощь':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h/2-35:box=1:boxcolor=0x101820@0.76:boxborderw=26,drawtext=fontfile='{font}':text='lexfis.ru':fontcolor=0xF3C969:fontsize=54:x=(w-text_w)/2:y=h/2+55"
    filters += [f"color=c=0x17212B:s={W}x{H}:r={FPS}:d={outro_seconds}[base]", f"[base]{outro}[endcard]", "[captioned][endcard]concat=n=2:v=1:a=0,format=yuv420p[vout]", f"[{audio_idx}:a]aresample=48000,apad,atrim=duration={content_seconds+outro_seconds:.3f},asetpts=PTS-STARTPTS[aout]"]
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", "-t", f"{content_seconds+outro_seconds:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(args.output)]
    run(cmd)
    print(json.dumps({"output": str(args.output), "duration": round(audio_seconds+outro_seconds, 2), "caption": caption}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except (ValueError, subprocess.CalledProcessError, OSError) as exc:
        print(f"render failed: {exc}", file=sys.stderr)
        sys.exit(1)
