"""中文翻译引擎:多语种(含小语种) -> 简体中文。

技术路线
--------
基座模型: NLLB-200 distilled 系列(Meta,原生支持 200+ 语种)
推理引擎: CTranslate2(int8 量化,CPU 亦可流畅运行,显存占用低)
源语种:   可显式指定,也可由 detect 模块自动识别并给出置信度

为什么选 NLLB-200
-----------------
- 覆盖 200+ 语种,包含大量低资源小语种(斯瓦希里语、齐切瓦语、宿务语等)
- 原生多语种模型,而非"英语枢轴"拼接,小语种质量显著更好
- 600M 版 int8 量化后约 700MB,可在这类 2GB 显存设备上实时运行
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from . import languages as L
from .detect import (
    Detection,
    detect_script,
    guess_language,
    looks_chinese,
    normalize_unicode,
    strip_markup,
)
from .postprocess import apply_glossary, tidy, to_traditional
from .tuning import auto_beam, default_intra_threads

DEFAULT_MODEL_DIR = os.environ.get(
    "ZH_TRANSLATOR_MODEL",
    str(Path(__file__).resolve().parents[2] / "models" / "nllb-zh-int8"),
)

# 单段最大字符数,超过则切分后翻译
MAX_CHARS = 2000
# 目标语种前缀所占 token
_TARGET_PREFIX = 1


class TranslationError(RuntimeError):
    """翻译过程中的可预期错误。"""


# ---------------------------------------------------------------- 句子切分

_SENT_SPLIT = re.compile(r"(?<=[.!?。！？;；\n])\s+")


def split_long_text(text: str, max_chars: int = MAX_CHARS) -> list:
    """把长文本切成不超过 max_chars 的片段。

    切分优先级:换行/句号 -> 逗号 -> 硬切,尽量不破坏语义单元。
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    for part in _SENT_SPLIT.split(text):
        if not part or not part.strip():
            continue
        if len(part) <= max_chars:
            chunks.append(part)
            continue
        for sub in re.split(r"(?<=[,，、;；:])\s*", part):
            if not sub.strip():
                continue
            while len(sub) > max_chars:
                chunks.append(sub[:max_chars])
                sub = sub[max_chars:]
            if sub.strip():
                chunks.append(sub)
    return chunks or [text[:max_chars]]


# ---------------------------------------------------------------- 术语表

# 术语占位符:使用 NLLB 分词器不会拆开的纯数字串
_PLACEHOLDER = "GLOSS{:03d}END"


def _apply_source_glossary(text: str, glossary):
    """把源文本中的术语替换为占位符。

    术语表约定为 {中文译词: 源语种术语},例如
    开放人工智能 对应 OpenAI。翻译前把 OpenAI 换成占位符,
    译回中文后再还原,这样专有名词不会被模型意译。

    返回 (处理后文本, {占位符: 中文译词})。
    """
    if not glossary or not text:
        return text, {}
    mapping = {}
    out = text
    for i, (zh, term) in enumerate(glossary.items()):
        if not zh or not term:
            continue
        term = str(term)
        if term.lower() not in out.lower():
            continue
        ph = _PLACEHOLDER.format(i)
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9 .\-]*", term):
            out = re.sub(re.escape(term), ph, out, flags=re.IGNORECASE)
        else:
            out = out.replace(term, ph)
        mapping[ph] = str(zh)
    return out, mapping


def _restore_glossary(text: str, mapping: dict, target_flores: str) -> str:
    """把占位符还原为中文译词,并按目标语种做简繁处理。"""
    if not text or not mapping:
        return text
    out = text
    for ph, zh in mapping.items():
        value = to_traditional(zh) if target_flores == L.ZHO_HANT else zh
        out = out.replace(ph, value)
        # 容忍模型把占位符拆开或改大小写
        idx = ph[5:8]
        # 逐字符拼接,允许字母与数字之间被空格拆开
        sep = r"\s*"
        pattern = sep.join(re.escape(c) for c in ph) + r"\s*"
        loose = pattern
        out = re.sub(loose, value, out, flags=re.IGNORECASE)
    return out


