import { mkdirSync, writeFileSync } from "node:fs";

const rate = 48000;
const seconds = 42;
const count = rate * seconds;
const hits = [
  [0.4, 196, 0.1],
  [11.3, 330, 0.14],
  [25.3, 392, 0.14],
];

const samples = new Int16Array(count);
for (let i = 0; i < count; i++) {
  const t = i / rate;
  let sample = 0.022 * Math.sin(2 * Math.PI * 46 * t) + 0.01 * Math.sin(2 * Math.PI * 92 * t);
  for (const [start, freq, amp] of hits) {
    const local = t - start;
    if (local >= 0 && local < 0.4) {
      const env = local < 0.012 ? local / 0.012 : 1 - (local - 0.012) / 0.388;
      sample += amp * env * Math.sin(2 * Math.PI * freq * local);
    }
  }
  sample = Math.max(-1, Math.min(1, sample));
  samples[i] = Math.round(sample * 24000);
}

const header = Buffer.alloc(44);
header.write("RIFF", 0);
header.writeUInt32LE(36 + samples.byteLength, 4);
header.write("WAVE", 8);
header.write("fmt ", 12);
header.writeUInt32LE(16, 16);
header.writeUInt16LE(1, 20);
header.writeUInt16LE(1, 22);
header.writeUInt32LE(rate, 24);
header.writeUInt32LE(rate * 2, 28);
header.writeUInt16LE(2, 32);
header.writeUInt16LE(16, 34);
header.write("data", 36);
header.writeUInt32LE(samples.byteLength, 40);

const wav = Buffer.concat([header, Buffer.from(samples.buffer)]);
mkdirSync(new URL("./public/", import.meta.url), { recursive: true });
writeFileSync(new URL("./public/bed.wav", import.meta.url), wav);
writeFileSync(new URL("./bed.wav", import.meta.url), wav);
console.log(`wrote bed.wav (${seconds}s)`);
