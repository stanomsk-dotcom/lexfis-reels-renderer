# LexFis Reels Renderer

A vertical Reel renderer using open-source FFmpeg, Python, and local Russian espeak-ng speech synthesis when no audio file is supplied. It does not use a paid video-rendering API.

## Input

Create input.json with title, full voiceover, publication caption, four to six public image/video URLs in media[], and an optional audio_url. Run `python renderer/render.py --input input.json --output output/lexfis-reel.mp4`. If audio_url is empty, the full voiceover is synthesized locally in Russian.

Output: portrait 1080x1920, H.264/AAC, 30 fps, animated scenes, Russian subtitles, title opening, and LexFis end card. Narration is never cut off to fit a duration target.

## GitHub Actions

Choose Actions > Render LexFis Reel > Run workflow. The finished MP4 is saved as a run artifact for seven days. No paid GitHub feature is configured.

## Integration status

The workflow renders an MP4 artifact. Make dispatch and Telegram delivery still require configuration. Keep the existing FFmpeg Micro, Gemini, JSON2Video, and image-generation chain disabled. Automatic Instagram publishing is not included.
