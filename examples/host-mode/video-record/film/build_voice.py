"""Build voice.wav and plan.json for the film: one spoken passage per shot, with the shots timed to the voice.

Run: uv run --no-sync --with kokoro-onnx --with soundfile python build_voice.py <folder with kokoro-v1.0.onnx and voices-v1.0.bin>
Kokoro is Apache-2.0 and runs on the CPU; nothing is sent anywhere.

Why it is built this way. The first cut spoke seven short slogans, each synthesised alone, each placed at a shot
start, with the voice at 0.95 speed: about half the film was silence, and every line began high and fell the same
way. Now each shot gets a short passage of two or three connected sentences that says what the app does and why,
spoken in one pass at the model's natural speed, so sentences carry into each other. The shots are then cut to the
voice (lead-in before each passage, a breath after it) rather than the voice squeezed into fixed shots.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = Path(__file__).resolve().parent
VOICE = "af_heart"
SPEED = 1.0
RATE = 24000
SENTENCE_PAUSE = 0.38  # seconds of air after a full stop inside a passage
CLAUSE_PAUSE = 0.14  # after a comma, colon or dash
FIRST_LEAD = 0.95  # the film fades in from black first
LEAD = 0.3  # the voice starts as the new shot finishes dissolving in
TAIL = 0.4  # short breath after a passage, before the next shot starts to dissolve
LAST_TAIL = 1.9  # the end card holds, then the film fades out
GRID = 1 / 30  # shot lengths snap to whole frames

# One passage per shot, in shot order. Every claim is something the app prototype
# (../launch/video/app/index.html) shows: the stations list with favorites and distances, the next high water
# (7:48 AM, 9.4 ft), the day's curve with a marker for now, the high/low list, the Offline badge with the data
# pack (24 months on the phone), and the $4.99 one-time unlock with no account and no ads.
BEATS = [
    "At low tide, you only need one answer: when's the water coming back? And out here, there's no signal.",
    "Tidewatch keeps that answer on your phone. Your favorite spots sit at the top, each with how far away it is.",
    "You get the next high water straight away: seven forty-eight, nine point four feet. A curve shows the whole day with a marker for now, and every high and low is listed.",
    "Now lose your signal. Nothing changes. The tide data is already on your phone, two years of it.",
    "Unlocking every station is four ninety-nine. You pay once. There's no account to make, and no ads to skip.",
    "So you can head out, tie off, and know when the water's coming back.",
    "Tidewatch. Know the water.",
]


def main() -> None:
    models = Path(sys.argv[1])
    kokoro = Kokoro(str(models / "kokoro-v1.0.onnx"), str(models / "voices-v1.0.bin"))
    passages = []
    for text in BEATS:
        samples, rate = kokoro.create(
            text, voice=VOICE, speed=SPEED, lang="en-us",
            sentence_pause=SENTENCE_PAUSE, clause_pause=CLAUSE_PAUSE, continuous=True,
        )
        assert rate == RATE, rate
        passages.append(samples.astype(np.float32))

    plan = []
    shot_start = 0.0
    for i, samples in enumerate(passages):
        lead = FIRST_LEAD if i == 0 else LEAD
        tail = LAST_TAIL if i == len(passages) - 1 else TAIL
        seconds = round((lead + len(samples) / RATE + tail) / GRID) * GRID
        plan.append({"text": BEATS[i], "shot_start": round(shot_start, 4), "seconds": round(seconds, 4),
                     "voice_start": round(shot_start + lead, 4), "voice_seconds": round(len(samples) / RATE, 3)})
        shot_start += seconds
    total = round(shot_start, 4)

    track = np.zeros(int(total * RATE) + RATE, dtype=np.float32)
    for item, samples in zip(plan, passages):
        begin = int(item["voice_start"] * RATE)
        track[begin:begin + len(samples)] += samples
        print(f"{item['voice_start']:6.2f}s +{item['voice_seconds']:5.2f}s  shot {item['seconds']:5.2f}s  {item['text'][:70]}")
    track = track[: int(total * RATE)]
    peak = float(np.max(np.abs(track)))
    if peak > 0.95:
        track *= 0.95 / peak
    sf.write(str(HERE / "voice.wav"), track, RATE)
    (HERE / "plan.json").write_text(json.dumps({"total": total, "voice": VOICE, "speed": SPEED, "shots": plan}, indent=2) + "\n", encoding="utf-8")
    print(f"total {total:.2f}s")


if __name__ == "__main__":
    main()
