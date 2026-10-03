# -*- coding: utf-8 -*-
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

PORT = '8905'
BASE = 'http://127.0.0.1:' + PORT


def call(path, payload=None):
    if payload is None:
        req = urllib.request.Request(BASE + path)
    else:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json; charset=utf-8'},
        )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode('utf-8'))
    return data, (time.time() - t0) * 1000


SAMPLES = [
    ('en', 'Hello world'),
    ('en', 'The library closes at six in the evening.'),
    ('de', 'Das Wetter ist heute schön.'),
    ('fr', 'Bonjour, comment allez-vous aujourd hui?'),
    ('es', 'El mundo es muy grande y hermoso.'),
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
]


print('=' * 64)
print('阶段耗时')
print('=' * 64)

t0 = time.time()
call('/health')
print('  /health 探活       %7.0f ms' % ((time.time() - t0) * 1000))

d, ms = call('/translate', {'text': 'Hello world', 'from': 'en'})
print('  首次翻译(冷启动)  %7.0f ms  -> %s' % (ms, d['translation']))

d, ms = call('/translate', {'text': 'Hello world', 'from': 'en'})
print('  第二次(同文本)    %7.0f ms' % ms)

print()
print('=' * 64)
print('稳态单句延迟  beam=4  轮 3 次取中位数')
print('=' * 64)

rows = []
for lang, text in SAMPLES:
    times = []
    for _ in range(3):
        d, ms = call('/translate', {'text': text, 'from': lang})
        times.append(ms)
    rows.append((statistics.median(times), lang, text, d['translation']))

for med, lang, text, tr in rows:
    print('  %-4s %7.0f ms   %-32s -> %s' % (lang, med, text[:31], tr[:16]))

alls = [r[0] for r in rows]
print()
print('  平均 %.0f ms   最快 %.0f ms   最慢 %.0f ms' % (sum(alls) / len(alls), min(alls), max(alls)))
