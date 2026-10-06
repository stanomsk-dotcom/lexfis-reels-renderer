#!/usr/bin/env python3
"""Render a vertical LexFis Reel with FFmpeg and local Russian speech."""
import json
import math
import subprocess
import sys
from pathlib import Path
from render import download, make_subtitles, run
from scenes import generate_scenes

W, H, FPS = 1080, 1920, 30

def main():
    data = json.loads(Path("input.json").read_text(encoding="utf-8"))
    title, voiceover = data["title"].strip(), data["voiceover"].strip()
    if not title or not voiceover:
        raise ValueError("title and full voiceover are required")
    out = Path("output/lexfis-reel.mp4")
    work = out.parent / "work"
    work.mkdir(parents=True, exist_ok=True)
    media = data.get("media") or []
    if media:
        if not 4 <= len(media) <= 6:
            raise ValueError("media must contain 4-6 URLs")
        scenes = [download(item["url"] if isinstance(item, dict) else item, work / f"source_{i:02}.bin") for i,item in enumerate(media)]
    else:
        scenes = generate_scenes(title, voiceover, data.get("visual_prompt", ""), work)
    audio_url = data.get("audio_url", "").strip()
    if audio_url:
        audio = download(audio_url, work / "narration.bin")
    else:
        audio = work / "narration.wav"
        run(["espeak-ng", "-v", "ru", "-s", "150", "-p", "48", "-w", str(audio), voiceover])
    seconds = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio)]))
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("narration duration is invalid")
    make_subtitles(voiceover, seconds, work / "captions.srt")
    count, scene_len, overlap = len(scenes), seconds / len(scenes) + 0.35, 0.35
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for src in scenes:
        cmd += ["-stream_loop", "-1", "-i", str(src)]
    cmd += ["-i", str(audio)]
    filters, labels = [], []
    frames = math.ceil(scene_len * FPS)
    for i in range(count):
        filters.append(f"[{i}:v]scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,fps={FPS},trim=duration={scene_len:.3f},setpts=PTS-STARTPTS,zoompan=z='min(zoom+0.0004,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]")
        labels.append(f"[v{i}]")
    current, elapsed = labels[0], scene_len
    for i in range(1, count):
        new = f"[x{i}]"
        filters.append(f"{current}{labels[i]}xfade=transition=fade:duration={overlap}:offset={elapsed-overlap:.3f}{new}")
        current, elapsed = new, elapsed + scene_len - overlap
    filters.append(f"{current}trim=duration={seconds:.3f},setpts=PTS-STARTPTS[body]")
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    title_file = work / "title.txt"
    title_file.write_text(title.upper(), encoding="utf-8")
    title_path = str(title_file).replace(":", chr(92) + ":")
    srt_path = str(work / "captions.srt").replace(":", chr(92) + ":")
    filters.append(f"[body]drawtext=fontfile='{font}':textfile='{title_path}':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=h*0.34:box=1:boxcolor=0x101820@0.82:boxborderw=32:enable='lt(t,2.7)',subtitles=filename='{srt_path}':force_style='FontName=DejaVu Sans,FontSize=48,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BackColour=&H88000000,BorderStyle=3,Alignment=2,MarginL=95,MarginR=95,MarginV=380'[captioned]")
    filters.append(f"color=c=0x17212B:s={W}x{H}:r={FPS}:d=2[outrobase]")
    filters.append(f"[outrobase]drawtext=fontfile='{font}':text='LexFis — юридическая помощь':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h/2-35,drawtext=fontfile='{font}':text='lexfis.ru':fontcolor=0xF3C969:fontsize=54:x=(w-text_w)/2:y=h/2+55[outro]")
    filters.append("[captioned][outro]concat=n=2:v=1:a=0,format=yuv420p[vout]")
    filters.append(f"[{count}:a]aresample=48000,apad,atrim=duration={seconds+2:.3f},asetpts=PTS-STARTPTS[aout]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", "-t", f"{seconds+2:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-b:v", "700k", "-maxrate", "800k", "-bufsize", "1600k", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]
    run(cmd)
    if out.stat().st_size > 4_800_000:
        raise ValueError("MP4 exceeds the 4.8 MB Make webhook limit")
    print(json.dumps({"duration_with_end_card": round(seconds+2, 2), "bytes": out.stat().st_size}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"render failed: {exc}", file=sys.stderr)
        sys.exit(1)
