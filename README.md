# World as Resonator

**Question:** if a song grows a world in Astra's [World](https://github.com/anttiluode/World), does that world become a resonator for that song? Does it ring more for the song that made it than for other songs?

**Answer so far: no.** It rings very slightly *less* for its own song, a weak habituation, and it cannot tell which song grew it. Details and numbers are below. The mechanism test (which material channel holds the effect) is still running; this README will be updated when it finishes.

*Do not hype. Do not lie. Just show.*

## What was run

World is used **unmodified**. `vendor/World_index.html` is a byte copy of World's `index.html` at commit `ceb9095` (sha256 `2643121…cd72cf`). The simulation shaders are read from that file and run headless through OpenGL/EGL, following the pattern of World's own `tests/gpu_egl.py`. This is a Mesa llvmpipe CPU backend, **not a browser and not your RTX 3060**.

1. **Songs.** `songs.cjs` synthesizes six 120-second drum-machine tracks as real audio. They come in pairs that differ in one thing only:
   - tempo: `march80` vs `march116`
   - register: `low96` (kick, bass, toms) vs `high96` (hats, lead, bells)
   - rhythm: `straight100` vs `broken100`

   World's own two generated weathers are added as a fourth pair. All audio is turned into band scores by World's own `features()` and its Korva-style `Organ`, loaded from World's code, not re-implemented.
2. **Grow.** One world per song, same seed, same starting ground: 120 s of song = 3840 ticks of World's 32 Hz clock.
3. **Listen.** Every grown world, plus the ungrown one, hears every song for 40 s **with the ground frozen** (World's own freeze mode), so listening writes nothing. The response is the mean oscillator energy |z|² over the basin, ignoring the first 8 s.
4. **Score.** `L = log(response / ungrown response)`, double-centred to remove "this world is louder overall" and "this song is louder overall". If worlds are tuned, the diagonal (world × its own song) is positive. A label-permutation null gives the p-value.

Five seeds: 2718, 1, 42, 2026, 7. Each 8×8 run takes about 5 minutes on llvmpipe.

## Results

| | Value |
|---|---|
| Own-song response, pooled over 5 seeds | **−0.67 %** (two-sided p = 0.017) |
| Recognition: which world rings most for a song | 0–1 of 8 per seed (chance = 1 of 8) |
| General dulling: grown vs ungrown, all songs | worlds respond 4–8 % less to everything |
| Spread between worlds for the same song | about 2–4 % (log) |

Per pair, 2×2 tuning index (positive = tuned, negative = habituated):

| Pair | Seeds 2718, 1, 42, 2026, 7 | Same sign |
|---|---|---|
| tempo 80 vs 116 | −0.040 −0.092 −0.053 −0.033 −0.040 | 5/5 negative |
| register low vs high | +0.033 +0.011 +0.008 +0.023 +0.010 | 5/5 positive |
| rhythm straight vs broken | −0.030 −0.075 −0.047 −0.018 −0.042 | 5/5 negative |
| World weather 0 vs 1 | −0.005 +0.000 −0.019 −0.006 −0.005 | 4/5 negative |

What this says:

- The ground **does** remember the song in a measurable, reproducible way: the sign of each pair is stable across seeds.
- The memory is the **wrong shape for a resonator**. Growing makes a world duller overall, and the song-specific part is about ten times smaller than that dulling. Where it's specific, it's mostly *less* response to the familiar song.
- Register is the one property that leans toward tuning, and only weakly (+1–3 %).

Raw data: `results/tuning.json` (all matrices), `results/pooled.json`, `results/tuning.log`.

## Why, from World's force shader (reading, not yet measured)

In World's force pass, a song reaches a cell as a slow push, `drive = bands[b] + .34*echo[b]`. The band `b` is fixed by the seeded natural-frequency map `g.b`, not by the ground. The ground acts on the oscillator in only two places: sand raises the rotation rate (`+1.7*m.r`), and compaction adds damping (`-.8*m.b`). Neither lets a song choose *which* cells listen to *which* band. The ground can only make cells louder or quieter, so a gain change is the expected result, not a tuned filter. The mechanism test (`mechanism.py`) swaps sand, mobile sand and compaction between grown worlds one at a time to check which channel actually carries the effect.

## Rerun

```sh
pip install numpy moderngl Pillow   # needs an EGL implementation
node songs.cjs                      # songs -> results/scores.json via World's own front end
python tuning.py 2718 1 42 2026 7   # 8x8 grow/listen matrices
python pooled.py                    # pooled two-sided analysis
python mechanism.py march80 march116 2718 1 42
```

`WRITE_WAV=1 node songs.cjs` also writes the test songs as .wav files, so you can play them into World in the browser yourself.

## Ledger

| Item | Status |
|---|---|
| World code | Unmodified; vendored byte copy, hash recorded |
| Front end and organ | World's own `features()` and `Organ`, executed from its file |
| Backend | Mesa llvmpipe through EGL. Not WebGL, not RTX 3060. Float results may differ across GPUs. |
| Songs | Synthetic drum-machine audio, not real music. Real songs might behave differently. |
| Response measure | Mean oscillator energy only. A spatial-pattern readout was not tested and might carry more song identity. |
| Grow length | 120 s per song. Longer growth was not tested. |
| Mechanism | Running |
