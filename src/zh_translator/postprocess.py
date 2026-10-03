"""中文后处理:标点规范、简繁统一、术语替换、冗余清理。

NLLB 输出的中文偶尔存在西式标点混用、冗余空白等问题,
本模块在不改变语义的前提下做规范化,提升成品观感。
"""

from __future__ import annotations

import re

# 简繁转换:优先使用 OpenCC(覆盖全部字表与词汇级转换),
# 未安装时回退到内置常用字表。
try:
    from opencc import OpenCC

    _S2T = OpenCC("s2t")
    _T2S_CC = OpenCC("t2s")
except Exception:  # pragma: no cover - OpenCC 为可选依赖
    _S2T = None
    _T2S_CC = None

    # 内置回退表:仅覆盖最常见的繁体字
    _T2S = {
        "說": "说", "話": "话", "這": "这", "個": "个", "們": "们", "時": "时",
        "會": "会", "來": "来", "對": "对", "開": "开", "關": "关", "發": "发",
        "產": "产", "業": "业", "電": "电", "車": "车", "門": "门", "問": "问",
        "題": "题", "長": "长", "東": "东", "書": "书", "見": "见",
        "聞": "闻", "語": "语", "讀": "读", "寫": "写", "學": "学", "國": "国",
        "園": "园", "圓": "圆", "圖": "图", "團": "团", "壓": "压",
        "壞": "坏", "態": "态", "應": "应", "該": "该", "樣": "样", "種": "种",
        "類": "类", "義": "义", "習": "习", "樂": "乐", "歲": "岁",
        "歷": "历", "氣": "气", "決": "决", "點": "点", "無": "无",
        "熱": "热", "為": "为", "與": "与", "專": "专", "絲": "丝",
    }


def to_simplified(text: str) -> str:
    """繁体转简体。优先走 OpenCC,保证字表完整。"""
    if not text:
        return text
    if _T2S_CC is not None:
        return _T2S_CC.convert(text)
    return "".join(_T2S.get(ch, ch) for ch in text)


def to_traditional(text: str) -> str:
    """简体转繁体。"""
    if not text:
        return text
    if _S2T is not None:
        return _S2T.convert(text)
    return text


# 西式标点 -> 中文全角标点(仅在中文语境中替换)
_PUNCT_MAP = {
    ",": "，", ";": "；", ":": "：", "!": "！", "?": "？",
    "(": "（", ")": "）",
}

# 常见中英混排空格规整
_SPACE_CN = re.compile(r"[ \t]+([，。！？；：）】》」』])")
_SPACE_CN_HEAD = re.compile(r"([（【《「『])[ \t]+")
_REPEAT_PUNCT = re.compile(r"([，。！？；：])\1{1,}")
_REPEAT_CHAR = re.compile(r"(.)\1{3,}")


def _is_cjk(ch: str) -> bool:
    """判断是否为中日韩表意文字或中文标点区。"""
    cp = ord(ch) if ch else 0
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0xF900 <= cp <= 0xFAFF
        or 0x3000 <= cp <= 0x303F
    )


def normalize_punctuation(text: str) -> str:
    """把西式标点转换为中文全角标点。

    句号需特殊处理:NLLB 输出的是 U+3002 句号,但本项目的
    normalize_unicode 会先做 NFKC 规范化,把它变成 ASCII 句点。
    因此这里对位于中文语境的句点还原为句号。
    """
    if not text:
        return text
    out = []
    for i, ch in enumerate(text):
        nxt = text[i + 1] if i + 1 < len(text) else ""
        prev = text[i - 1] if i > 0 else ""

        # 句点:中文语境 -> 。;小数点/英文 -> 保留
        if ch == ".":
            if nxt.isdigit() and prev.isdigit():
                out.append(ch)              # 3.14
            elif _is_cjk(prev) or _is_cjk(nxt):
                out.append(chr(0x3002))     # 中文句子结尾
            else:
                out.append(ch)              # Hello.
            continue

        if ch in _PUNCT_MAP:
            if prev.isdigit() and ch == ",":
                out.append(ch)              # 1,000
            elif ch in ":;" and re.match(r"https?$", text[max(0, i - 5):i]):
                out.append(ch)              # https://
            else:
                out.append(_PUNCT_MAP[ch])
        else:
            out.append(ch)
    return "".join(out)


def clean_spacing(text: str) -> str:
    """清理中文标点前后的多余空格。"""
    if not text:
        return text
    text = _SPACE_CN.sub(r"\1", text)
    text = _SPACE_CN_HEAD.sub(r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def tidy(text: str, simplify: bool = True, punct: bool = True) -> str:
    """综合后处理:繁简统一 + 标点规范 + 空格清理 + 冗余去除。"""
    if not text:
        return text
    if simplify:
        text = to_simplified(text)
    if punct:
        text = normalize_punctuation(text)
    text = clean_spacing(text)
    text = _REPEAT_PUNCT.sub(r"\1", text)
    # 去掉明显的重复字符(超过4连)
    text = _REPEAT_CHAR.sub(r"\1", text)
    return text.strip()


def apply_glossary(text: str, glossary: dict) -> str:
    """应用术语表:将 key 替换为 value(支持双向)。"""
    if not text or not glossary:
        return text
    for src, dst in glossary.items():
        if src and dst and src != dst:
            text = text.replace(src, dst)
    return text
