"""语种元数据:ISO 639-1/639-3 映射、中文名称、书写系统。

NLLB-200 使用 FLORES-200 风格的语种代码(多数为 ISO 639-3)。
本模块统一对外暴露 ISO 639-1(用户最熟悉)与内部 FLORES 代码,
并提供源语种自动识别所需的书写系统信息。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 中文目标语种在 FLORES-200 中的代码
ZHO_HANS = "zho_Hans"
ZHO_HANT = "zho_Hant"
CHINESE_CODES = (ZHO_HANS, ZHO_HANT)


@dataclass(frozen=True)
class LangInfo:
    """单个源语种的静态元数据。"""

    flores: str      # FLORES-200 / NLLB 代码,如 "pes_Arab"
    iso1: str        # ISO 639-1 两字母代码,如 "fa"
    iso3: str        # ISO 639-3 三字母代码,如 "pes"
    zh_name: str     # 简体中文名称
    en_name: str     # 英文名称
    script: str      # 主要书写系统,如 Latn / Cyrl / Arab / Hani
    family: str      # 语系,如 "Indo-European"
    resource_tier: str = "low"   # high / mid / low,提示小语种质量
    aliases: tuple = field(default_factory=tuple)


def _L(*args, **kwargs) -> LangInfo:
    return LangInfo(*args, **kwargs)


# 覆盖 100+ 源语种:主流大语种 + 大量小语种/低资源语种。
# resource_tier: high=平行语料充足(质量最好), mid=中等, low=低资源(质量受限)
_ENTRIES = [
    # ---------- 印欧语系 ----------
    _L("eng_Latn", "en", "eng", "英语", "English", "Latn", "Indo-European", "high"),
    _L("fra_Latn", "fr", "fra", "法语", "French", "Latn", "Indo-European", "high"),
    _L("deu_Latn", "de", "deu", "德语", "German", "Latn", "Indo-European", "high"),
    _L("spa_Latn", "es", "spa", "西班牙语", "Spanish", "Latn", "Indo-European", "high"),
    _L("por_Latn", "pt", "por", "葡萄牙语", "Portuguese", "Latn", "Indo-European", "high"),
    _L("ita_Latn", "it", "ita", "意大利语", "Italian", "Latn", "Indo-European", "high"),
    _L("rus_Cyrl", "ru", "rus", "俄语", "Russian", "Cyrl", "Indo-European", "high"),
    _L("ukr_Cyrl", "uk", "ukr", "乌克兰语", "Ukrainian", "Cyrl", "Indo-European", "mid"),
    _L("bel_Cyrl", "be", "bel", "白俄罗斯语", "Belarusian", "Cyrl", "Indo-European", "mid"),
    _L("pol_Latn", "pl", "pol", "波兰语", "Polish", "Latn", "Indo-European", "mid"),
    _L("ces_Latn", "cs", "ces", "捷克语", "Czech", "Latn", "Indo-European", "mid"),
    _L("slk_Latn", "sk", "slk", "斯洛伐克语", "Slovak", "Latn", "Indo-European", "mid"),
    _L("nld_Latn", "nl", "nld", "荷兰语", "Dutch", "Latn", "Indo-European", "mid"),
    _L("ron_Latn", "ro", "ron", "罗马尼亚语", "Romanian", "Latn", "Indo-European", "mid"),
    _L("hrv_Latn", "hr", "hrv", "克罗地亚语", "Croatian", "Latn", "Indo-European", "mid"),
    _L("srp_Cyrl", "sr", "srp", "塞尔维亚语", "Serbian", "Cyrl", "Indo-European", "mid"),
    _L("swe_Latn", "sv", "swe", "瑞典语", "Swedish", "Latn", "Indo-European", "mid"),
    _L("dan_Latn", "da", "dan", "丹麦语", "Danish", "Latn", "Indo-European", "mid"),
    _L("nor_Latn", "no", "nor", "挪威语", "Norwegian", "Latn", "Indo-European", "mid"),
    _L("nob_Latn", "nb", "nob", "书面挪威语", "Norwegian Bokmal", "Latn", "Indo-European", "mid"),
    _L("nno_Latn", "nn", "nno", "新挪威语", "Norwegian Nynorsk", "Latn", "Indo-European", "low"),
    _L("isl_Latn", "is", "isl", "冰岛语", "Icelandic", "Latn", "Indo-European", "low",
       aliases=("ice",)),
    _L("ell_Grek", "el", "ell", "希腊语", "Greek", "Grek", "Indo-European", "mid",
       aliases=("gre",)),
    _L("fin_Latn", "fi", "fi", "芬兰语", "Finnish", "Latn", "Uralic", "mid"),
    _L("hun_Latn", "hu", "hu", "匈牙利语", "Hungarian", "Latn", "Uralic", "mid"),
    _L("est_Latn", "et", "et", "爱沙尼亚语", "Estonian", "Latn", "Uralic", "low"),
    _L("lav_Latn", "lv", "lv", "拉脱维亚语", "Latvian", "Latn", "Indo-European", "low"),
    _L("lit_Latn", "lt", "lt", "立陶宛语", "Lithuanian", "Latn", "Indo-European", "low"),
    _L("slv_Latn", "sl", "slv", "斯洛文尼亚语", "Slovenian", "Latn", "Indo-European", "low"),
    _L("tur_Latn", "tr", "tr", "土耳其语", "Turkish", "Latn", "Indo-European", "mid"),
    _L("sqi_Latn", "sq", "sqi", "阿尔巴尼亚语", "Albanian", "Latn", "Indo-European", "low"),
    _L("mlt_Latn", "mt", "mlt", "马耳他语", "Maltese", "Latn", "Afro-Asiatic", "low"),
    _L("cat_Latn", "ca", "cat", "加泰罗尼亚语", "Catalan", "Latn", "Indo-European", "mid"),
    _L("eus_Latn", "eu", "eus", "巴斯克语", "Basque", "Latn", "Isolate", "low"),
    _L("glg_Latn", "gl", "glg", "加利西亚语", "Galician", "Latn", "Indo-European", "low"),
    _L("mkd_Cyrl", "mk", "mkd", "马其顿语", "Macedonian", "Cyrl", "Indo-European", "low"),
    _L("hin_Deva", "hi", "hin", "印地语", "Hindi", "Deva", "Indo-European", "high"),
    _L("ben_Beng", "bn", "ben", "孟加拉语", "Bengali", "Beng", "Indo-European", "mid"),
    _L("pan_Guru", "pa", "pan", "旁遮普语", "Punjabi", "Guru", "Indo-European", "mid"),
    _L("guj_Gujr", "gu", "guj", "古吉拉特语", "Gujarati", "Gujr", "Indo-European", "mid"),
    _L("mar_Deva", "mr", "mar", "马拉地语", "Marathi", "Deva", "Indo-European", "mid"),
    _L("nep_Deva", "ne", "nep", "尼泊尔语", "Nepali", "Deva", "Indo-European", "mid"),
    _L("sin_Sinh", "si", "sin", "僧伽罗语", "Sinhala", "Sinh", "Indo-European", "low"),
    _L("tam_Taml", "ta", "tam", "泰米尔语", "Tamil", "Taml", "Dravidian", "mid"),
    _L("tel_Telu", "te", "tel", "泰卢固语", "Telugu", "Telu", "Dravidian", "mid"),
    _L("kan_Knda", "kn", "kn", "卡纳达语", "Kannada", "Knda", "Dravidian", "mid"),
    _L("mal_Mlym", "ml", "ml", "马拉雅拉姆语", "Malayalam", "Mlym", "Dravidian", "mid"),
    _L("fas_Arab", "fa", "fas", "波斯语", "Persian", "Arab", "Indo-European", "mid",
       aliases=("per", "pes")),
    _L("urd_Arab", "ur", "urd", "乌尔都语", "Urdu", "Arab", "Indo-European", "mid"),
    _L("pus_Arab", "ps", "pus", "普什图语", "Pashto", "Arab", "Indo-European", "low"),
    # ---------- 闪米特语系 ----------
    _L("arb_Arab", "ar", "arb", "阿拉伯语", "Arabic", "Arab", "Afro-Asiatic", "high",
       aliases=("ara",)),
    _L("heb_Hebr", "he", "heb", "希伯来语", "Hebrew", "Hebr", "Afro-Asiatic", "mid",
       aliases=("iw",)),
    _L("amh_Ethi", "am", "amh", "阿姆哈拉语", "Amharic", "Ethi", "Afro-Asiatic", "low",
       aliases=("tir",)),
    _L("tir_Ethi", "ti", "tir", "提格雷尼亚语", "Tigrinya", "Ethi", "Afro-Asiatic", "low"),
    # ---------- 高加索、欧洲小语种 ----------
    _L("hye_Armn", "hy", "hye", "亚美尼亚语", "Armenian", "Armn", "Indo-European", "mid"),
    _L("kat_Geor", "ka", "kat", "格鲁吉亚语", "Georgian", "Geor", "Kartvelian", "mid"),
    # ---------- 阿尔泰语系 ----------
    _L("azj_Latn", "az", "azj", "阿塞拜疆语", "Azerbaijani", "Latn", "Turkic", "mid",
       aliases=("aze",)),
    _L("kkj_Latn", "kk", "kkj", "哈萨克语", "Kazakh", "Latn", "Turkic", "mid",
       aliases=("kaz",)),
    _L("kyr_Cyrl", "ky", "kyr", "吉尔吉斯语", "Kyrgyz", "Cyrl", "Turkic", "low",
       aliases=("kir",)),
    _L("uzn_Latn", "uz", "uzn", "乌兹别克语", "Uzbek", "Latn", "Turkic", "mid",
       aliases=("uzb",)),
    _L("tuk_Latn", "tk", "tuk", "土库曼语", "Turkmen", "Latn", "Turkic", "low"),
    _L("bak_Cyrl", "ba", "bak", "巴什基尔语", "Bashkir", "Cyrl", "Turkic", "low"),
    _L("tat_Cyrl", "tt", "tat", "塔塔尔语", "Tatar", "Cyrl", "Turkic", "low"),
    _L("uig_Arab", "ug", "uig", "维吾尔语", "Uyghur", "Arab", "Turkic", "mid"),
    _L("crh_Latn", "crh", "crh", "克里米亚鞑靼语", "Crimean Tatar", "Latn", "Turkic", "low"),
    # ---------- 补充:detect 可产出但此前未收录 ----------
    _L("bul_Cyrl", "bg", "bul", "保加利亚语", "Bulgarian", "Cyrl", "Indo-European", "mid"),
    _L("kaz_Cyrl", "kk", "kaz", "哈萨克语(西里尔)", "Kazakh Cyrillic", "Cyrl", "Turkic", "mid"),
    _L("tgk_Cyrl", "tg", "tgk", "塔吉克语(西里尔)", "Tajik Cyrillic", "Cyrl", "Iranian", "mid"),
    _L("kir_Cyrl", "ky", "kir", "吉尔吉斯语(西里尔)", "Kyrgyz Cyrillic", "Cyrl", "Turkic", "low"),
    _L("rom_Latn", "ro", "rom", "罗马尼亚语", "Romanian", "Latn", "Indo-European", "mid"),
    _L("bos_Latn", "bs", "bos", "波斯尼亚语", "Bosnian", "Latn", "Indo-European", "mid"),
    _L("srp_Latn", "sr", "srp", "塞尔维亚语(拉丁)", "Serbian Latin", "Latn", "Indo-European", "mid"),
    _L("gle_Latn", "ga", "gle", "爱尔兰语", "Irish", "Latn", "Celtic", "low"),
    _L("kat_Latn", "ka", "kat", "格鲁吉亚语(拉丁)", "Georgian Latin", "Latn", "Kartvelian", "mid"),
    _L("asm_Beng", "as", "asm", "阿萨姆语", "Assamese", "Beng", "Indo-European", "low"),
    _L("ori_Orya", "or", "ori", "奥里亚语", "Odia", "Orya", "Indo-European", "low"),
    _L("bho_Deva", "bh", "bho", "博杰普尔语", "Bhojpuri", "Deva", "Indo-European", "low"),
    _L("mai_Deva", "mai", "mai", "迈蒂利语", "Maithili", "Deva", "Indo-European", "low"),
    _L("san_Deva", "sa", "san", "梵语", "Sanskrit", "Deva", "Indo-European", "low"),
    _L("sna_Latn", "sn", "sna", "修纳语", "Shona", "Latn", "Niger-Congo", "mid"),
    _L("tgk_Latn", "tg", "tgk", "塔吉克语", "Tajik", "Latn", "Iranian", "mid"),
    _L("kon_Latn", "kg", "kon", "刚果语", "Kongo", "Latn", "Niger-Congo", "low"),
    # ---------- 东亚:中日韩 ----------
    _L("jpn_Jpan", "ja", "jpn", "日语", "Japanese", "Jpan", "Japonic", "high"),
    _L("kor_Hang", "ko", "kor", "韩语", "Korean", "Hang", "Koreanic", "high"),
    # ---------- 汉藏语系 ----------
    _L("bod_Tibt", "bo", "bod", "藏语", "Tibetan", "Tibt", "Sino-Tibetan", "low"),
    _L("dzo_Tibt", "dz", "dzo", "不丹语", "Dzongkha", "Tibt", "Sino-Tibetan", "low"),
    # ---------- 南亚、东南亚 ----------
    _L("ind_Latn", "id", "ind", "印尼语", "Indonesian", "Latn", "Austronesian", "mid"),
    _L("msa_Latn", "ms", "msa", "马来语", "Malay", "Latn", "Austronesian", "mid"),
    _L("tgl_Latn", "tl", "tgl", "他加禄语", "Tagalog", "Latn", "Austronesian", "mid"),
    _L("ceb_Latn", "ceb", "ceb", "宿务语", "Cebuano", "Latn", "Austronesian", "low"),
    _L("ilo_Latn", "ilo", "ilo", "伊洛卡诺语", "Ilocano", "Latn", "Austronesian", "low"),
    _L("jav_Latn", "jv", "jav", "爪哇语", "Javanese", "Latn", "Austronesian", "low"),
    _L("sun_Latn", "su", "sun", "巽他语", "Sundanese", "Latn", "Austronesian", "low"),
    _L("tha_Thai", "th", "tha", "泰语", "Thai", "Thai", "Kra-Dai", "mid"),
    _L("lao_Laoo", "lo", "lao", "老挝语", "Lao", "Laoo", "Kra-Dai", "low"),
    _L("khm_Khmr", "km", "khm", "高棉语", "Khmer", "Khmr", "Austroasiatic", "low"),
    _L("mya_Mymr", "my", "mya", "缅甸语", "Burmese", "Mymr", "Sino-Tibetan", "low",
       aliases=("bur",)),
    _L("vie_Latn", "vi", "vie", "越南语", "Vietnamese", "Latn", "Austroasiatic", "mid"),
    # ---------- 非洲语言 ----------
    _L("swa_Latn", "sw", "swa", "斯瓦希里语", "Swahili", "Latn", "Niger-Congo", "mid"),
    _L("hau_Latn", "ha", "hau", "豪萨语", "Hausa", "Latn", "Afro-Asiatic", "mid"),
    _L("yor_Latn", "yo", "yor", "约鲁巴语", "Yoruba", "Latn", "Niger-Congo", "mid"),
    _L("ful_Latn", "ff", "ful", "富拉尼语", "Fula", "Latn", "Niger-Congo", "low"),
    _L("bam_Latn", "bm", "bam", "班巴拉语", "Bambara", "Latn", "Niger-Congo", "low"),
    _L("wol_Latn", "wo", "wol", "沃洛夫语", "Wolof", "Latn", "Niger-Congo", "low"),
    _L("tso_Latn", "ts", "tso", "聪加语", "Tsonga", "Latn", "Niger-Congo", "low"),
    _L("ssw_Latn", "ss", "ssw", "斯威士语", "Swati", "Latn", "Niger-Congo", "low"),
    _L("nya_Latn", "ny", "nya", "齐切瓦语", "Chichewa", "Latn", "Niger-Congo", "low"),
    _L("run_Latn", "rn", "run", "卢安达语", "Kinyarwanda", "Latn", "Niger-Congo", "low"),
    _L("lin_Latn", "ln", "lin", "林加拉语", "Lingala", "Latn", "Niger-Congo", "low"),
    _L("lug_Latn", "lg", "lug", "卢刚达语", "Luganda", "Latn", "Niger-Congo", "low"),
    _L("umb_Latn", "um", "umb", "翁本杜语", "Umbundu", "Latn", "Niger-Congo", "low"),
    _L("zul_Latn", "zu", "zul", "祖鲁语", "Zulu", "Latn", "Niger-Congo", "mid"),
    _L("xho_Latn", "xh", "xho", "科萨语", "Xhosa", "Latn", "Niger-Congo", "mid"),
    _L("afr_Latn", "af", "afr", "南非荷兰语", "Afrikaans", "Latn", "Indo-European", "mid"),
    # ---------- 美洲及其他 ----------
    _L("que_Latn", "qu", "que", "克丘亚语", "Quechua", "Latn", "Quechuan", "low"),
    _L("aym_Latn", "ay", "aym", "艾马拉语", "Aymara", "Latn", "Aymaran", "low"),
    _L("gnu_Latn", "gn", "gnu", "瓜拉尼语", "Guarani", "Latn", "Tupian", "low"),
    _L("hat_Latn", "ht", "ht", "海地克里奥尔语", "Haitian Creole", "Latn", "French", "low"),
    _L("kal_Latn", "kl", "kal", "格陵兰语", "Kalaallisut", "Latn", "Eskimo-Aleut", "low"),
    _L("grn_Latn", "gn", "grn", "瓜拉尼语(克里奥尔)", "Guarani Creole", "Latn", "Creole",
       "low", aliases=("gcr",)),
    # ---------- 繁体中文源(港台) ----------
    _L(ZHO_HANT, "zh", "zho", "繁体中文", "Traditional Chinese", "Hant", "Sino-Tibetan",
       "high"),
]

# FLORES 代码 -> LangInfo(自动去重,后定义的覆盖先定义的)
LANGS: dict[str, LangInfo] = {}
for _info in _ENTRIES:
    LANGS[_info.flores] = _info


def _build_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for flores, info in LANGS.items():
        keys = {
            flores, flores.lower(), flores.split("_")[0], flores.split("_")[0].lower(),
            info.iso1, info.iso1.lower(), info.iso3, info.iso3.lower(),
            info.en_name.lower(), info.zh_name,
        }
        keys.update(a.lower() for a in info.aliases)
        for k in keys:
            if k:
                index.setdefault(k, flores)
    return index


_ALIAS_INDEX: dict[str, str] = _build_index()


class UnknownLanguage(ValueError):
    """请求了不支持的语种。"""


def resolve(code) -> LangInfo:
    """把任意常见写法解析为 LangInfo。

    支持 en / eng / eng_Latn / English / 英语 等形式。
    None 或 auto 抛错,由上层走自动检测。
    """
    if code is None:
        raise UnknownLanguage("未指定语种")
    key = str(code).strip()
    if not key or key.lower() in {"auto", "detect", "自动"}:
        raise UnknownLanguage("需要自动语种检测")
    found = _ALIAS_INDEX.get(key) or _ALIAS_INDEX.get(key.lower())
    if found is None:
        raise UnknownLanguage(
            "不支持的语种: %r。共支持 %d 种,例如 %s ..."
            % (code, len(LANGS), ", ".join(supported_iso1()[:20]))
        )
    return LANGS[found]


def to_flores(code) -> str:
    """解析任意语种写法为 FLORES-200 代码。"""
    return resolve(code).flores


def is_chinese(flores: str) -> bool:
    """判断 FLORES 代码是否为中文。"""
    return flores in CHINESE_CODES


def supported_iso1() -> list:
    """返回所有支持的 ISO 639-1 代码(去重,排除中文)。"""
    out = set()
    for info in LANGS.values():
        if is_chinese(info.flores) or info.iso1 == "zh":
            continue
        out.add(info.iso1)
    return sorted(out)


def supported_zh_names() -> list:
    """返回所有支持语种的中文名称(去重)。"""
    return sorted({info.zh_name for info in LANGS.values()})


def by_tier(tier: str) -> list:
    """按资源层级筛选,如 low 得到全部小语种。"""
    return [i for i in LANGS.values() if i.resource_tier == tier]
