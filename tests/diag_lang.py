# -*- coding: utf-8 -*-
"""诊断:检查语种自动识别在各语言上的表现。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zh_translator.detect import guess_language

CASES = [
    ("eng_Latn", "Hello, how are you doing today?"),
    ("eng_Latn", "The quick brown fox jumps over the lazy dog"),
    ("fra_Latn", "Bonjour, comment allez-vous aujourd'hui?"),
    ("fra_Latn", "Nous allons à la maison demain"),
    ("fra_Latn", "Je ne sais pas pourquoi il fait si beau aujourd'hui"),
    ("deu_Latn", "Das ist nicht so einfach, oder?"),
    ("deu_Latn", "Guten Tag, ich möchte ein Bier"),
    ("deu_Latn", "Die Geschichte der Wissenschaft ist lang und interessant"),
    ("spa_Latn", "El mundo es muy grande y hermoso"),
    ("spa_Latn", "Buenos días, ¿cómo estás?"),
    ("por_Latn", "Obrigado por sua ajuda, não sei como fazer"),
    ("ita_Latn", "Ciao, come stai oggi?"),
    ("nld_Latn", "Hoe gaat het met u?"),
    ("rus_Cyrl", "Привет, как дела сегодня?"),
    ("ukr_Cyrl", "Привіт, як справи сьогодні?"),
    ("arb_Arab", "مرحبا كيف حالك اليوم"),
    ("heb_Hebr", "שלום, מה שלומך היום"),
    ("hin_Deva", "नमस्ते, आप कैसे हैं"),
    ("tha_Thai", "สวัสดีครับ สบายดีไหม"),
    ("jpn_Jpan", "こんにちは世界"),
    ("kor_Hang", "안녕하세요 세계"),
    ("zho_Hans", "你好世界"),
    ("vie_Latn", "Xin chào, bạn khỏe không?"),
    ("tur_Latn", "Merhaba, nasılsınız?"),
    ("ind_Latn", "Selamat pagi, apa kabar?"),
    ("swa_Latn", "Habari za asubuhi, hujambo?"),
    ("pol_Latn", "Cześć, jak się masz?"),
    ("ces_Latn", "Dobrý den, jak se máš?"),
    ("zho_Hans", "这是一个中文句子"),
]

ok = 0
for expected, text in CASES:
    det = guess_language(text)
    hit = det.flores == expected
    ok += hit
    mark = "OK  " if hit else "MISS"
    print("%s exp=%-10s got=%-10s conf=%.2f method=%-12s %s"
          % (mark, expected, det.flores, det.confidence, det.method, text[:38]))

print("\n%d/%d correct (%.0f%%)" % (ok, len(CASES), 100.0 * ok / len(CASES)))
