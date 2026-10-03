"""zh-translator:多语种(含小语种) -> 简体中文翻译工具。

快速开始::

    from zh_translator import Translator

    tr = Translator()                          # 自动选 CPU/CUDA,int8 量化
    print(tr.translate("Hello world").text)            # 你好,世界
    print(tr.translate("こんにちは", source="ja").text)  # 你好
    print(tr.translate("Xin chào").source_lang)         # vie_Latn(自动识别)
"""

from . import languages, postprocess
from .detect import (
    Detection,
    detect_script,
    guess_language,
    looks_chinese,
    normalize_unicode,
    strip_markup,
)
from .engine import (
    MAX_CHARS,
    TranslationError,
    TranslationResult,
    Translator,
    resolve_target,
    split_long_text,
)
from .languages import (
    LANGS,
    UnknownLanguage,
    supported_iso1,
    supported_zh_names,
    to_flores,
)

__version__ = "1.0.0"

__all__ = [
    "Translator",
    "TranslationError",
    "TranslationResult",
    "Detection",
    "guess_language",
    "detect_script",
    "looks_chinese",
    "normalize_unicode",
    "strip_markup",
    "split_long_text",
    "resolve_target",
    "languages",
    "postprocess",
    "LANGS",
    "UnknownLanguage",
    "to_flores",
    "supported_iso1",
    "supported_zh_names",
    "MAX_CHARS",
    "__version__",
]
