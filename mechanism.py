"""Which material channel holds the tuning?

Grow world A on song a and world B on song b (same seed). Then build hybrids:
A with ONE channel replaced by B's (resting sand, mobile sand, compaction).
Probe each with both songs, matter frozen, and compute the 2x2 tuning index
T = (A:a + B:b - A:b - B:a) / mean. If swapping channel c from B into A flips
A's preference toward b, channel c carries the memory.
"""
import json, sys
import numpy as np
from world_sim import World, FREEZE, load_scores, ROOT
from tuning import GROW_TICKS, PROBE_TICKS, SKIP

CH = {'sand': 0, 'mobile': 1, 'compaction': 2}


def main(a, b, seed):
    S = load_scores()['songs']
    w = World(192, seed)
    mask = w.read('geo')[..., 3] > .5
    grown = {}
    for s in (a, b):
        w.reset(); w.play(S[s]['rows'], GROW_TICKS); grown[s] = (w.read('geo'), w.read('mat'))

    def probe(state, song):
        w.reset(); w.write('geo', state[0]); w.write('mat', state[1]); w.clear_forces()
        F = w.play(S[song]['rows'], PROBE_TICKS, matter_mode=FREEZE, measure_every=4, skip=SKIP)
        return float(np.mean([(f[..., 0] ** 2 + f[..., 1] ** 2)[mask].mean() for f in F]))

    def pref(state):
        """log preference of this world for a over b (bigger = prefers a)"""
        return np.log(probe(state, a)) - np.log(probe(state, b))

    out = {'pair': [a, b], 'seed': seed}
    pA, pB = pref(grown[a]), pref(grown[b])
    out['A_pref_a'], out['B_pref_a'] = pA, pB
    out['gap'] = pA - pB      # >0: A prefers a more than B does = tuning
    for name, c in CH.items():
        g, m = grown[a][0], grown[a][1].copy()
        m[..., c] = grown[b][1][..., c]
        out['A_with_B_' + name] = pref((g, m))
    # keep everything of B except compaction from A, for symmetry
    for name, c in CH.items():
        g, m = grown[b][0], grown[b][1].copy()
        m[..., c] = grown[a][1][..., c]
        out['B_with_A_' + name] = pref((g, m))
    w.close()
    return out


if __name__ == '__main__':
    a, b = sys.argv[1], sys.argv[2]
    seeds = [int(x) for x in sys.argv[3:]] or [2718]
    path = ROOT / 'results' / 'mechanism.json'
    res = json.loads(path.read_text()) if path.exists() else []
    for seed in seeds:
        o = main(a, b, seed)
        res.append(o)
        path.write_text(json.dumps(res, indent=1))
        share = {k: (o['A_pref_a'] - o['A_with_B_' + k]) / o['gap'] for k in CH}
        print(a, b, seed, f"gap {o['gap']:+.4f}", 'fraction of gap moved by swapping into A:',
              ' '.join(f'{k} {v:+.2f}' for k, v in share.items()), flush=True)
