// Synthesize the test songs as real audio, then score them with World's OWN
// front end (WorldCore.features) and Korva-style organ (WorldCore.Organ), loaded
// unmodified from vendor/World_index.html. Output: results/scores.json
//
// Each song is a short drum-machine track. Songs come in pairs that differ in
// one property only, so the tuning test can say WHAT a world learned:
//   tempo pair:    march80   vs march116  (same parts, same patterns, different tempo)
//   register pair: low96     vs high96    (same tempo, low instruments vs high ones)
//   pattern pair:  straight100 vs broken100 (same tempo and instruments, different rhythm)
//   weather pair:  World's own generated weather, variant 0 vs 1
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, 'vendor/World_index.html'), 'utf8');
const ctx = {}; vm.createContext(ctx);
vm.runInContext(html.match(/<script id="world-core">([\s\S]*?)<\/script>/)[1] + ';this.WorldCore=WorldCore;', ctx);
const W = ctx.WorldCore;

const RATE = 44100, SECONDS = Number(process.env.SONG_SECONDS || 120);
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// --- instruments: each adds one hit into the buffer at sample index i0 ---
const inst = {
  kick(buf, i0, v) { let ph = 0; for (let i = 0; i < RATE * .3 && i0 + i < buf.length; i++) { const t = i / RATE, f = 50 + 70 * Math.exp(-t * 30); ph += 2 * Math.PI * f / RATE; buf[i0 + i] += v * .9 * Math.sin(ph) * Math.exp(-t * 9); } },
  bass(buf, i0, v, n = 0) { const f = 82.4 * Math.pow(2, n / 12); for (let i = 0; i < RATE * .35 && i0 + i < buf.length; i++) { const t = i / RATE; buf[i0 + i] += v * .5 * Math.sin(2 * Math.PI * f * t) * Math.exp(-t * 5); } },
  tom(buf, i0, v, n = 0) { const f = 140 * Math.pow(2, n / 12); for (let i = 0; i < RATE * .25 && i0 + i < buf.length; i++) { const t = i / RATE; buf[i0 + i] += v * .6 * Math.sin(2 * Math.PI * f * t) * Math.exp(-t * 12); } },
  snare(buf, i0, v, r) { for (let i = 0; i < RATE * .18 && i0 + i < buf.length; i++) { const t = i / RATE; buf[i0 + i] += v * (.35 * (r() * 2 - 1) * Math.exp(-t * 22) + .25 * Math.sin(2 * Math.PI * 190 * t) * Math.exp(-t * 30)); } },
  hat(buf, i0, v, r) { let prev = 0; for (let i = 0; i < RATE * .05 && i0 + i < buf.length; i++) { const t = i / RATE, x = r() * 2 - 1; buf[i0 + i] += v * .5 * (x - prev) * Math.exp(-t * 90); prev = x; } },
  lead(buf, i0, v, n = 0) { const f = 523.25 * Math.pow(2, n / 12); for (let i = 0; i < RATE * .4 && i0 + i < buf.length; i++) { const t = i / RATE; buf[i0 + i] += v * .25 * (Math.sin(2 * Math.PI * f * t) + .4 * Math.sin(4 * Math.PI * f * t)) * Math.exp(-t * 6); } },
  bell(buf, i0, v, n = 0) { const f = 1567.98 * Math.pow(2, n / 12); for (let i = 0; i < RATE * .5 && i0 + i < buf.length; i++) { const t = i / RATE; buf[i0 + i] += v * .2 * (Math.sin(2 * Math.PI * f * t) + .5 * Math.sin(2 * Math.PI * 2.76 * f * t)) * Math.exp(-t * 7); } },
};

// A pattern is 16 sixteenth-note steps per bar; 'x' = hit. Optional note list cycles per hit.
function song(name, bpm, parts, seed) {
  const buf = new Float64Array(RATE * SECONDS), r = rng(seed), step = 60 / bpm / 4;
  for (const [instrument, pattern, notes = [0], vel = 1] of parts) {
    let k = 0;
    for (let s = 0, t = 0; t < SECONDS; s++, t = s * step) {
      if (pattern[s % 16] !== 'x') continue;
      const v = vel * (.85 + .3 * r());  // small deterministic humanised velocity
      inst[instrument](buf, Math.floor(t * RATE), v, typeof notes[0] === 'number' ? notes[k++ % notes.length] : r, r);
    }
  }
  // the snare/hat take the rng as 4th argument; fix the call shape for them
  return buf;
}
// snare and hat signatures are (buf,i0,v,r): adapt by wrapping
for (const k of ['snare', 'hat']) { const f = inst[k]; inst[k] = (b, i, v, a, r) => f(b, i, v, typeof a === 'function' ? a : r); }