# ---------------------------------------------------------------- 目标语种

_TARGET_ALIASES = {
    "zh": L.ZHO_HANS, "zh-cn": L.ZHO_HANS, "zh-hans": L.ZHO_HANS,
    "zho": L.ZHO_HANS, "hans": L.ZHO_HANS, "cn": L.ZHO_HANS,
    "简体": L.ZHO_HANS, "简体中文": L.ZHO_HANS, "中文": L.ZHO_HANS,
    "zh-tw": L.ZHO_HANT, "zh-hk": L.ZHO_HANT, "zh-hant": L.ZHO_HANT,
    "zh-mo": L.ZHO_HANT, "hant": L.ZHO_HANT, "繁体": L.ZHO_HANT,
    "繁体中文": L.ZHO_HANT,
}


def resolve_target(target) -> str:
    """把目标语种写法解析为 FLORES 代码。"""
    key = str(target or "zh").strip().lower().replace("_", "-")
    if key in _TARGET_ALIASES:
        return _TARGET_ALIASES[key]
    return L.to_flores(target)


# ---------------------------------------------------------------- 结果对象


@dataclass
class TranslationResult:
    """一次翻译的结果。"""

    text: str                  # 译文
    source_lang: str           # FLORES 源语种代码
    source_lang_zh: str        # 源语种中文名
    detected: bool             # 源语种是否为自动识别
    skipped: bool = False      # 源文本已是中文而跳过
    quality_tier: str = "high" # 源语种资源层级(high/mid/low)
    confidence: float = 1.0    # 语种识别置信度
    note: str = ""             # 提示信息

    def __str__(self) -> str:
        return self.text

    def to_dict(self) -> dict:
        return {
            "translation": self.text,
            "source_lang": self.source_lang,
            "source_lang_zh": self.source_lang_zh,
            "detected": self.detected,
            "skipped": self.skipped,
            "quality_tier": self.quality_tier,
            "confidence": self.confidence,
            "note": self.note,
        }


# ---------------------------------------------------------------- 引擎


