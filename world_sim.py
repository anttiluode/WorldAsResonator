"""Headless runner for World's simulation shaders (anttiluode/World, vendored).

The shader bodies are read unmodified from vendor/World_index.html. Only the GLSL ES
version/precision lines are translated so desktop OpenGL (EGL) can compile them.
The harness pattern follows World's own tests/gpu_egl.py by Astra; this file adds
what the tuning test needs: arbitrary score feeds, field read/write and a
force-energy probe. This is NOT a browser or WebGL test.
"""
from pathlib import Path
import json, re
import numpy as np
import moderngl

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / 'vendor' / 'World_index.html').read_text()


def _quoted(name):
    return re.search(r'const ' + name + r'=`([\s\S]*?)`;', HTML).group(1)


def _glsl(s):
    return re.sub(r'precision highp (?:float|int);', '', s.replace('#version 300 es', '#version 330'))


ctx = moderngl.create_standalone_context(backend='egl')
_vs = _glsl(_quoted('VS'))
_head = _quoted('HEAD')
_part = HTML.split('const shaders={', 1)[1].split('\n};', 1)[0]
PROGRAMS = {k: ctx.program(vertex_shader=_vs, fragment_shader=_glsl(_head + s))
            for k, s in re.findall(r'(\w+):HEAD\+`([\s\S]*?)`', _part)}
VAOS = {k: ctx.vertex_array(p, []) for k, p in PROGRAMS.items()}

LIVE, FREEZE, KILL = 0, 1, 2


def _target(n):
    t = ctx.texture((n, n), 4, dtype='f4')
    t.filter = (moderngl.NEAREST, moderngl.NEAREST)
    t.repeat_x = t.repeat_y = False
    return t, ctx.framebuffer([t])


def _put(p, k, v):
    if k in p:
        p[k].value = tuple(v) if isinstance(v, (list, tuple, np.ndarray)) else v


class World:
    """One 'world': geometry (bedrock, hardness, natural frequency, mask),
    material (resting sand, mobile sand, compaction, record), force (complex
    oscillator z, transport velocity)."""

    def __init__(self, n=192, seed=2718, structured=1):
        self.n, self.seed, self.structured = n, seed, structured
        self.geo = [_target(n), _target(n)]
        self.mat = [_target(n), _target(n)]
        self.force = [_target(n), _target(n)]
        self.flux = _target(n)
        self.reset()

    def _draw(self, name, target, mode=0, brush=(0, 0, 0)):
        p = PROGRAMS[name]
        target[1].use()
        ctx.viewport = (0, 0, self.n, self.n)
        ctx.disable(moderngl.DEPTH_TEST)
        for i, (k, t) in enumerate([('geo', self.geo[0]), ('mat', self.mat[0]),
                                    ('force', self.force[0]), ('flux', self.flux)]):
            t[0].use(i)
            _put(p, k, i)
        for k, v in [('N', self.n), ('seed', self.seed), ('tick', self.tick), ('structured', self.structured),
                     ('mode', mode), ('brush', brush), ('bands', self.bands), ('echo', self.echo),
                     ('surprise', self.surprise), ('organOn', self.organ_on)]:
            _put(p, k, v)
        VAOS[name].render(vertices=3)

    def reset(self):
        self.tick = 0
        self.bands, self.echo, self.surprise, self.organ_on = [0.] * 8, [0.] * 8, 0., 1.
        self._draw('seed', self.geo[1]); self.geo.reverse()
        self._draw('init', self.mat[1]); self.mat.reverse()
        self.clear_forces()

    def clear_forces(self):
        for t in self.force:
            t[1].clear(0, 0, 0, 0)
        self.flux[1].clear(0, 0, 0, 0)

    def step(self, row, force_mode=LIVE, matter_mode=LIVE):
        self.bands, self.echo, self.surprise = row['b'], row['echo'], row['surprise']
        self._draw('force', self.force[1], force_mode); self.force.reverse()
        self._draw('flux', self.flux)
        self._draw('matter', self.mat[1], matter_mode); self.mat.reverse()
        self.tick += 1

    def play(self, rows, ticks=None, matter_mode=LIVE, measure_every=0, skip=0):
        """Feed a song. World's clock: 32 simulation ticks per second, one feature
        frame (8 per second) held for 4 ticks. Returns sampled force fields if
        measure_every > 0."""
        ticks = ticks if ticks is not None else 4 * len(rows)
        samples = []
        for k in range(ticks):
            self.step(rows[(k // 4) % len(rows)], matter_mode=matter_mode)
            if measure_every and k >= skip and k % measure_every == 0:
                samples.append(self.read('force'))
        return samples

    def read(self, name):
        return np.frombuffer(getattr(self, name)[0][0].read(), np.float32).reshape(self.n, self.n, 4).copy()

    def write(self, name, data):
        getattr(self, name)[0][0].write(np.ascontiguousarray(data, dtype='f4').tobytes())

    def close(self):
        for arr in (self.geo, self.mat, self.force, [self.flux]):
            for t, f in arr:
                f.release(); t.release()


def load_scores():
    return json.loads((ROOT / 'results' / 'scores.json').read_text())
