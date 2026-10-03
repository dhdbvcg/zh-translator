# -*- coding: utf-8 -*-
import json
import statistics
import sys
import time
import urllib.request

BASE = 'http://127.0.0.1:8848'
SAMPLES = [
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


def call(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode('utf-8')), (time.time() - t0) * 1000


print('=' * 62)
print('HTTP 接口实测 (16 语种, 2 轮取中位数)')
print('=' * 62)

store = {}
for speed in ('fast', 'balanced', 'quality'):
    lat = []
    outs = []
    for lang, text in SAMPLES:
        ts = []
        for _ in range(2):
            d, ms = call('/translate', {'text': text, 'from': lang, 'speed': speed})
            ts.append(ms)
        lat.append(statistics.median(ts))
        outs.append(d['translation'])
    store[speed] = outs
    mean = sum(lat) / len(lat)
    print('  %-9s 平均 %5.0f ms   最慢 %5.0f ms'
          % (speed, mean, max(lat)))

print()
print('译文差异 (fast vs quality):')
qf = store['fast']
qq = store['quality']
n = 0
for i, pair in enumerate(zip(qf, qq)):
    if pair[0] != pair[1]:
        n += 1
        print('  ' + SAMPLES[i][0] + ': ' + pair[0] + '  ->  ' + pair[1])
print('  共 %d / %d 处不同' % (n, len(SAMPLES)))
