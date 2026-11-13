import time, sys, numpy as np
from world_sim import World, FREEZE, load_scores

S = load_scores()['songs']
a, b = sys.argv[1], sys.argv[2]
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 2718
n = int(sys.argv[4]) if len(sys.argv) > 4 else 192
w = World(n, seed)
base = (w.read('geo'), w.read('mat'))
t0 = time.time()
grown = {}
for s in (a, b):
    w.reset(); w.play(S[s]['rows']); grown[s] = (w.read('geo'), w.read('mat'))
print('grow s', time.time() - t0)
mask = base[0][..., 3] > .5


def probe(state, song, ticks=1280, skip=256):
    w.reset(); w.write('geo', state[0]); w.write('mat', state[1]); w.clear_forces()
    F = w.play(S[song]['rows'], ticks, matter_mode=FREEZE, measure_every=4, skip=skip)
    return float(np.mean([(f[..., 0] ** 2 + f[..., 1] ** 2)[mask].mean() for f in F]))


t0 = time.time()
R = {(wn, s): probe(st, s) for wn, st in [('base', base), ('A', grown[a]), ('B', grown[b])] for s in (a, b)}
print('probe s', time.time() - t0)
for wn in ('base', 'A', 'B'):
    print(wn, ' '.join(f'{s}:{R[(wn, s)]:.5f}' for s in (a, b)))
T = (R['A', a] + R['B', b] - R['A', b] - R['B', a]) / np.mean([R['A', a], R['B', b], R['A', b], R['B', a]])
print('tuning index', T)
print('sand diff', np.abs(grown[a][1][..., 0] - grown[b][1][..., 0])[mask].mean(), 'compact diff', np.abs(grown[a][1][..., 2] - grown[b][1][..., 2])[mask].mean())
