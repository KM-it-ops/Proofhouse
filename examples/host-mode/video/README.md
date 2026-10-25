# Host-mode video: Tidewatch launch film

A finished 30-second film, [final.mp4](final.mp4) (1280x720, H.264 plus AAC, about 2 MB), made with no API key and no paid service. Tidewatch is an invented app; nothing here is a real product.

It runs seven scenes: the wordmark, a tide chart, "no signal, no problem" on a phone, the $4.99 one-time price, "no accounts", "no ads", and an end card. A man's synthetic voice reads the lines over a soft pad, bass and shaker loop. Captions are burned in.

## Who made each asset

| Asset | Made by |
| --- | --- |
| `script.json`, `lines.txt`, scene design | Claude Code (the host agent) |
| `shot-01.png` to `shot-07.png` | Claude Code wrote [build_assets.py](build_assets.py); Pillow drew them with Windows system fonts |
| `voice.m4a` | Windows built-in speech (System.Speech, voice "Microsoft David Desktop") via [make_voice.ps1](make_voice.ps1), timed to the scenes by FFmpeg |
| `music.m4a` | Synthesised by `build_assets.py` with numpy (92 BPM, Am to F to C to G pad, bass, shaker) |
| `final.mp4`, `captions.srt` | `proofhouse render video` (FFmpeg): cut, join, mix, burn captions |

No hosted model or media service was called. The only download was the Pillow and numpy packages.

## Rebuild

```bash
powershell -NoProfile -File make_voice.ps1
uv run --no-sync --with pillow --with numpy python build_assets.py
# the build writes voice.wav and music.wav; shrink them as the committed files were
ffmpeg -i voice.wav -c:a aac -b:a 128k voice.m4a && ffmpeg -i music.wav -c:a aac -b:a 128k music.m4a
uv run --no-sync proofhouse render video . --formats 16x9 --size-scale 0.6667
mv video-16x9.mp4 final.mp4
```

The record of the two rounds is in [../video-record](../video-record). `proofhouse record` has no `video` kind, so the film is recorded as a two-part launch (film plus voice-over text). That record holds the pictures, script and audio, not the MP4.

## What the checks measured

- Render checks (from `proofhouse render video`): length 30.0 s of 30 s, frame size 1280x720, sound present, 7 captions match the script.
- FFmpeg: one video stream, one stereo audio stream, mean volume about -21 dB, peak -0.7 dB, and the loudness is similar in every scene window (so speech is not missing from any scene).
- Frames pulled at eight points were looked at for text overlap and layout.

## What the checks do not prove

- Nobody has listened to it. The measurements show sound is present and not clipping, not that the voice is pleasant or the mix balanced. The voice is a plain text-to-speech voice and sounds like one.
- The pictures are still images with no motion between scenes. It is a slide film with a voice, not footage.
- The agent that wrote the film also scored it. The scores in the record are the agent's own.
- Round 1 and round 2 in the record share the same audio files; only pictures and captions differ between them.
