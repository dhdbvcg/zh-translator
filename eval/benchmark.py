"""端到端质量与速度评测。

用法::

    python eval/benchmark.py
    python eval/benchmark.py --model models/nllb-zh-int8-1.3b

评测集为多语种代表性短句(含小语种),逐条输出译文与耗时。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zh_translator import Translator  # noqa: E402

# (源语种, 原文)
SAMPLES = [
    ("en", "Hello, how are you today?"),
    ("en", "The library closes at six in the evening."),
    ("fr", "Bonjour, comment allez-vous aujourd'hui?"),
    ("de", "Das Wetter ist heute sehr schön."),
    ("es", "El mundo es muy grande y hermoso."),
    ("ru", "Привет, как дела сегодня?"),
    ("ja", "こんにちは、お元気ですか。"),
    ("ko", "안녕하세요, 오늘 어떻게 지내세요?"),
    ("ar", "مرحبا كيف حالك اليوم"),
    ("sw", "Habari za asubuhi, hujambo?"),
    ("vi", "Xin chào, bạn khỏe không?"),
    ("th", "สวัสดีครับ สบายดีไหม"),
    ("km", "ជំរាបសួរ តើអ្នកយុត្តទេ?"),
    ("ne", "नमस्ते, तपाईं कसो हुनुहुन्छ?"),
    ("my", "မင်္ဂလာပါ မင်္ဂလာပါ"),
    ("zu", "Sawubona, unjani?"),
    ("he", "שלום, מה שלומך היום?"),
    ("hi", "नमस्ते, आप कैसे हैं?"),
    ("tr", "Merhaba, nasılsınız?"),
    ("id", "Selamat pagi, apa kabar?"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="翻译质量与速度评测")
    ap.add_argument("--model", default=None, help="模型目录")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--beam", type=int, default=4)
    args = ap.parse_args()

    tr = Translator(model_dir=args.model, device=args.device, beam_size=args.beam)
    t0 = time.time()
    tr.load()
    print("模型加载: %.1fs, 运行设备: %s" % (time.time() - t0, tr.runtime_device),
          file=sys.stderr)

    print("=" * 76)
    print("%-5s %-32s %-28s %s" % ("语种", "原文", "译文", "耗时"))
    print("=" * 76)

    total = 0.0
    for lang, src in SAMPLES:
        t = time.time()
        res = tr.translate(src, source=lang)
        dt = time.time() - t
        total += dt
        print("%-5s %-32s %-28s %.2fs" % (lang, src[:31], res.text[:27], dt))

    print("=" * 76)
    print("共 %d 条,平均 %.2f 秒/条" % (len(SAMPLES), total / len(SAMPLES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
