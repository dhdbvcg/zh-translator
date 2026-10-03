# -*- coding: utf-8 -*-
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from zh_translator import Translator
from zh_translator.tuning import describe

TEXTS = [
    ('en', 'Hello world'),
    ('en', 'The library closes at six in the evening.'),
    ('de', 'Das Wetter ist heute schön.'),
    ('fr', 'Bonjour, comment allez-vous aujourd hui?'),
    ('ru', 'Привет, как дела сегодня?'),
    ('ja', 'こんにちは、お元気ですか。'),
    ('ko', '안녕하세요, 오늘 어떻게 지내세요?'),
    ('ar', 'مرحبا كيف حالك اليوم'),
    ('sw', 'Habari za asubuhi, hujambo?'),
    ('vi', 'Xin chào, bạn khỏe không?'),
    ('th', 'สวัสดีครับ สบายดีไหม'),
    ('km', 'ជំរាបសួរ តើអ្នកយុត្តទេ?'),
    ('ne', 'नमस्ते, तपाईं कसो हुनुहुन्छ?'),
    ('zu', 'Sawubona, unjani?'),
    ('id', 'Selamat pagi, apa kabar?'),
    ('my', 'မင်္ဂလာပါ'),
]


def run(tr, rounds=3):
    lat = []
    outs = []
    for lang, text in TEXTS:
        ts = []
        for _ in range(rounds):
            t0 = time.time()
            r = tr.translate(text, source=lang)
            ts.append((time.time() - t0) * 1000)
        lat.append(statistics.median(ts))
        outs.append(r.text)
    return lat, outs
info = describe()
print('环境: 逻辑核 %d / 物理核 %d -> intra_threads=%d'
      % (info['logical_cpus'], info['physical_cpus'], info['intra_threads']))
print('=' * 72)
print('%-26s %-9s %-8s' % ('配置', '平均ms', '最慢'))
print('-' * 72)

CFGS = [
    ('优化前 8线程/beam4', dict(intra_threads=8, beam_size=4, speed=None)),
    ('默认 auto', dict()),
    ('speed=fast', dict(speed='fast')),
    ('speed=balanced', dict(speed='balanced')),
    ('speed=quality', dict(speed='quality')),
]

store = {}
for name, kw in CFGS:
    tr = Translator(**kw)
    tr.load()
    tr.translate('warmup', source='en')
    lat, outs = run(tr)
    mean = sum(lat) / len(lat)
    srt = sorted(lat)
    store[name] = outs
    print(name.ljust(26) + format(mean, '9.0f') + format(srt[-1], '8.0f'))
    del tr

print()
base = store['优化前 8线程/beam4']
print('译文与优化前的差异:')
for name in list(store)[1:]:
    outs = store[name]
    diff = []
    for i, pair in enumerate(zip(base, outs)):
        if pair[0] != pair[1]:
            diff.append(TEXTS[i][0] + ': ' + pair[0] + '  ->  ' + pair[1])
    print('  [' + name + '] ' + str(len(diff)) + ' / ' + str(len(base)) + ' 处不同')
    for d in diff:
        print('     ' + d)
