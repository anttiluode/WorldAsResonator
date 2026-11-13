"""The tuning test: does a world grown on a song become a resonator for that song?

For each seed:
  1. Grow one world per song (same seed, same start; only the song differs).
  2. Probe every grown world, plus the ungrown base world, with every song while
     MATTER IS FROZEN (World's own 'freeze' mode). Forces run live. So the probe
     reads what the grown material does to the oscillator field; nothing is
     written during listening.
  3. Response R[world, song] = mean oscillator energy |z|^2 over the domain,
     sampled every 4 ticks after an 8 s settling window.

Analysis (no extra simulation):
  Q = R / R[base, song]          gain relative to the ungrown world
  L = log Q double-centred       removes 'this world is louder' and 'this song is louder'
  diagonal mean of L > 0         = each world prefers the song that made it
  recognition                    = argmax over worlds of L[:, song] == song
  permutation null               = shuffle which world is assigned to which song
"""
import json, sys, time, itertools
import numpy as np
from world_sim import World, FREEZE, load_scores, ROOT

SONGS = ['march80', 'march116', 'low96', 'high96', 'straight100', 'broken100', 'weather0', 'weather1']
GROW_TICKS = 3840          # 120 s of song at World's 32 Hz clock
PROBE_TICKS, SKIP = 1280, 256   # 40 s probe, first 8 s ignored


def run_seed(seed, n=192, songs=SONGS):
    S = load_scores()['songs']
    w = World(n, seed)
    base = (w.read('geo'), w.read('mat'))
    mask = base[0][..., 3] > .5
    grown = {}
    for s in songs:
        w.reset(); w.play(S[s]['rows'], GROW_TICKS); grown[s] = (w.read('geo'), w.read('mat'))

    def probe(state, song):
        w.reset(); w.write('geo', state[0]); w.write('mat', state[1]); w.clear_forces()
        F = w.play(S[song]['rows'], PROBE_TICKS, matter_mode=FREEZE, measure_every=4, skip=SKIP)
        e = np.mean([(f[..., 0] ** 2 + f[..., 1] ** 2) for f in F], axis=0)
        return float(e[mask].mean()), e

    R = np.zeros((len(songs) + 1, len(songs)))
    maps = {}
    for i, (wn, st) in enumerate([('base', base)] + [(s, grown[s]) for s in songs]):
        for j, s in enumerate(songs):
            R[i, j], maps[(wn, s)] = probe(st, s)
    # material differences between grown worlds, for context
    mat_diff = {f'{a}|{b}': float(np.abs(grown[a][1][..., :3] - grown[b][1][..., :3])[mask].mean())
                for a, b in itertools.combinations(songs, 2)}
    w.close()
    return R, mat_diff, maps, grown, base, mask


def analyse(R, perms=20000, rng=np.random.default_rng(0)):
    base, G = R[0], R[1:]
    L = np.log(G / base)
    L = L - L.mean(1, keepdims=True) - L.mean(0, keepdims=True) + L.mean()
    k = len(L)
    diag = float(np.trace(L) / k)
    null = np.array([np.mean(L[np.arange(k), rng.permutation(k)]) for _ in range(perms)])
    p = float((np.sum(null >= diag) + 1) / (perms + 1))
    rec_song = float(np.mean(L.argmax(0) == np.arange(k)))   # which world rings most for this song
    rec_world = float(np.mean(L.argmax(1) == np.arange(k)))  # which song this world rings most for
    return dict(diag=diag, p=p, rec_song=rec_song, rec_world=rec_world, L=L.tolist(),
                gain_pct=float((np.exp(diag) - 1) * 100))


def pair_index(R, a, b, songs=SONGS):
    """2x2 log gap: log(A:a * B:b / (A:b * B:a)). > 0 = each world prefers its own song.
    (An earlier version normalised raw energies by their sum; that let a loud song
    swamp a quiet one, e.g. low96 vs high96 differ ~100x on some seeds. Replaced.)"""
    i, j = songs.index(a), songs.index(b)
    G = R[1:]
    return float(np.log(G[i, i] * G[j, j] / (G[i, j] * G[j, i])))


if __name__ == '__main__':
    seeds = [int(x) for x in sys.argv[1:]] or [2718]
    out = {'songs': SONGS, 'growTicks': GROW_TICKS, 'probeTicks': PROBE_TICKS, 'skip': SKIP, 'seeds': {}}
    path = ROOT / 'results' / 'tuning.json'
    if path.exists():
        out = json.loads(path.read_text())
    for seed in seeds:
        t = time.time()
        R, md, *_ = run_seed(seed)
        a = analyse(R)
        a['pairs'] = {f'{x}|{y}': pair_index(R, x, y) for x, y in
                      [('march80', 'march116'), ('low96', 'high96'), ('straight100', 'broken100'), ('weather0', 'weather1')]}
        out['seeds'][str(seed)] = dict(R=R.tolist(), matDiff=md, **a, seconds=time.time() - t)
        path.write_text(json.dumps(out, indent=1))
        print(seed, f"diag {a['diag']:+.4f} ({a['gain_pct']:+.2f}%) p={a['p']:.4f} recSong {a['rec_song']:.2f} recWorld {a['rec_world']:.2f}",
              ' '.join(f'{k}:{v:+.3f}' for k, v in a['pairs'].items()), f'{time.time() - t:.0f}s', flush=True)
