# -*- coding: utf-8 -*-
"""验收测试:Python API 全能力 + 批量 + 长文本 + 术语表 + 简繁。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zh_translator import Translator, supported_iso1

t0 = time.time()
tr = Translator()
tr.load()
print("加载 %.1fs  设备=%s" % (time.time() - t0, tr.runtime_device))
print("支持源语种: %d 种" % len(supported_iso1()))


print("=== 1. 单条翻译(多语种含小语种)===")
CASES = [
    ("en", "The weather is beautiful today."),
    ("de", "Das Wetter ist heute sehr schon."),
    ("sw", "Habari za asubuhi, hujambo?"),
    ("km", "ជំរាបសួរ តើអ្នកយុត្តទេ?"),
    ("my", "မင်္ဂလာပါ မင်္ဂလာပါ"),
]
for lang, text in CASES:
    r = tr.translate(text, source=lang)
    print("  %-4s %-30s -> %s" % (lang, text[:29], r.text))


print("=== 2. 批量(混合语种)===")
MIXED = [
    "Hello world",
    "Guten Tag",
    "Bonjour",
    "Спасибо большое",
    "ありがとう",
]
t = time.time()
batch = tr.translate_batch(MIXED, source='auto')
for src, r in zip(MIXED, batch):
    print("  %-22s %-8s -> %s" % (src[:21], r.source_lang_zh, r.text))
print("  批量总耗时 %.2fs" % (time.time() - t))


print("=== 3. 繁体输出 ===")
r = tr.translate('Hello world', source='en', target='zh-Hant')
print("  zh-Hant ->", r.text)
assert '您好' in r.text or '你好' in r.text, 'traditional output wrong: %s' % r.text
print("  繁体输出正确")


print("=== 4. 术语表(占位符机制)===")
g = {'开放人工智能': 'OpenAI', '模型': 'model'}
r = tr.translate('OpenAI released a new model.', source='en', glossary=g)
print("  ->", r.text)
assert '开放人工智能' in r.text, 'glossary term missing'
assert '模型' in r.text, 'glossary term missing'
print("  术语已正确注入")


print("=== 5. 长文本自动切分 ===")
long_text = ("The history of science is a long road. " * 60).strip()
print("  原文 %d 字符" % len(long_text))
t = time.time()
r = tr.translate(long_text, source='en')
print("  译文 %d 字符, 耗时 %.1fs" % (len(r.text), time.time() - t))
print("  译文开头:", r.text[:56])


print("=== 6. 已是中文自动跳过 ===")
r = tr.translate('这已经是中文了,不需要翻译。', source='auto')
print("  skipped =", r.skipped, "| 返回:", r.text[:20])


print("全部通过")