# -*- coding: utf-8 -*-
import statistics
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
]


def measure(tr, rounds=3):
    out = []
    for lang, text in TEXTS:
        ts = []
        for _ in range(rounds):
            t0 = time.time()
            tr.translate(text, source=lang)
            ts.append((time.time() - t0) * 1000)
        out.append(statistics.median(ts))
    return out


print('%-8s %-10s %-8s %s' % ('intraop', 'mean', 'min', 'per-lang(ms)'))
print('-' * 74)

rows = []
for n in (0, 2, 3, 4, 6, 8):
    tr = Translator(intra_threads=n)
    tr.load()
    tr.translate('warmup', source='en')
    s = measure(tr)
    mean = sum(s) / len(s)
    rows.append((mean, n))
    label = 'auto' if n == 0 else str(n)
    detail = ' '.join(str(int(x)) for x in s)
    print('%-8s %-10.0f %-8.0f %s' % (label, mean, min(s), detail))
    del tr

best = min(rows, key=lambda x: x[0])
bl = 'auto' if best[1] == 0 else str(best[1])
print()
print('最优 intraop = %s  (%.0f ms)' % (bl, best[0]))
