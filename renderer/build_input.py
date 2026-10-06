#!/usr/bin/env python3
"""Build renderer input from GitHub Actions inputs."""
import json
import os
from pathlib import Path

media = json.loads(os.environ.get("MEDIA_JSON", "[]"))
if not isinstance(media, list):
    raise SystemExit("media_json must be a JSON array")
payload = {
    "title": os.environ["TITLE"],
    "voiceover": os.environ["VOICEOVER"],
    "caption": os.environ["CAPTION"],
    "media": media,
    "audio_url": os.environ.get("AUDIO_URL", ""),
}
Path("input.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
