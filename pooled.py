"""Pool the per-seed tuning matrices. Two-sided: is there tuning (diag > 0) OR
habituation (diag < 0)? Null: independent label permutations within each seed,
averaged across seeds."""
import json
import numpy as np
from tuning import analyse, ROOT

d = json.loads((ROOT / 'results' / 'tuning.json').read_text())
songs, seeds = d['songs'], list(d['seeds'])
Ls = [np.array(d['seeds'][s]['L']) for s in seeds]
k = len(songs)
obs = float(np.mean([np.trace(L) / k for L in Ls]))
rng = np.random.default_rng(1)
null = np.array([np.mean([L[np.arange(k), rng.permutation(k)].mean() for L in Ls]) for _ in range(50000)])
p_two = float((np.sum(np.abs(null) >= abs(obs)) + 1) / (len(null) + 1))
# per-song diagonal across seeds: which songs make worlds that ring less / more for themselves
per_song = {s: [float(L[i, i]) for L in Ls] for i, s in enumerate(songs)}
pairs = {p: [d['seeds'][s]['pairs'][p] for s in seeds] for p in d['seeds'][seeds[0]]['pairs']}
# overall effect of growth: gain of grown world vs ungrown, averaged over all songs
gains = {s: float(np.mean(np.array(d['seeds'][s]['R'])[1:] / np.array(d['seeds'][s]['R'])[0])) for s in seeds}
# how much of the total variation is the diagonal: spread of log gain across worlds for a fixed song
spread = {s: float(np.std(np.log(np.array(d['seeds'][s]['R'])[1:] / np.array(d['seeds'][s]['R'])[0]), axis=0).mean()) for s in seeds}
summary = dict(seeds=seeds, meanDiag=obs, meanDiagPct=float((np.exp(obs) - 1) * 100), pTwoSided=p_two,
               perSongDiag=per_song, pairs=pairs, growthGain=gains, worldSpreadLog=spread,
               recSong=[d['seeds'][s]['rec_song'] for s in seeds], recWorld=[d['seeds'][s]['rec_world'] for s in seeds])
(ROOT / 'results' / 'pooled.json').write_text(json.dumps(summary, indent=1))
print(f'seeds {seeds}')
print(f'mean diagonal {obs:+.4f} = {summary["meanDiagPct"]:+.2f}% own-song gain, two-sided p = {p_two:.4f}')
print('recognition by song', summary['recSong'], 'by world', summary['recWorld'], '(chance 0.125)')
for p, v in pairs.items():
    print(f'{p:24s}', ' '.join(f'{x:+.3f}' for x in v), f'| mean {np.mean(v):+.3f}, same sign {max(sum(x > 0 for x in v), sum(x < 0 for x in v))}/{len(v)}')
for s, v in per_song.items():
    print(f'{s:12s} own-song L', ' '.join(f'{x:+.4f}' for x in v))
print('growth gain vs ungrown (all songs):', {k: round(v, 3) for k, v in gains.items()})
print('typical log spread across worlds for one song:', {k: round(v, 4) for k, v in spread.items()})
