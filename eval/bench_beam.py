# -*- coding: utf-8 -*-
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from zh_translator import Translator

TEXTS = [
    ('en', 'Hello world'),
    ('fr', 'Bonjour, comment allez-vous aujourd hui?'),
    ('de', 'Das Wetter ist heute schön.'),
    ('ru', 'Привет, как дела сегодня?'),
    ('ja', 'こんにちは、お元気ですか。'),
    ('sw', 'Habari za asubuhi, hujambo?'),
    ('ar', 'مرحبا كيف حالك اليوم'),
    ('km', 'ជំរាបសួរ តើអ្នកយុត្តទេ?'),
]

tr = Translator(intra_threads=4)
tr.load()
tr.translate('warmup', source='en')

print('%-6s %-10s %s' % ('beam', 'mean(ms)', '与 beam=1 相同的译文数'))
print('-' * 60)

rows = []
base = None
for beam in (1, 2, 4, 8):
    ts = []
    outs = []
    for lang, text in TEXTS:
        t0 = time.time()
        r = tr.translate(text, source=lang, beam_size=beam)
        ts.append((time.time() - t0) * 1000)
        outs.append(r.text)
    mean = sum(ts) / len(ts)
    rows.append((beam, mean, outs))
    if base is None:
        base = outs
    same = sum(1 for a, b in zip(base, outs) if a == b)
    label = 'beam=' + str(beam)
    print('%-6s %-10.0f %d / %d' % (label, mean, same, len(outs)))

print()
print('译文对比 (法语 / 高棉语):')
for beam, mean, outs in rows:
    print('  beam=' + str(beam))
    print('    fr: ' + outs[1])
    print('    km: ' + outs[7])