const kickMarch = 'x.......x.......', snare24 = '....x.......x...', hats8 = 'x.x.x.x.x.x.x.x.';
const bassMarch = 'x.......x...x...', leadMotif = 'x..x..x...x.x...';
const defs = {
  march80:  [80,  [['kick', kickMarch], ['snare', snare24], ['hat', hats8, [0], .7], ['bass', bassMarch, [0, 0, 7]], ['lead', leadMotif, [0, 3, 7, 5, 3]]], 11],
  march116: [116, [['kick', kickMarch], ['snare', snare24], ['hat', hats8, [0], .7], ['bass', bassMarch, [0, 0, 7]], ['lead', leadMotif, [0, 3, 7, 5, 3]]], 11],
  low96:    [96,  [['kick', 'x...x...x...x...'], ['bass', 'x..x..x...x..x..', [0, 5, 7, 3]], ['tom', '..x.....x.x...x.', [0, -5, 3]]], 22],
  high96:   [96,  [['hat', 'x.x.x.x.x.x.x.x.'], ['lead', 'x..x..x...x..x..', [0, 5, 7, 3]], ['bell', '..x.....x.x...x.', [0, -5, 3]]], 22],
  straight100: [100, [['kick', 'x...x...x...x...'], ['snare', snare24], ['hat', 'x.x.x.x.x.x.x.x.', [0], .7], ['bass', 'x...x...x...x...', [0, 0, 5, 7]]], 33],
  broken100:   [100, [['kick', 'x..x..x...x..x..'], ['snare', snare24], ['hat', '.x.x.xx..x.x.xx.', [0], .7], ['bass', 'x..x..x...x..x..', [0, 0, 5, 7]]], 33],
};

function organScore(bands) {
  const o = new W.Organ(), rows = [];
  for (const b of bands) { const r = o.step(b); rows.push({ b, echo: r.echo, surprise: r.surprise, laps: r.laps, mismatch: r.mismatch }); }
  return rows;
}

const out = { meta: { rate: RATE, seconds: SECONDS, frameRate: 8, worldIndexSha256: require('crypto').createHash('sha256').update(html).digest('hex') }, songs: {} };
for (const [name, [bpm, parts, seed]] of Object.entries(defs)) {
  const audio = song(name, bpm, parts, seed);
  let peak = 0; for (const x of audio) peak = Math.max(peak, Math.abs(x));
  for (let i = 0; i < audio.length; i++) audio[i] *= .8 / peak;   // normalise loudness per song
  const frames = Math.ceil(SECONDS * 8), bands = [];
  for (let t = 0; t < frames; t++) bands.push(W.features(audio, RATE, Math.floor(t * RATE / 8)));
  out.songs[name] = { bpm, rows: organScore(bands) };
  if (process.env.WRITE_WAV) writeWav(path.join(__dirname, 'results', name + '.wav'), audio);
}
for (const v of [0, 1]) {
  const bands = []; for (let t = 0; t < Math.ceil(SECONDS * 8); t++) bands.push(W.weather(t, v));
  out.songs['weather' + v] = { bpm: null, rows: organScore(bands) };
}
function writeWav(file, a) {
  const n = a.length, b = Buffer.alloc(44 + n * 2);
  b.write('RIFF', 0); b.writeUInt32LE(36 + n * 2, 4); b.write('WAVEfmt ', 8); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22);
  b.writeUInt32LE(RATE, 24); b.writeUInt32LE(RATE * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34); b.write('data', 36); b.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) b.writeInt16LE(Math.max(-32767, Math.min(32767, Math.round(a[i] * 32767))), 44 + i * 2);
  fs.writeFileSync(file, b);
}
fs.mkdirSync(path.join(__dirname, 'results'), { recursive: true });
fs.writeFileSync(path.join(__dirname, 'results/scores.json'), JSON.stringify(out));
// short summary
for (const [k, s] of Object.entries(out.songs)) {
  const m = Array(8).fill(0), on = Array(8).fill(0);
  for (const r of s.rows) r.b.forEach((v, i) => { m[i] += v / s.rows.length; on[i] += (v > .18) / s.rows.length; });
  const last = s.rows[s.rows.length - 1];
  console.log(k.padEnd(12), 'mean', m.map(v => v.toFixed(2)).join(' '), '| on', on.map(v => v.toFixed(2)).join(' '), '| laps', last.laps.join(','), 'mis', last.mismatch.toFixed(2));
}
