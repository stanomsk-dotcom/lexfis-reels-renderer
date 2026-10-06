# LexFis Reels Renderer

Free video rendering in GitHub Actions with open-source FFmpeg and local Russian speech synthesis. No paid video API, FFmpeg Micro, Gemini Video, JSON2Video, or Instagram publishing is used.

## What it renders

- Vertical MP4 at 1080×1920, H.264 video, AAC audio, 30 fps, optimized for Telegram and iPhone playback.
- The full Russian voiceover, locally synthesized with eSpeak NG when no audio file is supplied. The video is never shortened to fit a target length; the closing card follows the final spoken word.
- Four to six varied, topic-colored visual scenes, slow zoom/pan, and soft transitions when no media URLs are supplied. Each short direction from the visual prompt selects an appropriate scene illustration. These are motion graphics; supply four to six public image/video URLs in media[] for documentary footage.
- A large Russian opening title for the first 2.7 seconds, readable Russian captions timed over the narration, and a closing card: LexFis — юридическая помощь · lexfis.ru.
- Automated checks for audible audio, H.264/AAC streams, frame size, frame rate, duration, and file size.

## Inputs

input.json contains title, the entire voiceover, a publication caption, optional visual_prompt, an optional array of four to six public URLs in media[], and optional audio_url.

Run locally in an environment with FFmpeg, eSpeak NG, DejaVu fonts, and librsvg:

    python renderer/render_local.py --input input.json --output output/lexfis-reel.mp4

If audio_url is empty, the complete Russian narration is synthesized locally.

## GitHub Actions and Telegram

Open Actions → Render LexFis Reel → Run workflow and enter the Russian title, full voiceover, publication description, and (optionally) visual prompt, media URLs, and audio URL. The action renders the MP4, verifies its audio/video streams, and sends the finished MP4 plus title and publication description to the configured Make webhook for Telegram delivery.

The daily Make scenario invokes the same workflow_dispatch endpoint. Keep it disabled during testing and turn it on only after the test Reel arrives in Telegram and its picture and sound have been reviewed.

## Cost and publishing

The repository uses public GitHub Actions and open-source packages. It does not configure a paid GitHub feature, video-rendering subscription, or automatic Instagram/TikTok publishing. The former paid rendering routes are not in this workflow.
