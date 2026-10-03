# -*- coding: utf-8 -*-
"""端到端冒烟测试:验证模型真正可用。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zh_translator import Translator

t0 = time.time()
tr = Translator()
tr.load()
print("loaded in %.1fs on %s" % (time.time() - t0, tr.runtime_device))

CASES = [
    ("en", "Hello, how are you today?"),
    ("ja", "こんにちは、お元気ですか。"),
    ("ru", "Привет, как дела сегодня?"),
    ("ar", "مرحبا كيف حالك اليوم"),
    ("sw", "Habari za asubuhi, hujambo?"),
    ("auto", "Bonjour, comment allez-vous aujourd hui?"),
]

for lang, text in CASES:
    t = time.time()
    r = tr.translate(text, source=lang)
    print("[%s] %-34s -> %-24s (%.2fs, conf=%.2f)"
          % (lang, text[:33], r.text[:23], time.time() - t, r.confidence))
