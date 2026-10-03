"""源语种自动识别:书写系统判定 + 功能词打分 + 特征字符判定。

设计目标
--------
1. 零依赖、纯离线、亚毫秒级——用于网页实时翻译的前置判断。
2. 非拉丁文字:靠书写系统即可高置信度锁定语种。
3. 拉丁文字:功能词(冠词/介词/代词/助动词)是最强判别特征,
   配合语种特征字符(如波兰语 ł、越南语 ệ)提升准确率。
4. 始终返回置信度;置信度低时由调用方决定是否要求用户显式指定语种。

若安装了可选依赖 langid / fasttext,会自动优先使用以获得更高准确率。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ------------------------------------------------------------------ 书写系统

_SCRIPT_RANGES = {
    "Han": (0x4E00, 0x9FFF),
    "Hiragana": (0x3040, 0x309F),
    "Katakana": (0x30A0, 0x30FF),
    "Hangul": (0xAC00, 0xD7AF),
    "Cyrillic": (0x0400, 0x04FF),
    "Arabic": (0x0600, 0x06FF),
    "Hebrew": (0x0590, 0x05FF),
    "Devanagari": (0x0900, 0x097F),
    "Bengali": (0x0980, 0x09FF),
    "Gurmukhi": (0x0A00, 0x0A7F),
    "Gujarati": (0x0A80, 0x0AFF),
    "Oriya": (0x0B00, 0x0B7F),
    "Tamil": (0x0B80, 0x0BFF),
    "Telugu": (0x0C00, 0x0C7F),
    "Kannada": (0x0C80, 0x0CFF),
    "Malayalam": (0x0D00, 0x0D7F),
    "Sinhala": (0x0D80, 0x0DFF),
    "Thai": (0x0E00, 0x0E7F),
    "Lao": (0x0E80, 0x0EFF),
    "Tibetan": (0x0F00, 0x0FFF),
    "Myanmar": (0x1000, 0x109F),
    "Khmer": (0x1780, 0x17FF),
    "Georgian": (0x10A0, 0x10FF),
    "Armenian": (0x0530, 0x058F),
    "Ethiopic": (0x1200, 0x137F),
}


def detect_script(text: str) -> str:
    """判断文本的主导书写系统。

    假名/谚文为决定性特征:出现假名判为日语,出现谚文判为韩语。
    """
    if not text:
        return "Unknown"
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for name, (lo, hi) in _SCRIPT_RANGES.items():
            if lo <= cp <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
    if not counts:
        return "Latin"
    for decisive in ("Hiragana", "Katakana", "Hangul"):
        if counts.get(decisive, 0) >= 2:
            return {"Hiragana": "Japanese", "Katakana": "Japanese",
                    "Hangul": "Korean"}[decisive]
    return max(counts.items(), key=lambda kv: kv[1])[0]


def looks_chinese(text: str) -> bool:
    """判断文本是否已是中文(用于跳过翻译)。"""
    han = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    if han == 0:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    return han / len(letters) > 0.3


# ------------------------------------------------------------------ 文本清洗

_TAG = re.compile(r"<[^>]+>")
_ENTITIES = {
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&#39;": "'", "&apos;": "'", "&mdash;": "—",
    "&ndash;": "–", "&hellip;": "…", "&middot;": "·",
}


def strip_markup(text: str) -> str:
    """剥离 HTML 标签与常见实体。"""
    if "<" in text and ">" in text:
        text = _TAG.sub("", text)
    for ent, rep in _ENTITIES.items():
        text = text.replace(ent, rep)
    return text


def normalize_unicode(text: str) -> str:
    """统一 Unicode 规范形式,消除同形异码。"""
    return unicodedata.normalize("NFKC", text)


# ------------------------------------------------------- 非拉丁语种特征字符

# 每个语种在书写系统内的判别性字符(越独特越可靠)
_DISTINCT = {
    # 斯拉夫
    "ukr_Cyrl": "іїєґІЇЄҐ",
    "bel_Cyrl": "ўіЎІ",
    "srp_Cyrl": "ђћџљњЋЂЏЉЊ",
    "mkd_Cyrl": "ѓќѕљњЃЌЅЉЊ",
    "bul_Cyrl": "ъщ",
    "rus_Cyrl": "ыэъёЫЭЪЁ",
    "kaz_Cyrl": "әғқңөұүһі",
    "kir_Cyrl": "өү",
    "tgk_Cyrl": "әň",
    "bak_Cyrl": "ғҙһ",
    "tat_Cyrl": "әғө",
    # 希腊
    "ell_Grek": "θξψως",
    # 高加索 / 亚美尼亚
    "kat_Geor": "ღყშჩცძწჭხჯჰ",
    "hye_Armn": "ևֆուձյշ",
    # 闪米特
    "heb_Hebr": "ךםןףץ",
    "amh_Ethi": "ሀሁሂሃህነአከ",
    "tir_Ethi": "በከየገግዝ",
    "arb_Arab": "ثجحخدذرزسشصضطظعغفقكلمنهوي",
    "fas_Arab": "پچژگکی",
    "urd_Arab": "ٹڈڑںھےہی",
    "pus_Arab": "ډړږڼ",
    "uig_Arab": "ۇۆۈڭ",
    # 南亚
    "hin_Deva": "कखगघचछजझञटठडढणतथदधनपफबभमयरलवशषसह",
    "mar_Deva": "ळऴ",
    "nep_Deva": "झञ",
    "bho_Deva": "ञ",
    "mai_Deva": "ञ",
    "san_Deva": "ञ",
    "ben_Beng": "ঞ",
    "asm_Beng": "ৱ",
    "pan_Guru": "ਞਸ਼",
    "guj_Gujr": "ઞ્",
    "ori_Orya": "ଢ଼",
    "tam_Taml": "ஃஶஷஸஹ",
    "tel_Telu": "ఢఱ",
    "kan_Knda": "ಝೞ",
    "mal_Mlym": "ഴൺ",
    "sin_Sinh": "ඉගඣ",
    # 东南亚
    "tha_Thai": "ะัาำิีึืุู",
    "lao_Laoo": "ັິີຸູ",
    "mya_Mymr": "ကငတ",
    "khm_Khmr": "អំរ",
    "bod_Tibt": "ༀ་ྂ",
    "dzo_Tibt": "ཨོཾ",
    # 欧洲拉丁扩展
    "isl_Latn": "þæðö",
    "pol_Latn": "ąćęłńśźż",
    "ces_Latn": "ěřůčďňťžů",
    "slk_Latn": "ľĺŕäôčšžýá",
    "ron_Latn": "ăîșțâ",
    "hrv_Latn": "čćžšđ",
    "srp_Latn": "čćžšđ",
    "bos_Latn": "čćžšđ",
    "slv_Latn": "čšž",
    "hun_Latn": "őű",
    "fin_Latn": "äö",
    "est_Latn": "õ",
    "lav_Latn": "āčēģīķļņšūž",
    "lit_Latn": "ąčęėįšųūž",
    "sqi_Latn": "ëç",
    "mlt_Latn": "ċġħż",
    "tur_Latn": "ğışİ",
    "azj_Latn": "əğış",
    "kkj_Latn": "әғқңһ",
    "uzn_Latn": "ʻʼ",
    "tuk_Latn": "äçşžň",
    "tgk_Latn": "äçşžň",
    "kat_Latn": "შ",
    "eus_Latn": "ñ",
    "glg_Latn": "ñ",
    "cat_Latn": "ïò",
    "tgl_Latn": "ñ",
    "ceb_Latn": "ñ",
    "ilo_Latn": "ñ",
    "hau_Latn": "ƙƊɓɗŋ",
    "ful_Latn": "ƙɓɗŋ",
    "yor_Latn": "ẹọṣ",
    "swa_Latn": "ŉ",
    "sna_Latn": "ŉ",
    "vie_Latn": "ơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹđ",
}

# 书写系统 -> 该系统下的语种集合(用于把范围收窄到少数候选)
_SCRIPT_LANGS = {
    "Cyrillic": ["rus_Cyrl", "ukr_Cyrl", "bel_Cyrl", "bul_Cyrl", "srp_Cyrl",
                 "mkd_Cyrl", "kaz_Cyrl", "kir_Cyrl", "tgk_Cyrl", "bak_Cyrl",
                 "tat_Cyrl"],
    "Greek": ["ell_Grek"],
    "Georgian": ["kat_Geor"],
    "Armenian": ["hye_Armn"],
    "Hebrew": ["heb_Hebr"],
    "Ethiopic": ["amh_Ethi", "tir_Ethi"],
    "Arabic": ["arb_Arab", "fas_Arab", "urd_Arab", "pus_Arab", "uig_Arab"],
    "Devanagari": ["hin_Deva", "mar_Deva", "nep_Deva"],
    "Bengali": ["ben_Beng", "asm_Beng"],
    "Gurmukhi": ["pan_Guru"],
    "Gujarati": ["guj_Gujr"],
    "Tamil": ["tam_Taml"],
    "Telugu": ["tel_Telu"],
    "Kannada": ["kan_Knda"],
    "Malayalam": ["mal_Mlym"],
    "Sinhala": ["sin_Sinh"],
    "Thai": ["tha_Thai"],
    "Lao": ["lao_Laoo"],
    "Tibetan": ["bod_Tibt", "dzo_Tibt"],
    "Myanmar": ["mya_Mymr"],
    "Khmer": ["khm_Khmr"],
    "Japanese": ["jpn_Jpan"],
    "Korean": ["kor_Hang"],
    "Han": ["zho_Hans"],
}

# 书写系统的判定容差:某字符占比超过此值即认为主导脚本为该系统
_SCRIPT_CJK_HINT = 0.15


# ------------------------------------------------------------- 拉丁语种功能词

# 高频功能词(冠词/介词/代词/助动词/连词),是拉丁语种最强判别信号
_STOPWORDS = {
    "eng_Latn": [
        "the ", " of ", " and ", " to ", " in ", " is ", " that ", " it ", " for ",
        " was ", " on ", " are ", " as ", " with ", " his ", " they ", " i ", " you ",
        " not ", " this ", " but ", " have ", " from ", " or ", " had ", " we ",
        " will ", " would ", " there ", " their ", " what ", " about ", " which ",
        " when ", " can ", " all ", " if ", " me ", " your ", " no ", " been ",
        " hello ", " thank ", " please ",
    ],
    "fra_Latn": [
        " le ", " la ", " les ", " de ", " du ", " des ", " un ", " une ", " et ",
        " est ", " que ", " qui ", " dans ", " pour ", " pas ", " sur ", " au ",
        " aux ", " ce ", " cette ", " il ", " elle ", " nous ", " vous ", " ils ",
        " mais ", " ou ", " avec ", " sans ", " plus ", " tout ", " très ", " sont ",
        " être ", " avoir ", " fait ", " moi ", " toi ", " son ", " sa ", " notre ",
        " votre ", " bonjour ", " merci ", " comment ", " pourquoi ", " quand ",
        " comme ", " cela ", " alors ", " aussi ", " depuis ", " si ", " ne ",
        " aux ", " chez ", " leurs ", " peut ", " faut ",
    ],
    "deu_Latn": [
        " der ", " die ", " das ", " und ", " ist ", " nicht ", " ein ", " eine ",
        " einen ", " einem ", " einer ", " ich ", " wir ", " ihr ", " sie ", " er ",
        " es ", " mit ", " für ", " auf ", " auch ", " werden ", " von ", " zu ",
        " im ", " in ", " dem ", " den ", " des ", " sind ", " war ", " haben ",
        " hat ", " dass ", " wie ", " was ", " aber ", " oder ", " wenn ", " man ",
        " sich ", " noch ", " nur ", " schon ", " bei ", " aus ", " nach ",
        " über ", " vor ", " durch ", " um ", " seit ", " bis ", " gegen ", " ohne ",
        " unter ", " mehr ", " sehr ", " hallo ", " danke ", " bitte ", " zum ",
        " zur ", " kann ", " wird ", " hier ", " dann ", " damit ",
    ],
    "spa_Latn": [
        " el ", " la ", " los ", " las ", " un ", " una ", " de ", " del ", " que ",
        " y ", " en ", " para ", " con ", " por ", " no ", " se ", " es ", " son ",
        " como ", " más ", " pero ", " su ", " sus ", " mi ", " tu ", " ese ",
        " esta ", " este ", " eso ", " muy ", " todo ", " todos ", " también ",
        " porque ", " cuando ", " donde ", " quien ", " cuál ", " cómo ", " qué ",
        " hola ", " gracias ", " buen ", " día ", " ser ", " estar ", " tener ",
        " hay ", " ha ", " han ", " nuestro ", " nuestra ", " desde ", " entre ",
        " sobre ", " hasta ", " cada ", " puede ", " hola ",
    ],
    "por_Latn": [
        " o ", " a ", " os ", " as ", " um ", " uma ", " de ", " do ", " da ",
        " dos ", " das ", " e ", " que ", " para ", " com ", " por ", " não ", " se ",
        " em ", " no ", " na ", " nos ", " nas ", " é ", " são ", " como ", " mais ",
        " mas ", " seu ", " sua ", " meu ", " minha ", " este ", " esta ", " isso ",
        " muito ", " todos ", " também ", " porque ", " quando ", " onde ", " quem ",
        " que ", " como ", " olá ", " obrigado ", " ser ", " ter ", " há ", " foi ",
        " foram ", " pelo ", " pela ", " desde ", " até ", " cada ", " você ",
        " não ", " até ", " pelos ",
    ],
    "ita_Latn": [
        " il ", " lo ", " la ", " i ", " gli ", " le ", " di ", " del ", " della ",
        " e ", " che ", " per ", " con ", " non ", " in ", " un ", " una ", " sono ",
        " è ", " come ", " più ", " ma ", " mi ", " ti ", " ci ", " questo ",
        " questa ", " suo ", " sua ", " loro ", " molto ", " tutti ", " tutto ",
        " anche ", " perché ", " quando ", " dove ", " chi ", " cosa ", " ciao ",
        " grazie ", " essere ", " avere ", " fa ", " hanno ", " era ", " nel ",
        " nella ", " sul ", " dalla ", " gli ", " quello ", " quella ", " si ",
        " sempre ", " già ", " ancora ", " molto ",
    ],
    "nld_Latn": [
        " de ", " het ", " een ", " en ", " van ", " niet ", " is ", " zijn ", " dat ",
        " op ", " voor ", " met ", " te ", " die ", " er ", " ik ", " je ", " hij ",
        " wij ", " ook ", " worden ", " maar ", " of ", " als ", " door ", " over ",
        " ze ", " zich ", " bij ", " uit ", " naar ", " heeft ", " hebben ", " was ",
        " waren ", " hoe ", " wat ", " waarom ", " wanneer ", " hallo ", " dank ",
        " heel ", " erg ", " veel ", " meer ", " al ", " geen ", " wel ", " tot ",
        " onder ", " tussen ", " kan ", " hier ", " daar ", " jullie ",
    ],
    "swa_Latn": [
        " na ", " ya ", " wa ", " kwa ", " katika ", " ni ", " za ", " la ", " cha ",
        " vya ", " kama ", " lakini ", " au ", " pia ", " hii ", " hiyo ", " huyo ",
        " wangu ", " wako ", " wao ", " sisi ", " wewe ", " yeye ", " sana ",
        " asante ", " karibu ", " habari ", " jua ", " asubuhi ", " jioni ",
        " mimi ", " yako ", " nini ", " wapi ", " lini ", " kwa nini ",
    ],
    "ind_Latn": [
        " yang ", " dan ", " di ", " dari ", " untuk ", " dengan ", " pada ", " ini ",
        " itu ", " tidak ", " adalah ", " akan ", " sudah ", " bisa ", " atau ",
        " dalam ", " juga ", " saya ", " kamu ", " dia ", " kami ", " kita ",
        " mereka ", " apa ", " bagaimana ", " mengapa ", " di ", " terima ",
        " kasih ", " selamat ", " pagi ", " malam ", " hari ", " ada ", " orang ",
        " kalau ", " bahwa ", " atau ", " satu ", " oleh ", " sebagai ", " adalah ",
    ],
    "msa_Latn": [
        " yang ", " dan ", " di ", " dari ", " untuk ", " dengan ", " pada ", " ini ",
        " itu ", " tidak ", " adalah ", " akan ", " sudah ", " boleh ", " atau ",
        " dalam ", " juga ", " saya ", " kamu ", " dia ", " kami ", " kita ",
        " mereka ", " apa ", " bagaimana ", " mengapa ", " terima ", " kasih ",
        " selamat ", " pagi ", " malam ", " hari ", " ada ", " orang ", " kalau ",
        " bahawa ", " oleh ", " sebagai ", " telah ", " sangat ", " bukan ",
    ],
    "vie_Latn": [
        " và ", " của ", " là ", " không ", " có ", " được ", " trong ", " người ",
        " những ", " cho ", " một ", " các ", " với ", " này ", " đã ", " để ",
        " khi ", " đến ", " về ", " như ", " từ ", " ra ", " thì ", " tôi ", " bạn ",
        " anh ", " chị ", " xin ", " cảm ", " ơn ", " nhé ", " ạ ", " những ",
        " quá ", " rất ", " cũng ", " còn ", " phải ", " nữa ", " chúng ",
    ],
    "pol_Latn": [
        " nie ", " jest ", " się ", " i ", " w ", " z ", " na ", " do ", " to ",
        " że ", " jak ", " ale ", " tylko ", " już ", " jeszcze ", " przez ",
        " dla ", " przy ", " może ", " być ", " mam ", " masz ", " on ", " ona ",
        " ono ", " my ", " wy ", " oni ", " gdzie ", " kiedy ", " dlaczego ",
        " cześć ", " dziękuję ", " bardzo ", " wszystko ", " nic ", " ktoś ",
        " jestem ", " jesteś ", " tego ", " jego ", " jej ",
    ],
    "ces_Latn": [
        " a ", " je ", " se ", " na ", " v ", " z ", " do ", " to ", " že ", " ale ",
        " jako ", " pro ", " od ", " po ", " za ", " který ", " které ", " jsou ",
        " byl ", " byla ", " být ", " má ", " mají ", " já ", " ty ", " on ", " ona ",
        " my ", " vy ", " oni ", " kde ", " kdy ", " proč ", " ahoj ", " děkuji ",
        " velmi ", " všechno ", " nic ", " jsem ", " jsi ", " toho ", " jeho ",
        " její ", " tak ", " také ", " když ", " ještě ", " jak se ", " dobrý ",
        " den ", " den, ", " máš ", " máte ", " si ", " o ", " ve ", " není ",
    ],
    "slk_Latn": [
        " a ", " je ", " sa ", " na ", " v ", " z ", " do ", " to ", " že ", " ale ",
        " ako ", " pre ", " od ", " po ", " za ", " ktorý ", " ktoré ", " sú ",
        " bol ", " bola ", " byť ", " má ", " majú ", " ja ", " ty ", " on ", " ona ",
        " my ", " vy ", " oni ", " kde ", " kedy ", " prečo ", " ahoj ",
        " ďakujem ", " veľmi ", " všetko ", " nič ", " som ", " si ", " jeho ",
    ],
    "tur_Latn": [
        " bir ", " ve ", " bu ", " için ", " ile ", " de ", " da ", " çok ", " daha ",
        " olan ", " olarak ", " var ", " yok ", " ne ", " nasıl ", " neden ", " kim ",
        " hangi ", " ben ", " sen ", " o ", " biz ", " siz ", " onlar ", " ise ",
        " ki ", " ama ", " ya ", " hem ", " göre ", " sonra ", " önce ", " kadar ",
        " ancak ", " merhaba ", " teşekkür ", " değil ", " olan ", " şey ",
        " değil ", " böyle ", " şöyle ",
    ],
    "hun_Latn": [
        " és ", " nem ", " hogy ", " egy ", " meg ", " de ", " van ", " ez ", " az ",
        " mint ", " csak ", " már ", " még ", " kell ", " lehet ", " én ", " te ",
        " ő ", " mi ", " ti ", " ők ", " hol ", " mikor ", " miért ", " hogyan ",
        " köszönöm ", " nagyon ", " minden ", " semmi ", " vagy ", " ami ", " aki ",
        " ha ", " vagyok ", " vagyunk ", " volt ", " lesz ", " ezt ", " ezek ",
    ],
    "fin_Latn": [
        " ja ", " on ", " ei ", " että ", " en ", " joka ", " kun ", " mutta ", " niin ",
        " tai ", " myös ", " vain ", " vielä ", " jo ", " olen ", " olet ", " hän ",
        " me ", " te ", " he ", " missä ", " milloin ", " miksi ", " miten ",
        " hei ", " kiitos ", " paljon ", " kaikki ", " mitään ", " tämä ", " sekä ",
        " ovat ", " oli ", " ollut ", " siis ", " nyt ",
    ],
    "est_Latn": [
        " ja ", " on ", " ei ", " et ", " see ", " oli ", " aga ", " ka ", " kui ",
        " mis ", " siis ", " veel ", " juba ", " ainult ", " palju ", " väga ",
        " aitäh ", " tänapäeval ", " ma ", " me ", " nad ", " sa ", " ta ",
        " tema ", " meie ", " teie ", " nemad ", " oma ", " üks ", " kaks ",
    ],
    "ron_Latn": [
        " și ", " de ", " la ", " în ", " cu ", " un ", " o ", " este ", " sunt ",
        " pe ", " pentru ", " nu ", " se ", " din ", " ca ", " care ", " mai ",
        " ce ", " dar ", " dacă ", " când ", " unde ", " cine ", " cum ", " eu ",
        " tu ", " el ", " ea ", " noi ", " voi ", " ei ", " bună ", " mulțumesc ",
        " foarte ", " tot ", " nimic ", " așa ", " deci ", " fost ", " fi ",
    ],
    "hrv_Latn": [
        " i ", " je ", " su ", " na ", " se ", " za ", " da ", " od ", " do ", " ne ",
        " a ", " u ", " s ", " ali ", " kao ", " ili ", " što ", " koji ", " koja ",
        " ovo ", " taj ", " bio ", " bila ", " bili ", " sam ", " si ", " smo ",
        " ste ", " hvala ", " bok ", " dobro ", " dan ", " več ", " lahko ",
    ],
    "sqi_Latn": [
        " dhe ", " është ", " për ", " nuk ", " me ", " në ", " të ", " një ", " janë ",
        " por ", " si ", " ky ", " ajo ", " unë ", " ti ", " ai ", " ne ", " ju ",
        " faleminderit ", " mirë ", " ditën ", " natën ", " shumë ", " çdo ",
        " pas ", " prej ", " deri ", " edhe ", " kështu ",
    ],
    "cat_Latn": [
        " el ", " la ", " els ", " les ", " un ", " una ", " de ", " del ", " que ",
        " i ", " en ", " amb ", " per ", " no ", " és ", " són ", " com ", " més ",
        " però ", " seu ", " seva ", " molt ", " també ", " però ", " aquest ",
        " aquesta ", " què ", " com ", " on ", " perquè ", " bon dia ", " gràcies ",
    ],
    "eus_Latn": [
        " eta ", " da ", " ez ", " bat ", " du ", " dira ", " baina ", " gero ",
        " dago ", " hau ", " zu ", " nire ", " zure ", " gure ", " beren ", " dela ",
        " bere ", " ditu ", " oso ", " asko ", " oso ", " aldi ", " honek ", " honek ",
    ],
    "tgl_Latn": [
        " ang ", " ng ", " mga ", " at ", " sa ", " na ", " ay ", " mga ", " ito ",
        " iyon ", " hindi ", " may ", " para ", " kung ", " pero ", " o ", " ka ",
        " mo ", " namin ", " natin ", " nila ", " salamat ", " magandang ",
        " umaga ", " gabi ", " araw ", " maraming ",
    ],
    "gle_Latn": [
        " an ", " is ", " agus ", " na ", " ar ", " do ", " le ", " go ", " i ",
        " tá ", " bhfuil ", " seo ", " sin ", " mé ", " tú ", " sé ", " sí ", " muid ",
        " sibh ", " siad ", " go raibh ", " maith ", " fáilte ", " ag ", " chun ",
    ],
    "afr_Latn": [
        " die ", " het ", " 'n ", " en ", " van ", " is ", " nie ", " wat ", " in ",
        " dat ", " op ", " met ", " vir ", " te ", " is ", " ek ", " jy ", " hy ",
        " ons ", " hulle ", " was ", " sal ", " asseblief ", " baie ", " baie ",
        " reeds ", " nog ", " so ", " meer ", " goed ", " dankie ", " hallo ",
    ],
    "isl_Latn": [
        " og ", " að ", " á ", " er ", " sem ", " til ", " í ", " um ", " það ",
        " þessi ", " hann ", " hún ", " það ", " þeir ", " þær ", " þau ", " ekki ",
        " mér ", " þér ", " okkar ", " ykkar ", " þeimra ", " þeirra ", " vera ",
        " hef ", " hefur ", " hafa ", " verið ", " þó ", " eða ", " en ",
    ],
    "hau_Latn": [
        " da ", " na ", " ta ", " ya ", " a ", " ba ", " ne ", " ce ", " ko ", " ku ",
        " mu ", " su ", " in ", " sai ", " wannan ", " wanda ", " wadannan ", " ni ",
        " ka ", " ki ", " kuma ", " amma ", " sai ", " yana ", " tana ", " suna ",
        " sannu ", " barka ", " yaya ", " ina ", " me ", " ke ",
    ],
    "yor_Latn": [
        " ni ", " ti ", " ati ", " si ", " won ", " ki ", " pe ", " ni ", " fun ",
        " si ", " pe ", " o ", " a ", " ti ", " won ", " ki ", " pe ", " yi ", " naa ",
        " se ", " pelu ", " tabi ", " rara ", " nitori ", " jowo ", " nina ", " wa ",
    ],
    "zho_Hans": [],
    "dan_Latn": [
        " og ", " at ", " det ", " som ", " en ", " på ", " er ", " af ", " for ",
        " med ", " til ", " den ", " har ", " de ", " ikke ", " om ", " et ", " men ",
        " var ", " jeg ", " du ", " han ", " hun ", " vi ", " i ", " de ", " hvordan ",
        " hvad ", " hvorfor ", " hvornår ", " hej ", " tak ", " meget ", " alt ",
        " ingenting ", " til ", " fra ", " over ", " under ",
    ],
    "nob_Latn": [
        " og ", " i ", " det ", " som ", " en ", " på ", " er ", " av ", " for ",
        " med ", " til ", " den ", " har ", " de ", " ikke ", " om ", " et ", " men ",
        " var ", " jeg ", " du ", " han ", " hun ", " vi ", " dere ", " hvordan ",
        " hva ", " hvorfor ", " når ", " hei ", " takk ", " mye ", " alt ", " ingenting ",
    ],
    "swe_Latn": [
        " och ", " att ", " det ", " som ", " en ", " på ", " är ", " av ", " för ",
        " med ", " till ", " den ", " har ", " de ", " inte ", " om ", " ett ", " men ",
        " var ", " jag ", " du ", " han ", " hon ", " vi ", " ni ", " hur ", " vad ",
        " varför ", " när ", " hej ", " tack ", " mycket ", " allt ", " ingenting ",
        " till ", " från ", " över ", " under ", " kan ", " här ",
    ],
}

# 语种别名 -> _STOPWORDS 键(某些语种共享表)
_STOP_ALIAS = {
    "gle_Latn": "eng_Latn",
    "hat_Latn": "fra_Latn",
    "gcr_Latn": "por_Latn",
    "jav_Latn": "ind_Latn",
    "sun_Latn": "ind_Latn",
    "ilo_Latn": "tgl_Latn",
    "ceb_Latn": "tgl_Latn",
    "azj_Latn": "tur_Latn",
    "kkj_Latn": "tur_Latn",
    "uzn_Latn": "tur_Latn",
    "tuk_Latn": "tur_Latn",
    "crh_Latn": "tur_Latn",
    "srp_Latn": "hrv_Latn",
    "bos_Latn": "hrv_Latn",
    "slv_Latn": "hrv_Latn",
    "nno_Latn": "nob_Latn",
    "bam_Latn": "fra_Latn",
    "wol_Latn": "fra_Latn",
    "lug_Latn": "swa_Latn",
    "lin_Latn": "fra_Latn",
    "run_Latn": "swa_Latn",
    "tso_Latn": "swa_Latn",
    "ssw_Latn": "swa_Latn",
    "nya_Latn": "swa_Latn",
    "umb_Latn": "swa_Latn",
    "kal_Latn": "dan_Latn",
    "epo_Latn": "eng_Latn",
}

# 各语种问候语/常见开场白:在短文本上比功能词更可靠。
# 注意:必须用词边界匹配,否则 "bonjour" 会命中 "bon" 之类的前缀。
_GREETINGS = {
    "tur_Latn": ["merhaba", "nasilsiniz", "nasilsin", "gunaydin",
                 "iyi aksamlar", "hos bulduk"],
    "ell_Grek": ["geia", "kalimera", "ti kanete"],
    "heb_Hebr": ["shalom", "boker tov"],
    "tha_Thai": ["sawat", "sawasdee"],
    "ind_Latn": ["selamat", "assalamualaikum"],
    "msa_Latn": ["selamat", "assalamualaikum"],
    "swa_Latn": ["habari", "jambo", "asubuhi njema", "pole"],
    "amh_Ethi": ["selam", "betam"],
    "tir_Ethi": ["selam", "dekem"],
    "arb_Arab": ["marhaba", "as-salamu alaykum", "sabah alkhayr"],
    "isl_Latn": ["halló", "góðan dag"],
    "fin_Latn": ["hei", "moi", "hyvää päivää"],
    "est_Latn": ["tere", "head hommikust"],
    "lav_Latn": ["sveiki", "labvēl"],
    "lit_Latn": ["labas", "sveiki"],
    "kat_Geor": ["gamarjosba", "moakle"],
    "hye_Armn": ["barev", "aravot"],
    "jpn_Jpan": ["konnichiwa", "ohayou", "konbanwa"],
    "kor_Hang": ["annyeonghaseyo"],
    "khm_Khmr": ["suostei", "chumreap"],
    "mya_Mymr": ["mingalarbar", "mingalaba"],
    "lao_Laoo": ["sabaidee"],
    "tgl_Latn": ["kumusta", "magandang"],
    "ceb_Latn": ["kumusta", "salamat"],
    "ilo_Latn": ["kumusta", "salamat"],
    "eus_Latn": ["kaixo", "on egin"],
    "gle_Latn": ["fáilte", "dia duit"],
    "afr_Latn": ["hallo", "groot dit"],
    "azj_Latn": ["salam", "merhaba"],
    "kkj_Latn": ["salam", "qalay"],
    "uzn_Latn": ["salom"],
    "tuk_Latn": ["sag bolung", "salam"],
    "crh_Latn": ["merhaba", "selam"],
    "fas_Arab": ["salam", "sobh be khayr"],
    "urd_Arab": ["salam", "sabah bakhair"],
    "pus_Arab": ["salam", "sab bakhair"],
    "kat_Geor2": [],
}
_GREETINGS = {k: v for k, v in _GREETINGS.items() if v}

# 预编译词边界正则(支持无空格书写体系:泰语/高棉语/缅甸语等)
_GREETING_RES = [
    (flores, re.compile(r"(?<![\w])" + re.escape(w) + r"(?![\w])"))
    for flores, words in _GREETINGS.items()
    for w in words
]


def _greeting_hit(low: str) -> str:
    """若文本含某语种的问候语,返回该语种 FLORES 代码(词边界匹配)。

    词边界用 (?<![a-z]) 之类的拉丁边界,避免 "tere" 命中 "Wissenschaft"
    这类跨词包含。但无空格书写体系(泰语/高棉语)不适用拉丁边界。
    """
    for flores, rx in _GREETING_RES:
        if rx.search(low):
            return flores
    return ""



def _greeting_hit(low: str) -> str:
    """若文本含某语种的问候语,返回该语种 FLORES 代码。"""
    for flores, words in _GREETINGS.items():
        for w in words:
            if w in low:
                return flores
    return ""


# 归一化后(去重)的功能词表
_STOPWORDS = {k: sorted(set(v)) for k, v in _STOPWORDS.items() if v}

# 合并短文本补充词表(来自 _words.py)
try:
    from ._words import EXTRA_STOPWORDS as _EXTRA_STOP
except ImportError:  # pragma: no cover
    _EXTRA_STOP = {}

for _k, _v in _EXTRA_STOP.items():
    _STOPWORDS[_k] = sorted(set(_STOPWORDS.get(_k, [])) | set(_v.split()))

# 判定为"非某语种"的独占字符(高特异性,直接判定)
_EXCLUSIVE = {
    "vie_Latn": "ơư",
    "tur_Latn": "ğışİş",
    "pol_Latn": "ł",
    "ces_Latn": "řů",
    "rom_Latn": "ășț",
    "isl_Latn": "þð",
    "hrv_Latn": "ćđ",
    "lav_Latn": "ģķļņ",
    "lit_Latn": "ėįų",
    "mlt_Latn": "ġħ",
    "sqi_Latn": "ë",
    "hun_Latn": "őű",
    "uig_Arab": "ۇ",
    "pan_Guru": "ਞ",
    "ben_Beng": "ঞ",
    "tir_Ethi": "በ",
    "amh_Ethi": "ሀ",
    "kat_Geor": "შ",
    "hye_Armn": "և",
    "ell_Grek": "θξ",
    "ukr_Cyrl": "іїєґ",
    "srp_Cyrl": "ђћџ",
    "mkd_Cyrl": "ѓќѕ",
    "bel_Cyrl": "ў",
    "kaz_Cyrl": "әғ",
    "tha_Thai": "ะ",
    "lao_Laoo": "ັ",
    "mya_Mymr": "က",
    "khm_Khmr": "អ",
    "bod_Tibt": "ༀ",
    "tam_Taml": "ஃ",
    "tel_Telu": "ఢ",
    "kan_Knda": "ಝ",
    "mal_Mlym": "ഴ",
    "sin_Sinh": "ඉ",
    "heb_Hebr": "ך",
    "hau_Latn": "ƙɓ",
    "yor_Latn": "ẹọṣ",
    "azj_Latn": "ə",
    "uzn_Latn": "ʻ",
    "est_Latn": "õ",
    "lit_Latn": "ų",
}


@dataclass
class Detection:
    """语种识别结果。"""

    flores: str           # FLORES-200 语种代码
    confidence: float     # 0~1 置信度
    method: str           # script / exclusive / stopword / default / external
    script: str           # 书写系统

    @property
    def is_reliable(self) -> bool:
        return self.confidence >= 0.55


def _distinct_chars_for(flores: str) -> str:
    return _DISTINCT.get(flores, "")


# 西语倒问号/倒叹号、各类引号与破折号:统计前统一规整,避免切碎功能词
_PUNCT_NORM = {
    "¿": "", "¡": "",          # ¿ ¡
    "’": "'", "ʼ": "'",        # ’ ʼ
    "‘": "'", "“": '"', "”": '"',
    "«": '"', "»": '"',
    "–": "-", "—": "-",
    " ": " ", " ": " ", " ": " ",
    "­": "",
}


def normalize_for_scoring(text: str) -> str:
    """把标点规整为 ASCII 形式,提升功能词匹配率。"""
    if not text:
        return ""
    for k, v in _PUNCT_NORM.items():
        if k in text:
            text = text.replace(k, v)
    return re.sub(r"\s+", " ", text).strip().lower()


_WORD_SPLIT = re.compile(r"[^\w']+", re.UNICODE)


def _tokens(text: str) -> list:
    """按非字母数字边界切词,用于精确的功能词匹配。"""
    return [t for t in _WORD_SPLIT.split(text) if t]


def _score_padded(low: str, words) -> int:
    """按整词统计功能词命中次数。

    早期实现用带空格的子串匹配,只有词表中带空格的功能词
    (如 " der ")才能命中,导致 "Guten Tag" 这类短语首词无法参与。
    这里改为整词集合求交,长短语均适用,且不会跨词误匹配。
    """
    toks = set(_tokens(low))
    if not toks:
        return 0
    hits = 0
    for w in words:
        if len(w) < 2:
            continue
        # 词表项可能自带首尾空格,统一剥掉
        ww = w.strip()
        if not ww:
            continue
        if " " in ww:
            if ww in low:
                hits += 1
        elif ww in toks:
            hits += 1
    return hits


def _score_stopwords(low: str, n_words: int) -> dict:
    """按功能词命中密度给拉丁语种打分。"""
    scores = {}
    for flores, words in _STOPWORDS.items():
        hits = _score_padded(low, words)
        if hits:
            # 归一化:命中数 / 词表大小(短表更易命中,需校正)
            density = hits / (n_words + 1)
            scores[flores] = density * (1.0 + hits * 0.12)
    return scores


def _apply_alias(scores: dict) -> dict:
    """把别名语种的分数归并到主语种。"""
    for alias, base in _STOP_ALIAS.items():
        if alias in scores:
            scores[base] = scores.get(base, 0.0) + scores.pop(alias)
    return scores


def _lang_script_hits(text: str, flores: str) -> int:
    """文本中命中该语种特征字符的次数。"""
    chars = _distinct_chars_for(flores)
    if not chars:
        return 0
    return sum(1 for c in text if c in chars)


def _script_from_name(name: str) -> str:
    """把 Unicode 脚本名转为内部书写系统名。"""
    return {
        "Cyrillic": "Cyrillic", "Greek": "Greek", "Arabic": "Arabic",
        "Hebrew": "Hebrew", "Devanagari": "Devanagari", "Bengali": "Bengali",
        "Gurmukhi": "Gurmukhi", "Gujarati": "Gujarati", "Oriya": "Oriya",
        "Tamil": "Tamil", "Telugu": "Telugu", "Kannada": "Kannada",
        "Malayalam": "Malayalam", "Sinhala": "Sinhala", "Thai": "Thai",
        "Lao": "Lao", "Tibetan": "Tibetan", "Myanmar": "Myanmar",
        "Khmer": "Khmer", "Georgian": "Georgian", "Armenian": "Armenian",
        "Ethiopic": "Ethiopic", "Hiragana": "Japanese", "Katakana": "Japanese",
        "Hangul": "Korean", "Han": "Han",
    }.get(name, name)


def guess_language(text: str, default: str = "eng_Latn") -> Detection:
    """识别文本的源语种,返回 FLORES 代码与置信度。"""
    from .languages import ZHO_HANS  # 局部导入避免循环依赖

    if not text or not text.strip():
        return Detection(default, 0.0, "default", "Unknown")

    if looks_chinese(text):
        return Detection(ZHO_HANS, 0.95, "script", "Han")

    script = detect_script(text)
    internal = _script_from_name(script)

    # 1) 独占字符判定(特异性最高)
    for flores, chars in _EXCLUSIVE.items():
        if any(c in text for c in chars):
            # 确认该语种的书写系统与文本一致
            from .languages import LANGS

            info = LANGS.get(flores)
            if info and (info.script == internal or info.script == script):
                return Detection(flores, 0.9, "exclusive", internal)

    # 1.5) 问候语候选(先记录,待功能词打分后仲裁)
    greeting = ""
    if internal not in _SCRIPT_LANGS:
        greeting = _greeting_hit(normalize_for_scoring(text))

    # 2) 书写系统内语种判定
    if internal in _SCRIPT_LANGS:
        cands = _SCRIPT_LANGS[internal]
        if len(cands) == 1:
            return Detection(cands[0], 0.9, "script", internal)
        # 多个候选:按特征字符命中数打分
        best = max(cands, key=lambda f: _lang_script_hits(text, f))
        hits = _lang_script_hits(text, best)
        second = sorted((_lang_script_hits(text, f) for f in cands), reverse=True)
        runner = second[1] if len(second) > 1 else 0
        if hits > runner:
            return Detection(best, 0.75 if hits else 0.5,
                             "script+char" if hits else "script", internal)
        return Detection(best, 0.4, "script", internal)

    # 3) 拉丁文字:功能词打分
    if internal in ("Latin", "Unknown"):
        # 可选外部检测器优先
        ext = _external_detect(text)
        if ext is not None:
            return ext

        low = normalize_for_scoring(text)
        n_words = max(1, len(low.split()))
        scores = _apply_alias(_score_stopwords(low, n_words))
        if scores:
            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
            top, top_s = ranked[0]
            second_s = ranked[1][1] if len(ranked) > 1 else 0.0
            # 置信度:绝对强度 + 与第二名的差距
            strength = min(1.0, top_s / 0.9)
            margin = (top_s - second_s) / max(top_s, 1e-6)
            conf = 0.35 + 0.35 * strength + 0.25 * margin
            # 弱证据仲裁:命中很少且与第二名接近时,英语是更安全的默认值。
            # 例如 "The quick brown fox..." 这类不含真实功能词的短句,
            # 各语种都会零星命中一两个词,此时应回退到英语。
            if top != "eng_Latn" and top_s < 0.35 and (top_s - second_s) < 0.2:
                return Detection("eng_Latn", round(min(0.5, conf), 3),
                                "stopword-weak", "Latin")
            # 问候语与功能词指向不同语种时,信任证据更强的功能词
            if greeting and greeting != top and top_s > 0.25:
                conf = max(conf, 0.5)
                return Detection(top, round(conf, 3), "stopword>greeting", "Latin")
            if greeting == top:
                conf = min(0.95, conf + 0.12)
                return Detection(top, round(conf, 3), "stopword+greeting", "Latin")
            return Detection(top, round(conf, 3), "stopword", "Latin")
        if greeting:
            return Detection(greeting, 0.85, "greeting", "Latin")
        return Detection(default, 0.2, "default", "Latin")

    return Detection(default, 0.2, "default", internal)


def _external_detect(text: str):
    """若安装了 langid / fasttext,则调用其获得更高准确率。"""
    try:
        import langid  # type: ignore

        code, _ = langid.classify(text[:2000])
        from .languages import resolve

        return Detection(resolve(code).flores, 0.92, "external", "Latin")
    except Exception:
        pass
    return None
