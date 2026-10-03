# -*- coding: utf-8 -*-
"""模拟浏览器端自检:断言与 web/app.js 保持一致。"""

import json
import sys
import time
import urllib.error
import urllib.request

import os

# 端口可用环境变量覆盖:  set ZT_PORT=8848
PORT = os.environ.get('ZT_PORT', '8848')
BASE = 'http://127.0.0.1:' + PORT


class ApiError(Exception):
    def __init__(self, message, status):
        Exception.__init__(self, message)
        self.status = status


def call(path, payload=None):
    if payload is None:
        req = urllib.request.Request(BASE + path)
    else:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json; charset=utf-8'},
        )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            data = json.loads(body)
        except Exception:
            data = {'error': body}
        raise ApiError(data.get('error', 'HTTP err'), e.code)


def post(text, frm, to=None):
    body = {'text': text, 'from': frm}
    if to:
        body['to'] = to
    return call('/translate', body)


def has_zh(s):
    return any(chr(0x4e00) <= c <= chr(0x9fff) for c in s)


def cond(x, msg):
    if not x:
        raise AssertionError(msg)


def batch_case():
    r = call('/batch', {'texts': ['Hello world', 'Guten Tag', 'Bonjour'],
                     'from': 'auto'})
    ts = r['translations']
    cond(len(ts) == 3, '返回条数不符')
    for t in ts:
        cond(has_zh(t['translation']), '译文无中文')
    langs = [t['source_lang'] for t in ts]
    for want in ('eng_Latn', 'deu_Latn', 'fra_Latn'):
        cond(want in langs, '未识别出 ' + want)
    return ', '.join(langs)


def bad_lang_case():
    try:
        post('hello', '不存在的语种')
    except ApiError as e:
        msg = str(e)
        cond(e.status == 400, '应为 400,实际 ' + str(e.status))
        cond('不支持的语种' in msg, '错误信息不符: ' + msg)
        return '正确拒绝(400):' + msg[:20]
    raise AssertionError('非法语种未被拒绝')


TESTS = [
    ('GET /health', lambda: (lambda r: (
        cond(r['ok'] is True, 'ok 不为 true'),
        'device=' + r['device'],
    )[1])(call('/health'))),
    ('GET /langs', lambda: (lambda r: (
        cond(r['count'] > 50, '语种过少'),
        str(r['count']) + ' 种',
    )[1])(call('/langs'))),
    ('POST /translate en', lambda: (lambda r: (
        cond(has_zh(r['translation']), '译文无中文'),
        r['translation'],
    )[1])(post('Hello world', 'en'))),
    ('POST /translate auto', lambda: (lambda r: (
        cond(r['detected'] is True, 'detected 应为 true'),
        cond(r['source_lang'].startswith('deu'), '识别为 ' + r['source_lang']),
        cond(has_zh(r['translation']), '译文无中文'),
        r['source_lang'] + '  ' + r['translation'],
    )[1])(post('Das Wetter ist heute schön.', 'auto'))),
    ('POST /translate zh-Hant', lambda: (lambda r: (
        cond(has_zh(r['translation']), '译文无中文'),
        r['translation'],
    )[1])(post('Hello world', 'en', 'zh-Hant'))),
    ('POST /translate empty', lambda: (lambda r: (
        cond(r['skipped'] is True, '未跳过'),
        'skipped=true',
    )[1])(post('   ', 'en'))),
    ('POST /translate bad lang', bad_lang_case),
    ('POST /batch mixed', batch_case),
]


results = []
for name, fn in TESTS:
    t0 = time.time()
    try:
        detail = fn()
        results.append((True, name, detail, int((time.time() - t0) * 1000)))
    except Exception as exc:
        results.append((False, name, str(exc), int((time.time() - t0) * 1000)))

print('=' * 72)
ok = sum(1 for x in results if x[0])
for good, name, detail, cost in results:
    txt = (detail or '')[:30]
    print('%s  %-28s %-32s %5d ms' % ('PASS' if good else 'FAIL', name, txt, cost))
print('=' * 72)
print('%d / %d passed' % (ok, len(results)))
sys.exit(0 if ok == len(results) else 1)
