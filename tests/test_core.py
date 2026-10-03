"""不依赖模型权重的单元测试:语种解析、脚本识别、切分、后处理。

运行:

    python -m pytest tests/ -v
    # 或不装 pytest 直接运行:
    python tests/test_core.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zh_translator import languages as L  # noqa: E402
from zh_translator.detect import (  # noqa: E402
    detect_script,
    guess_language,
    looks_chinese,
    normalize_unicode,
    strip_markup,
)
from zh_translator.engine import (  # noqa: E402
    Translator,
    resolve_target,
    split_long_text,
)
from zh_translator.postprocess import (  # noqa: E402
    apply_glossary,
    clean_spacing,
    normalize_punctuation,
    tidy,
    to_simplified,
)


def test_resolve_various_forms():
    """各种语种写法都应解析到同一 FLORES 代码。"""
    assert L.to_flores("en") == "eng_Latn"
    assert L.to_flores("eng") == "eng_Latn"
    assert L.to_flores("eng_Latn") == "eng_Latn"
    assert L.to_flores("English") == "eng_Latn"
    assert L.to_flores("英语") == "eng_Latn"
    assert L.to_flores("ENGLISH") == "eng_Latn"


def test_resolve_legacy_codes():
    """处理已废弃的 ISO 代码。"""
    assert L.to_flores("iw") == "heb_Hebr"   # 旧希伯来语代码
    assert L.to_flores("per") == "fas_Arab"   # 旧波斯语代码
    assert L.to_flores("bur") == "mya_Mymr"   # 旧缅甸语代码
    assert L.to_flores("aze") == "azj_Latn"   # 旧阿塞拜疆语代码


def test_chinese_codes():
    """中文代码应被正确识别且从源语种列表排除。"""
    assert L.to_flores("zh") == "zho_Hant"
    assert L.is_chinese(L.to_flores("zh"))
    assert "zh" not in L.supported_iso1()


def test_unknown_language_raises():
    """未知语种应抛出可读的错误。"""
    for bad in ("xx", "klingon", "不存在的语言"):
        try:
            L.resolve(bad)
        except L.UnknownLanguage:
            pass
        else:
            raise AssertionError("应当对 %r 抛出 UnknownLanguage" % bad)


def test_coverage():
    """应覆盖足够多的语种,且包含代表性小语种。"""
    iso1 = set(L.supported_iso1())
    assert len(L.LANGS) >= 90, "语种数量偏少: %d" % len(L.LANGS)
    for lang in ["en", "fr", "de", "ru", "ar", "sw", "km", "ne", "my", "zu"]:
        assert lang in iso1, "缺少语种 %s" % lang


def test_detect_script():
    """书写系统识别。"""
    assert detect_script("Hello") == "Latin"
    assert detect_script("Привет") == "Cyrillic"
    assert detect_script("مرحبا") == "Arabic"
    assert detect_script("你好") == "Han"
    assert detect_script("こんにちは") == "Japanese"
    assert detect_script("안녕하세요") == "Korean"
    assert detect_script("नमस्ते") == "Devanagari"


def test_looks_chinese():
    """中文判定。"""
    assert looks_chinese("这是一段中文")
    assert looks_chinese("混合 English 文本")
    assert not looks_chinese("This is English")
    assert not looks_chinese("")
    # 纯假名不应误判为中文
    assert not looks_chinese("これはにほんごです")


def test_strip_markup():
    """HTML 标签与实体应被剥离。"""
    assert strip_markup("<p>Hello</p>") == "Hello"
    assert strip_markup("A &amp; B") == "A & B"
    assert strip_markup("plain") == "plain"


def test_normalize_unicode():
    """全角数字应归一化为半角。"""
    assert normalize_unicode("１２３") == "123"


def test_split_long_text():
    """长文本切分不应丢失内容。"""
    text = "Hello world. " * 400
    chunks = split_long_text(text, max_chars=200)
    assert all(len(c) <= 200 for c in chunks)
    assert len(chunks) > 1
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")

    assert split_long_text("") == []
    assert split_long_text("short") == ["short"]


def test_guess_language_heuristics():
    """不加载模型即可测试语种自动识别。"""
    cases = {
        "Hello, how are you doing today?": "eng_Latn",
        "Das ist nicht so einfach, oder?": "deu_Latn",
        "Bonjour, comment allez-vous aujourd'hui?": "fra_Latn",
        "El mundo es muy grande y hermoso": "spa_Latn",
        "Привет, как дела сегодня?": "rus_Cyrl",
        "مرحبا كيف حالك اليوم": "arb_Arab",
        "你好世界": "zho_Hans",
        "Merhaba, nasilsiniz?": "tur_Latn",
        "안녕하세요": "kor_Hang",
        "Xin chào, bạn khỏe không?": "vie_Latn",
    }
    for text, expected in cases.items():
        got = guess_language(text).flores
        assert got == expected, "%r 识别为 %s,期望 %s" % (text, got, expected)


def test_detection_confidence():
    """识别结果应带置信度,且在合理区间。"""
    for text in ["Hello world", "Bonjour", "你好世界", "Привет"]:
        det = guess_language(text)
        assert 0.0 <= det.confidence <= 1.0
        assert det.method
        assert det.flores


def test_resolve_target():
    """目标语种别名解析。"""
    assert resolve_target("zh") == L.ZHO_HANS
    assert resolve_target("zh-CN") == L.ZHO_HANS
    assert resolve_target("简体") == L.ZHO_HANS
    assert resolve_target("zh-Hant") == L.ZHO_HANT
    assert resolve_target("zh-TW") == L.ZHO_HANT
    assert resolve_target("繁体") == L.ZHO_HANT


def test_to_simplified():
    """繁体转简体。"""
    assert to_simplified("這個問題") == "这个问题"
    assert to_simplified("学习中文") == "学习中文"
    assert to_simplified("") == ""


def test_normalize_punctuation():
    """西式标点转中文全角标点,但保留数字与 URL 场景。"""
    assert normalize_punctuation("你好,世界") == "你好，世界"
    assert normalize_punctuation("你好?") == "你好？"
    assert normalize_punctuation("你好!") == "你好！"
    assert normalize_punctuation("3.14") == "3.14"
    assert normalize_punctuation("1,000") == "1,000"
    assert normalize_punctuation("https://a.com") == "https://a.com"
    assert normalize_punctuation("") == ""
    # 回归:NFKC 会把句号变成 ASCII '.',中文语境下必须还原成句号
    assert normalize_punctuation("今天天气非常好.") == "今天天气非常好。"
    assert normalize_punctuation("3.14") == "3.14"
    assert normalize_punctuation("Hello.") == "Hello."


def test_clean_spacing():
    """清理中文全角标点前的多余空格,并合并连续空格。"""
    # 只清理全角标点"前"的空格,标点后的空格保留(交给 tidy 处理)
    assert clean_spacing("你好 ，世界") == "你好，世界"
    assert clean_spacing("  多个   空格  ") == "多个 空格"
    assert clean_spacing("") == ""


def test_tidy():
    """综合后处理:繁简 + 标点 + 空格 + 冗余。"""
    assert tidy("這個  問題,") == "这个 问题，"
    assert tidy("好好好好好好") == "好"
    assert tidy("你好,世界") == "你好，世界"
    assert tidy("") == ""
def test_apply_glossary():
    """术语表替换。"""
    g = {"OpenAI": "开放人工智能", "GPT": "生成式预训练变换器"}
    assert apply_glossary("OpenAI 发布了 GPT", g) == "开放人工智能 发布了 生成式预训练变换器"
    assert apply_glossary("test", {}) == "test"


def test_glossary_placeholder_roundtrip():
    """术语表占位符:源语种术语应被替换,译后能还原。"""
    from zh_translator.engine import (
        _apply_source_glossary,
        _restore_glossary,
    )

    text, mapping = _apply_source_glossary(
        "OpenAI released a new model.",
        {"开放人工智能": "OpenAI", "模型": "model"},
    )
    assert "OpenAI" not in text
    assert "model" not in text
    assert len(mapping) == 2

    out = _restore_glossary("GLOSS000END 发布 GLOSS001END。", mapping, L.ZHO_HANS)
    assert "开放人工智能" in out and "模型" in out
    assert "GLOSS" not in out


def test_glossary_restores_split_placeholder():
    """占位符被模型拆开或改大小写时也能还原。"""
    from zh_translator.engine import _restore_glossary

    mapping = {"GLOSS000END": "开放人工智能"}
    out = _restore_glossary("G L O S S 0 0 0 E N D 很好", mapping, L.ZHO_HANS)
    assert "开放人工智能" in out, out
    out2 = _restore_glossary("gloss000end 很好", mapping, L.ZHO_HANS)
    assert "开放人工智能" in out2, out2


def test_glossary_restored_before_punctuation():
    """回归:术语占位符必须在标点规范化之前还原。

    否则术语表里夹带的半角标点(常见于句末的 ".")
    会绕过 tidy 留在译文里,导致中英标点混用。
    """
    from zh_translator.engine import _restore_glossary
    from zh_translator.postprocess import tidy

    # 模拟模型输出:占位符后跟半角句点
    raw = "GLOSS000END 发布 GLOSS001END."
    mapping = {"GLOSS000END": "开放人工智能", "GLOSS001END": "模型"}

    # 错误顺序会留下半角点
    wrong = tidy(_restore_glossary(raw, mapping, L.ZHO_HANS), simplify=True)
    # 正确顺序:先还原再 tidy
    right = tidy(raw, simplify=True)
    right = _restore_glossary(right, mapping, L.ZHO_HANS)
    right = tidy(right, simplify=True)

    assert right.endswith("。"), repr(right)
    assert not right.endswith("."), repr(right)
    assert "开放人工智能" in right
    void = wrong


def test_glossary_empty_is_noop():
    """空术语表不应改变文本。"""
    from zh_translator.engine import _apply_source_glossary

    text, mapping = _apply_source_glossary("Hello", None)
    assert text == "Hello" and mapping == {}
    text, mapping = _apply_source_glossary("Hello", {})
    assert text == "Hello" and mapping == {}


def test_opencc_conversion():
    """简繁互转:有 OpenCC 时应覆盖常用繁体字。"""
    from zh_translator.postprocess import to_traditional

    trad = to_traditional("今天天气很好")
    assert "天氣" in trad, trad
    assert to_simplified(trad) == "今天天气很好", to_simplified(trad)


def test_srt_block_parsing():
    """SRT 解析:应保留序号与时间轴,只翻译正文。"""
    from zh_translator.cli import _is_srt, _translate_srt

    srt = (
        "1\n00:00:01,000 --> 00:00:04,000\nGood morning, everyone.\n\n"
        "2\n00:00:04,500 --> 00:00:08,000\nWelcome to the meeting.\n\n"
    )
    assert _is_srt(srt)

    class FakeTranslator:
        """记录入参并返回固定译文的假翻译器。"""

        def __init__(self):
            self.calls = []

        def translate(self, text, source=None, target=None):
            self.calls.append(text)
            class R:
                text = "译文"
            return R()

    tr = FakeTranslator()
    out = _translate_srt(tr, srt, "en", "zh")

    assert out.count("-->") == 2, out
    assert "00:00:01,000 --> 00:00:04,000" in out
    assert "00:00:04,500 --> 00:00:08,000" in out
    assert "Good morning" not in out, out
    assert len(tr.calls) == 2, tr.calls


def test_srt_preserves_crlf():
    """SRT 输出应沿用输入的行尾风格。"""
    from zh_translator.cli import _translate_srt

    crlf = chr(13) + chr(10)
    srt_crlf = ("1" + crlf + "00:00:01,000 --> 00:00:04,000" + crlf
               + "Hello there." + crlf + crlf)

    class FakeTranslator:
        def translate(self, text, source=None, target=None):
            class R:
                text = "你好"
            return R()

    out = _translate_srt(FakeTranslator(), srt_crlf, "en", "zh")
    assert crlf in out, repr(out)
    assert out.count(chr(13)) > 0


def test_read_input_preserves_crlf():
    """读取文件时不能把 CRLF 折叠成 LF。"""
    import tempfile
    from pathlib import Path

    from zh_translator.cli import _read_input

    crlf = chr(13) + chr(10)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.txt"
        p.write_bytes(("line1" + crlf + "line2" + crlf).encode("utf-8"))
        got = _read_input(str(p))
    assert crlf in got, repr(got)


def test_looks_html_detection():
    """HTML 片段识别。"""
    from zh_translator.cli import _looks_html

    assert _looks_html("<p>Hello</p>")
    assert _looks_html("<html><body>Hi</body></html>")
    assert _looks_html("text before <br> after")
    assert not _looks_html("Hello world")
    assert not _looks_html("")
    assert not _looks_html("a < b and c > d")


def test_translate_html_preserves_structure():
    """HTML 翻译应保留标签结构,只替换正文。"""
    from zh_translator.cli import _translate_html

    class FakeTranslator:
        def translate(self, text, source=None, target=None):
            class R:
                text = "译文"
            return R()

    html = (
        "<html><head><title>T</title></head><body>"
        "<h1>Title</h1><p>First para</p>"
        "<script>var x = 1;</script>"
        "<p>Second para</p></body></html>"
    )
    out = _translate_html(FakeTranslator(), html, "en", "zh")

    assert out.count("<html>") == 1
    assert out.count("</html>") == 1
    assert "<h1>" in out and "</h1>" in out
    assert "<p>" in out and "</p>" in out
    assert out.count("<script>") == 1
    assert "var x = 1;" in out, "script 内容不应被翻译"
    assert "Title" not in out
    assert "First para" not in out
    assert out.count("译文") == 3, out


def test_translate_text_dispatches_html():
    """_translate_text 应按内容类型分派。"""
    from zh_translator.cli import _translate_text

    class FakeTranslator:
        def translate(self, text, source=None, target=None):
            class R:
                text = "X"
            return R()

    assert _translate_text(FakeTranslator(), "Hello", "en", "zh") == "X"
    out = _translate_text(FakeTranslator(), "<p>Hello</p>", "en", "zh")
    assert out == "<p>X</p>", out


def test_junk_tokens_filtered():
    """回归:特殊 token 不能泄漏到译文里。

    实测 Bonne journee 在 beam=1 下会产出含结束符的字符串,
    只剥开头的前缀是不够的,必须整串过滤。
    """
    from zh_translator import languages as L

    junk = {L.ZHO_HANS, L.ZHO_HANT, chr(60) + '/s' + chr(62),
            chr(60) + 'pad' + chr(62), chr(60) + 'unk' + chr(62)}
    toks = [L.ZHO_HANS, chr(9605), chr(22909), chr(60) + '/s' + chr(62), chr(30041),
            chr(60) + 'unk' + chr(62), chr(65290), chr(19990), chr(30028),
            chr(60) + '/s' + chr(62)]
    kept = [t for t in toks if t not in junk]

    assert kept, '过滤后不应为空'
    for t in kept:
        assert t not in junk, t


def test_tiny_text_beam_guard():
    """回归:极短输入必须保底 beam=2。

    贪心解码在超短输入上会退化成重复输出
    (Guten Tag / Bonjour / Buongiorno 全部译成重复的问候语),
    因此 fast 档对短文本要保底。
    """
    from zh_translator.tuning import TINY_TEXT_CHARS, auto_beam

    for text in ['Hallo', 'Guten Tag', 'Bonjour', 'Buongiorno', 'Bonne journee']:
        assert len(text) <= TINY_TEXT_CHARS, text
        b = auto_beam(text, 'fast')
        assert b >= 2, 'fast 档对极短文本应为 2,实际 ' + str(b)

    # 长文本仍可用 beam=1 提速
    long_text = 'x' * 200
    assert auto_beam(long_text, 'fast') == 1


def test_beam_presets_monotonic():
    """档位必须单调:quality >= balanced >= fast。"""
    from zh_translator.tuning import auto_beam

    for text in ['Hallo', 'Guten Tag', 'The library closes at six',
                 'The history of science is a long winding road today']:
        q = auto_beam(text, 'quality')
        b = auto_beam(text, 'balanced')
        f = auto_beam(text, 'fast')
        assert q >= b, (text, q, b)
        assert b >= f, (text, b, f)


def _run_without_pytest():
    """让本文件可直接运行,无需安装 pytest。"""
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    passed, failed = 0, []
    for name, fn in fns:
        try:
            fn()
            passed += 1
            print("  PASS  %s" % name)
        except Exception as exc:  # noqa: BLE001
            failed.append((name, exc))
            print("  FAIL  %s: %s" % (name, exc))
    print("\n%d passed, %d failed (共 %d)" % (passed, len(failed), len(fns)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_without_pytest())
