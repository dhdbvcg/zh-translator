# -*- coding: utf-8 -*-
"""候选方案直接对比:(intraop, beam) 组合。"""
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from zh_translator import Translator

TEXTS = [
    ('en', 'Hello world'),
    ('en', 'The library closes at six in the evening.'),
    ('fr', 'Bonjour, comment allez-vous aujourd hui?'),
    ('de', 'Das Wetter ist heute schön.'),
    ('ru', 'Привет, как дела сегодня?'),
    ('ja', 'こんにちは、お元気ですか。'),
    ('ko', '안녕하세요, 오늘 어떻게 지내세요?'),
    ('ar', 'مرحبا كيف حالك اليوم'),
    ('sw', 'Habari za asubuhi, hujambo?'),
    ('th', 'สวัสดีครับ สบายดีไหม'),
    ('km', 'ជំរាបសួរ តើអ្នកយុត្តទេ?'),
    ('ne', 'नमस्ते, तपाईं कसो हुनुहुन्छ?'),
    ('zu', 'Sawubona, unjani?'),
    ('id', 'Selamat pagi, apa kabar?'),
    ('my', 'မင်္ဂလာပါ'),
]


def bench(intra, beam, rounds=3):
    tr = Translator(intra_threads=intra, beam_size=beam)
    tr.load()
    tr.translate('warmup', source='en')
    lat = []
    outs = []
    for lang, text in TEXTS:
        ts = []
        for _ in range(rounds):
            t0 = time.time()
            r = tr.translate(text, source=lang, beam_size=beam)
            ts.append((time.time() - t0) * 1000)
        lat.append(statistics.median(ts))
        outs.append(r.text)
    del tr
    return lat, outs


CANDS = [(0, 4), (4, 4), (4, 1), (4, 2), (3, 2)]

print('%-14s %-10s %-8s %s' % ('config', 'mean', 'p90', 'vs baseline'))
print('-' * 56)

base_mean = None
store = {}
for intra, beam in CANDS:
    lat, outs = bench(intra, beam)
    mean = sum(lat) / len(lat)
    srt = sorted(lat)
    idx = int(len(srt) * 0.9) - 1
    if idx < 0:
        idx = 0
    p90 = srt[idx]
    key = str(intra) + '/' + str(beam)
    store[key] = (mean, outs)
    if base_mean is None:
        base_mean = mean
    delta = (mean / base_mean - 1) * 100
    label = 'intra=' + str(intra) + ' b=' + str(beam)
    sign = '+' if delta >= 0 else ''
    row = sign + format(delta, '.0f') + '%'
    line = label.ljust(16) + format(mean, '9.0f') + format(p90, '9.0f') + '   ' + row
    print(line)

print()
print('译文一致性 (与基线 intra=0/beam=4 相同的条数):')
base_outs = store['0/4'][1]
for key in sorted(store):
    outs = store[key][1]
    same = sum(1 for a, b in zip(base_outs, outs) if a == b)
    print('  ' + key.ljust(10) + str(same) + ' / ' + str(len(outs)))

print()
print('与基线不同的译文:')
for key in sorted(store):
    if key == '0/4':
        continue
    outs = store[key][1]
    diffs = []
    for i, pair in enumerate(zip(base_outs, outs)):
        if pair[0] != pair[1]:
            diffs.append(TEXTS[i][0] + ': ' + pair[0] + '  ->  ' + pair[1])
    if diffs:
        print('  [' + key + ']')
        for d in diffs:
            print('     ' + d)
