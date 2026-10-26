# Host-mode video: Tidewatch launch film

A finished 30-second film, [final.mp4](final.mp4) (1280x720, H.264 plus AAC, about 4 MB), made with no API key and no paid service. Tidewatch is an invented app; nothing here is a real product.

It runs seven shots: a generated low-tide shore, the app splash, the tide chart, the offline badge, the $4.99 price sheet, a generated shot of a skipper tying off a dinghy as the water floods back, and an end card. A woman's synthetic voice reads the lines over a soft pad, bass and shaker loop. Captions are burned in.

## The premium cut: `final-premium.mp4`

A 48.8 s, 1920x1080 rebuild by [build_premium.py](build_premium.py) from the same clips and app frames. It has a longer script ([lines.txt](lines.txt)) in which each beat says what the app does and why, timed to the app footage; a voice built in connected passages (the old film read seven separate slogans with long gaps); dissolves, slow camera drift, a graded look and captions beside the phone. Every claim in the script is something the prototype shows. Order: `build_voice.py` (writes `voice.wav` and `plan.json`), `build_music.py`, the two `ffmpeg` shrink commands, then `uv run --no-sync python build_premium.py`. `final.mp4` below is the older 30 s film and is unchanged. Boss watched and listened to the premium cut and accepted it as is. Version 4 of [../video-record](../video-record) records it, scored 7/10 by Codex, which did not make it, from 16 frames, the script and loudness figures (it cannot hear sound). That record holds the shot clips, audio and scripts, not `final-premium.mp4` itself, to keep the repo small.

## Who made each asset

| Asset | Made by |
| --- | --- |
| `script.json`, `lines.txt`, shot plan | Claude Code (the host agent) |
| Shore and dinghy clips | Gemini ("Create video") on the owner's free allowance, one prompt each. They are the two clips from the launch promo, kept in [../launch/video/gen](../launch/video/gen) with their prompts in `PROMPTS.md`; this film uses other parts of them |
| App screen footage | The HTML prototype in [../launch/video/app](../launch/video/app), recorded frame by frame by `capture_app.py` with the installed Chrome; this film uses other stretches of it |
| `shot-01.mp4` to `shot-07.mp4` | [build_shots.py](build_shots.py): FFmpeg cuts the clips, softens the backdrop behind the phone, places the phone, holds the last app frame where the voice runs on |
| `voice.m4a` | [build_voice.py](build_voice.py): Kokoro (Apache-2.0, CPU, voice `af_heart`), each line placed at its shot's start |
| `music.m4a` | [build_music.py](build_music.py): numpy only (92 BPM, Am to F to C to G pad, plucked bass, shaker, bells) |
| `final.mp4`, `captions.srt`, `studio.json` | `proofhouse render video` (FFmpeg): join, mix, burn captions |

No hosted service was called while making this film. The Gemini clips were made once, earlier, for the promo.

## Rebuild

The film needs the promo's clips and app frames, so build those first (see [../launch/README.md](../launch/README.md): `capture_app.py` writes `launch/video/app/frames/`, which is git-ignored).

```bash
uv run --no-sync python build_shots.py
uv run --no-sync --with numpy python build_music.py
uv run --no-sync --with kokoro-onnx --with soundfile python build_voice.py <folder with the Kokoro model files>
# shrink the audio as the committed files were
ffmpeg -i voice.wav -c:a aac -b:a 128k voice.m4a && ffmpeg -i music.wav -c:a aac -b:a 128k music.m4a
uv run --no-sync proofhouse render video . --formats 16x9 --size-scale 0.6667
mv video-16x9.mp4 final.mp4
```

The record of the four rounds is in [../video-record](../video-record) (rounds 1 and 2 are the earlier slide film, round 3 the 30 s film, round 4 the 48.8 s film). `proofhouse record` has no `video` kind, so the film is recorded as a two-part launch (film plus voice-over text). Rounds 1 to 3 hold the script, audio, scripts and MP4, not the seven shot clips; round 4 holds the shot clips, not the finished MP4.

## What the checks measured

- Render checks (from `proofhouse render video`): length 30.0 s of 30 s, frame size 1280x720, sound present, 7 captions match the script.
- The two-part launch check passes (video structure, voice-over copy, shared name, three facts, avoid-words, parts differ).
- FFmpeg: one video stream, one audio stream, mean volume -22.8 dB, peak -4.7 dB, and every shot window sits between -21.7 and -23.8 dB (so the voice is not missing from any shot).
- Frames pulled at eight points were looked at for caption overlap, phone position and whether the app screen shows what the script says.

## What the checks do not prove

- Nobody has listened to it. The measurements show sound is present and not clipping, not that the Kokoro voice is pleasant or the mix balanced.
- The footage is thin: two generated clips of 10 seconds at 720p, no retakes, shared with the promo, and the app is an HTML prototype, not a real build. The three app shots sit over a softened copy of the shore, with empty space on the left.
- Generated footage can contain small physical errors; a person should look at both clips before a real release.
- The agent that wrote the film also scored it (8). Rounds 1 and 2 in the record are the earlier slide film.
