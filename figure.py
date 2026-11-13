"""Figure: where in the ground the song was learned, and where the world rings.

One pair, one seed. Panels:
  1. compaction of world grown on song a
  2. compaction of world grown on song b
  3. compaction difference (a - b)
  4. response difference: [A hears a - B hears a] - [A hears b - B hears b]
     red = cells that ring more for their own song (tuning), blue = the reverse
Renders with matplotlib-free numpy + PIL so it runs anywhere.
"""
import sys
import numpy as np
from PIL import Image, ImageDraw
from world_sim import World, FREEZE, load_scores, ROOT
from tuning import GROW_TICKS, PROBE_TICKS, SKIP


def diverging(x, lim):
    t = np.clip(x / lim, -1, 1)
    r = np.where(t > 0, 1, 1 + t); b = np.where(t < 0, 1, 1 - t); g = 1 - np.abs(t)
    return np.stack([r, g * .97, b], -1)


def seq(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo + 1e-12), 0, 1)
    return np.stack([.06 + .9 * t, .09 + .8 * t ** 1.2, .12 + .62 * t ** 1.6], -1)


def main(a, b, seed):
    S = load_scores()['songs']
    w = World(192, seed)
    mask = w.read('geo')[..., 3] > .5
    grown = {}
    for s in (a, b):
        w.reset(); w.play(S[s]['rows'], GROW_TICKS); grown[s] = (w.read('geo'), w.read('mat'))

    def emap(state, song):
        w.reset(); w.write('geo', state[0]); w.write('mat', state[1]); w.clear_forces()
        F = w.play(S[song]['rows'], PROBE_TICKS, matter_mode=FREEZE, measure_every=4, skip=SKIP)
        return np.mean([(f[..., 0] ** 2 + f[..., 1] ** 2) for f in F], axis=0)

    E = {(x, y): emap(grown[x], y) for x in (a, b) for y in (a, b)}
    tune = (E[a, a] - E[b, a]) - (E[a, b] - E[b, b])
    ca, cb = grown[a][1][..., 2], grown[b][1][..., 2]
    panels = [(seq(ca, 0, max(ca.max(), cb.max())), f'compaction, grown on {a}'),
              (seq(cb, 0, max(ca.max(), cb.max())), f'compaction, grown on {b}'),
              (diverging(ca - cb, np.percentile(np.abs(ca - cb)[mask], 99)), f'compaction {a} minus {b}'),
              (diverging(tune, np.percentile(np.abs(tune)[mask], 99)), 'tuning: red rings more for own song')]
    s, pad, top = 3, 16, 30
    W_, H_ = 4 * 192 * s + 5 * pad, 192 * s + top + pad
    img = Image.new('RGB', (W_, H_), (10, 14, 16)); d = ImageDraw.Draw(img)
    for i, (rgb, title) in enumerate(panels):
        rgb = np.where(mask[..., None], rgb, np.array([.04, .055, .06]))
        tile = Image.fromarray((np.flipud(rgb) * 255).astype(np.uint8)).resize((192 * s, 192 * s), Image.NEAREST)
        x = pad + i * (192 * s + pad); img.paste(tile, (x, top)); d.text((x, 8), title, fill=(220, 225, 220))
    out = ROOT / 'results' / f'figure_{a}_{b}_{seed}.png'
    img.save(out)
    inside = tune[mask]
    print(out, 'tuning map: own-song cells', float((inside > 0).mean()), 'sum', float(inside.sum()))
    w.close()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2718)
