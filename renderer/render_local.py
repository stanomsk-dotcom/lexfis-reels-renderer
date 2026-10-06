#!/usr/bin/env python3
"""Render a complete vertical LexFis Reel using open-source FFmpeg and Russian TTS."""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from render import download, make_subtitles, run
from scenes import generate_scenes

W, H, FPS = 1080, 1920, 30


def probe(path: Path) -> dict:
    raw = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    return json.loads(raw)


def verify_audible(path: Path) -> None:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"], text=True, capture_output=True, check=True)
    match = re.search(r"mean_volume: *(-?inf|[-0-9.]+) dB", result.stderr)
    if not match or match.group(1) == "-inf" or float(match.group(1)) < -45:
        raise ValueError("Rendered audio is silent or too quiet")


def verify_mp4(path: Path, narration_seconds: float) -> dict:
    info = probe(path)
    streams = info.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise ValueError("MP4 must contain both video and audio streams")
    if (video.get("codec_name"), video.get("width"), video.get("height")) != ("h264", W, H):
        raise ValueError("MP4 video must be H.264 at 1080x1920")
    if audio.get("codec_name") != "aac":
        raise ValueError("MP4 audio must be AAC")
    rate = video.get("r_frame_rate", "0/1").split("/")
    fps = float(rate[0]) / float(rate[1])
    if not 25 <= fps <= 30:
        raise ValueError("MP4 frame rate must be between 25 and 30 fps")
    duration = float(info.get("format", {}).get("duration", 0))
    if duration < narration_seconds + 1.4:
        raise ValueError("MP4 is shorter than the complete narration and closing pause")
    return {"duration_with_end_card": round(duration, 2), "video_codec": "h264", "audio_codec": "aac", "resolution": "1080x1920", "fps": round(fps, 2)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("input.json"))
    parser.add_argument("--output", type=Path, default=Path("output/lexfis-reel.mp4"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    title = str(data.get("title", "")).strip()
    voiceover = str(data.get("voiceover", "")).strip()
    if not title or not voiceover:
        raise ValueError("title and the complete Russian voiceover are required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    work = args.output.parent / "work"
    work.mkdir(parents=True, exist_ok=True)
    media = data.get("media") or []
    if media:
        if not 4 <= len(media) <= 6:
            raise ValueError("media must contain four to six image or video URLs")
        scenes = [download(item["url"] if isinstance(item, dict) else str(item), work / f"source_{i:02}.bin") for i, item in enumerate(media)]
    else:
        scenes = generate_scenes(title, voiceover, data.get("visual_prompt", ""), work)
    audio_url = str(data.get("audio_url", "")).strip()
    if audio_url:
        audio = download(audio_url, work / "narration.bin")
    else:
        audio = work / "narration.wav"
        text_file = work / "narration.txt"
        text_file.write_text(voiceover, encoding="utf-8")
        run(["espeak-ng", "-v", "ru", "-s", "128", "-p", "48", "-a", "180", "-w", str(audio), "-f", str(text_file)])
    seconds = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio)]))
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("narration duration is invalid")
    subtitles = work / "captions.srt"
    make_subtitles(voiceover, seconds, subtitles)
    title_file = work / "title.txt"
    words, lines, line = title.upper().split(), [], ""
    for word in words:
        if line and len(line) + len(word) + 1 > 22:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        lines.append(line)
    if not lines:
        raise ValueError("Reel title is empty")
    title_file.write_text("\n".join(lines), encoding="utf-8")
    title_size = 64 if len(lines) <= 2 else 54 if len(lines) == 3 else 46 if len(lines) == 4 else 40
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    scene_seconds = seconds / len(scenes) + 0.45
    overlap = 0.45
    outro_seconds = 1.8
    cmd, filters, labels = ["ffmpeg", "-hide_banner", "-y"], [], []
    for src in scenes:
        cmd += ["-stream_loop", "-1", "-i", str(src)]
    audio_index = len(scenes)
    cmd += ["-i", str(audio)]
    for i in range(len(scenes)):
        x = "iw/2-(iw/zoom/2)+sin(on/65)*36" if i % 2 == 0 else "iw/2-(iw/zoom/2)-sin(on/65)*36"
        y = "ih/2-(ih/zoom/2)+cos(on/80)*28"
        filters.append(f"[{i}:v]scale=1200:2134:force_original_aspect_ratio=increase,crop=1200:2134,fps={FPS},trim=duration={scene_seconds:.3f},setpts=PTS-STARTPTS,zoompan=z='min(zoom+0.0005,1.12)':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]")
        labels.append(f"[v{i}]")
    current, elapsed = labels[0], scene_seconds
    for i in range(1, len(labels)):
        next_label = f"[x{i}]"
        filters.append(f"{current}{labels[i]}xfade=transition=fade:duration={overlap:.3f}:offset={elapsed-overlap:.3f}{next_label}")
        current, elapsed = next_label, elapsed + scene_seconds - overlap
    filters.append(f"{current}trim=duration={seconds:.3f},setpts=PTS-STARTPTS[body]")
    srt_path = str(subtitles).replace(":", "\\:").replace("'", "\\'")
    title_path = str(title_file).replace(":", "\\:").replace("'", "\\'")
    style = "FontName=DejaVu Sans,FontSize=46,PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,BackColour=&H88000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginL=95,MarginR=95,MarginV=500"
    title_filter = f"drawtext=fontfile='{font}':textfile='{title_path}':fontcolor=white:fontsize={title_size}:line_spacing=8:x=(w-text_w)/2:y=h*0.20:box=1:boxcolor=0x091723@0.78:boxborderw=24:enable='lt(t,2.7)'"
    filters.append(f"[body]{title_filter},subtitles=filename='{srt_path}':force_style='{style}'[captioned]")
    end_card = f"drawtext=fontfile='{font}':text='LexFis — юридическая помощь':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h/2-35:box=1:boxcolor=0x101820@0.78:boxborderw=28,drawtext=fontfile='{font}':text='lexfis.ru':fontcolor=0xF3C969:fontsize=54:x=(w-text_w)/2:y=h/2+70"
    filters += [f"color=c=0x17212B:s={W}x{H}:r={FPS}:d={outro_seconds}[outrobase]", f"[outrobase]{end_card}[outro]", "[captioned][outro]concat=n=2:v=1:a=0,format=yuv420p[vout]", f"[{audio_index}:a]aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11,apad,atrim=duration={seconds+outro_seconds:.3f},asetpts=PTS-STARTPTS[aout]"]
    cmd += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", "-t", f"{seconds+outro_seconds:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-b:v", "800k", "-maxrate", "1000k", "-bufsize", "2000k", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(args.output)]
    run(cmd)
    verify_audible(args.output)
    metadata = verify_mp4(args.output, seconds)
    if args.output.stat().st_size > 4_800_000:
        raise ValueError("MP4 exceeds the 4.8 MB Make webhook limit")
    metadata.update({"narration_seconds": round(seconds, 2), "scene_count": len(scenes), "audio": "audible", "bytes": args.output.stat().st_size})
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"render failed: {exc}", file=sys.stderr)
        sys.exit(1)