class Translator:
    """多语种 -> 简体中文翻译器。

    典型用法::

        tr = Translator()
        tr.translate("Hello world")               # 自动识别 -> 你好,世界
        tr.translate("Bonjour", source="fr")      # 显式指定 -> 你好
        tr.translate_batch([...], source="en")    # 批量
    """

    def __init__(
        self,
        model_dir: Optional[str] = None,
        device: str = "auto",
        compute_type: str = "int8",
        beam_size: int = 4,
        max_batch_size: int = 16,
        postprocess: bool = True,
        intra_threads: int = 0,
        inter_threads: int = 1,
        speed: str = "auto",
    ):
        """初始化翻译器。

        speed: 速度档位,取 auto / fast / balanced / quality。
            fast     贪心解码,约 480 ms/句
            balanced 约 630 ms/句(默认)
            quality  约 960 ms/句
            auto     按机器选线程数,并按文本长度自动调 beam
        intra_threads: OpenMP 线程数,0 表示按物理核心数自动推断。
            超线程对本模型无益,实测 8 逻辑线程比 4 物理线程慢 83%。
        inter_threads: 并发翻译槽位,服务端多请求时调大可提升吞吐。
        """
        self.model_dir = str(model_dir or DEFAULT_MODEL_DIR)
        self.device = device
        self.compute_type = compute_type
        self.speed = speed
        self.beam_size = beam_size
        self.max_batch_size = max_batch_size
        self.postprocess = postprocess
        # intra_threads=0 时按物理核心数推断,而不是交给 OpenMP 默认值
        self.intra_threads = intra_threads or default_intra_threads()
        self.inter_threads = inter_threads
        self._translator = None
        self._tokenizer = None
        self._loaded = False
        self._device = "cpu"

    # ---------------- 模型加载 ----------------

    def load(self) -> "Translator":
        """加载模型(幂等)。"""
        if self._loaded:
            return self

        if not Path(self.model_dir).exists():
            raise TranslationError(
                f"模型目录不存在: {self.model_dir}\n"
                f"请先运行: python scripts/download_model.py"
            )
        try:
            import ctranslate2
            from transformers import AutoTokenizer
        except ImportError as exc:  # pragma: no cover
            raise TranslationError(
                "缺少依赖,请运行: pip install ctranslate2 transformers sentencepiece"
            ) from exc

        device = self.device
        if device == "auto":
            device = "cuda" if self._cuda_available() else "cpu"

        try:
            self._translator = ctranslate2.Translator(
                self.model_dir, device=device, compute_type=self.compute_type,
                intra_threads=self.intra_threads, inter_threads=self.inter_threads,
            )
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        except Exception as exc:
            # 显式指定 CUDA 但运行库不齐(如缺 cuBLAS)时回退到 CPU,
            # 避免整个工具不可用。
            if device == "cuda":
                try:
                    self._translator = ctranslate2.Translator(
                        self.model_dir, device="cpu", compute_type=self.compute_type,
                        intra_threads=self.intra_threads,
                        inter_threads=self.inter_threads,
                    )
                    device = "cpu"
                except Exception:
                    raise TranslationError(f"模型加载失败: {exc}") from exc
            else:
                raise TranslationError(f"模型加载失败: {exc}") from exc

        self._device = device
        self._loaded = True
        return self

    @staticmethod
    def _cuda_available() -> bool:
        """检测 CUDA 是否真正可用。

        仅看 ctranslate2.get_cuda_device_count() 不够:驱动报告了设备,
        但若缺少 cuBLAS 运行库(如 nvidia-cublas-cu12 未安装),真正推理时
        才会抛 "Library cublas64_12.dll is not found"。这里要求 torch 侧
        也能正常初始化 CUDA,作为运行库齐备的旁证。
        """
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() <= 0:
                return False
        except Exception:
            return False
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def runtime_device(self) -> str:
        return self._device

    def _beam_for(self, text: str, speed: Optional[str], explicit) -> int:
        """决定本次翻译使用的 beam 宽度。

        优先级:显式 beam > 请求级 speed > 实例级 speed > 实例 beam_size。
        speed 为 auto 时按文本长度自适应。
        """
        if explicit:
            return int(explicit)
        preset = speed or (None if self.speed == 'auto' else self.speed)
        if preset:
            return auto_beam(text, preset)
        return int(self.beam_size)

    # ---------------- 语种识别 ----------------

    def detect(self, text: str) -> Detection:
        """识别文本语种,返回带置信度的结果(无需加载模型)。"""
        return guess_language(normalize_unicode(strip_markup(text or "")))

    def _resolve_source(self, text: str, source) -> tuple:
        """返回 (LangInfo, detected_flag, confidence)。"""
        if source in (None, "auto", "detect", "自动", ""):
            det = guess_language(text)
            info = L.LANGS.get(det.flores) or L.LANGS["eng_Latn"]
            return info, True, det.confidence
        return L.resolve(source), False, 1.0

    # ---------------- 翻译 ----------------

    def translate(
        self,
        text: str,
        source="auto",
        target: str = "zh",
        beam_size: Optional[int] = None,
        max_tokens: int = 1024,
        skip_if_chinese: bool = True,
        glossary: Optional[dict] = None,
        speed: Optional[str] = None,
    ) -> TranslationResult:
        """把 text 翻译成中文。

        参数
        ----
        text:     待翻译文本,支持 HTML 片段(标签自动剥离)
        source:   源语种,支持 en/eng/eng_Latn/英语/auto,默认自动识别
        target:   目标语种,zh(简体)或 zh-Hant(繁体)
        beam_size: beam 宽度,越大越准越慢;给了则忽略速度档位
        speed:     速度档位,覆盖实例设置
        glossary: 术语表,{中文译词: 源语种术语}。
            源语种术语会在翻译前被替换为占位标记,
            译后再还原为指定中文译词,这是让专有名词稳定输出的可靠做法。
        """
        if not isinstance(text, str):
            raise TranslationError("text 必须是字符串")
        if not text.strip():
            return TranslationResult("", L.ZHO_HANS, "简体中文", False, skipped=True)

        self.load()
        target_flores = resolve_target(target)
        clean = normalize_unicode(strip_markup(text))

        # 术语表:翻译前把源语种术语换成数字占位符,译后再换回中文译词。
        # 直接对译文做字符串替换几乎不会命中,因为模型已把术语意译了。
        clean, placeholder_map = _apply_source_glossary(clean, glossary)

        if not clean.strip():
            return TranslationResult(text, L.ZHO_HANS, "简体中文", False,
                                     skipped=True, note="清理后为空")

        # 源文本已是中文且目标为简体 -> 跳过
        if skip_if_chinese and looks_chinese(clean) and target_flores == L.ZHO_HANS:
            info, detected, conf = self._resolve_source(clean, source)
            return TranslationResult(text, L.ZHO_HANS, "简体中文",
                                     detected, skipped=True, confidence=conf,
                                     note="源文本已是中文")

        info, detected, conf = self._resolve_source(clean, source)
        if L.is_chinese(info.flores) and target_flores == L.ZHO_HANS:
            return TranslationResult(text, info.flores, info.zh_name, detected,
                                     skipped=True, confidence=conf,
                                     note="源语种与目标语种相同")

        chunks = split_long_text(clean)
        # NLLB 的 zho_Hant(繁体)输出质量很差(实测会把 "Hello world" 译成
        # 「您的位置:」),因此统一先译成简体,再用 OpenCC 转繁体。
        decode_target = L.ZHO_HANS if target_flores == L.ZHO_HANT else target_flores
        pieces = self._translate_chunks(
            chunks, info.flores, decode_target,
            self._beam_for(clean, speed, beam_size), max_tokens,
        )
        out = "".join(pieces)
        # 先还原术语占位符,再做标点规范化。
        # 顺序反了的话,术语表里夹带的半角标点(如 ".")会绕过 tidy 留在译文里。
        if placeholder_map:
            out = _restore_glossary(out, placeholder_map, target_flores)
        if self.postprocess:
            out = tidy(out, simplify=True)
            if target_flores == L.ZHO_HANT:
                out = to_traditional(out)

        return TranslationResult(
            text=out, source_lang=info.flores, source_lang_zh=info.zh_name,
            detected=detected, quality_tier=info.resource_tier, confidence=conf,
        )

    def translate_batch(
        self,
        texts: Sequence[str],
        source="auto",
        target: str = "zh",
        beam_size: Optional[int] = None,
        max_tokens: int = 1024,
        glossary: Optional[dict] = None,
        speed: Optional[str] = None,
    ) -> list:
        """批量翻译。

        自动模式下按识别出的源语种分组,以便一次 decode 多条句子。
        """
        if not texts:
            return []
        self.load()
        target_flores = resolve_target(target)
        # 批量场景下按整批最长文本决定 beam,避免同批内质量不一致
        longest = max((len((t or '').strip()) for t in texts), default=0)
        beam = self._beam_for('x' * longest, speed, beam_size)

        # 1) 预处理:清洗 + 术语占位 + 判定语种
        prepared = []
        for raw in texts:
            raw = raw or ""
            clean = normalize_unicode(strip_markup(raw))
            if not clean.strip():
                prepared.append((raw, None, True, 1.0, "skip", {}))
                continue
            # 语种判定要在术语替换之前,占位符会影响功能词统计
            info, detected, conf = self._resolve_source(clean, source)
            gclean, gmap = _apply_source_glossary(clean, glossary)
            if (looks_chinese(clean) and target_flores == L.ZHO_HANS) or (
                L.is_chinese(info.flores) and target_flores == L.ZHO_HANS
            ):
                prepared.append((raw, info, detected, conf, "skip", gmap))
            else:
                prepared.append((raw, info, detected, conf, "translate", gmap))

        # 2) 按源语种分组,展开为待解码片段
        groups: dict = {}
        for idx, (raw, info, detected, conf, action, gmap) in enumerate(prepared):
            if action == "translate":
                gclean, _ = _apply_source_glossary(
                    normalize_unicode(strip_markup(raw)), glossary)
                groups.setdefault(info.flores, []).append(
                    (idx, split_long_text(gclean)))


        # 3) 逐组翻译,组内再按 max_batch_size 限流
        # 繁体同样先走简体再转繁,理由见 translate() 中的说明
        decode_target = L.ZHO_HANS if target_flores == L.ZHO_HANT else target_flores
        outputs: dict = {}
        for src_flores, items in groups.items():
            flat = []
            for orig_idx, chunks in items:
                for c in chunks:
                    flat.append((orig_idx, c))
            for i in range(0, len(flat), self.max_batch_size):
                window = flat[i:i + self.max_batch_size]
                srcs = [c for _, c in window]
                pieces = self._translate_chunks(
                    srcs, src_flores, decode_target, beam, max_tokens
                )
                for orig_idx, piece in zip([o for o, _ in window], pieces):
                    outputs.setdefault(orig_idx, []).append(piece)

        # 4) 组装结果
        results = []
        for idx, (raw, info, detected, conf, action, gmap) in enumerate(prepared):
            if action == "skip":
                results.append(TranslationResult(
                    raw,
                    info.flores if info else L.ZHO_HANS,
                    info.zh_name if info else "简体中文",
                    detected, skipped=True, confidence=conf,
                    note="源文本已是中文",
                ))
                continue
            out = "".join(outputs.get(idx, []))
            # 同样先还原术语再做标点规范化,理由见 translate() 中的说明
            if gmap:
                out = _restore_glossary(out, gmap, target_flores)
            if self.postprocess:
                out = tidy(out, simplify=True)
                if target_flores == L.ZHO_HANT:
                    out = to_traditional(out)
            results.append(TranslationResult(
                out, info.flores, info.zh_name, detected,
                quality_tier=info.resource_tier, confidence=conf,
            ))
        return results

    # ---------------- 内部实现 ----------------

    def _translate_chunks(
        self, chunks, src: str, tgt: str, beam_size: int, max_tokens: int
    ) -> list:
        """对同一源语种的多个片段做批量解码。"""
        chunks = [c for c in chunks if c and c.strip()]
        if not chunks:
            return []
        # NLLB 的源语种 token 由 prefix_tokens 决定。
        # 直接给 tokenizer.src_lang 赋值只改属性,不会刷新 prefix_tokens,
        # 会导致整批文本沿用上一种语言,进而抛出
        # "One input stream has less examples than the others"。
        # 必须调用 set_src_lang_special_tokens 重新计算。
        tok = self._tokenizer
        if getattr(tok, "src_lang", None) != src:
            tok.set_src_lang_special_tokens(src)
        encoded = [
            tok.convert_ids_to_tokens(tok.encode(c, add_special_tokens=True))
            for c in chunks
        ]
        results = self._translator.translate_batch(
            encoded,
            # target_prefix 必须与 batch 中样本数一致,否则 CTranslate2 会报
            # "One input stream has less examples than the others"。
            target_prefix=[[tgt] for _ in encoded],
            beam_size=max(1, beam_size),
            max_decoding_length=max(_TARGET_PREFIX + 8, max_tokens),
            replace_unknowns=True,
        )
        out = []
        # 目标语种前缀 token、结束符、填充符都不该出现在译文里。
        # 只剥开头是不够的:实测 Bonne journee 在 beam=1 下会产出
        # 含 </s> 的字符串,即结束符出现在序列中间,必须整串过滤。
        junk = {tgt, L.ZHO_HANS, L.ZHO_HANT, '</s>', '<pad>', '<unk>'}
        for r in results:
            toks = [t for t in r.hypotheses[0] if t not in junk]
            out.append(self._tokenizer.convert_tokens_to_string(toks).strip())
        return out
