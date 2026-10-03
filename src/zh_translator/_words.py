# -*- coding: utf-8 -*-
"""短文本补充词表:问候语之外的核心词,让两词短语也能正确识别。

键为 FLORES-200 语种代码,值为空白分隔的词。
"""

EXTRA_STOPWORDS = {
    "deu_Latn": "guten gutenmorgen morgen tag abend nacht heute woche monat jahre jahr zeit leben liebe freund danke bitte nein okay warum wo wann wer was wie viel sehr schon nur auch noch immer wieder hier dort bei mit von zu zur zum fur für und oder aber dass dem den des die der das ist bin sind war hat haben kann muss wird wurde sein gut gute machen macht gehen geht kommen kommt sagen sagt geben steht liegt",
    "spa_Latn": "buenos dias noches noche gracias hola adios adiós bueno buena muy todo todos tampoco porque cuando donde quien cómo qué por para con como pero este esta esto eso tiene tienen hacer puede debe quiere sabe vida mundo tiempo dia día año años hoy mañana ahora siempre nunca aquí allí tú usted",
    "fra_Latn": "bonjour bonsoir salut merci oui non bien très trop peu aujourd aujourdhui demain hier soir matin nuit jour jours année ans vie monde temps toujours jamais ici là comment pourquoi quand où qui quoi combien parce maintenant avec sans pour dans sur plus même fait faire être avoir aller vient voit sait peut veut vous",
    "ita_Latn": "buongiorno buonasera ciao grazie prego così bene molto poco troppo oggi domani ieri sera mattina notte giorno giorni anno anni vita mondo tempo sempre mai qui come perché quando dove chi cosa con senza per nel nella fare essere avere andare vuole sa può deve",
    "por_Latn": "bom bons boa obrigado obrigada sim não muito bem hoje amanhã ontem noite dia dias ano anos vida mundo tempo sempre nunca aqui como porque quando onde quem qual com para por mas muita desculpa fazer ser ter ir quer sabe pode deve",
    "nld_Latn": "goedendag goedenavond dag morgen avond nacht vandaag jaar jaren leven wereld tijd altijd nooit hier hoe waarom wanneer wie wat hoeveel heel erg nog al ook bedankt dank graag hallo doei met voor niet naar over onder tussen zonder hebben zijn worden gaan komen maken zeggen geweest",
    "swa_Latn": "asubuhi mchana jana leo kesho tena sasa karibu sana hakuna kuna wote wengine zaidi habari hujambo jambo nini wapi lini kwa",
    "ind_Latn": "selamat pagi siang sore malam hari ini besok kemarin terima kasih banyak sedikit sangat sudah belum bisa tidak apa siapa dimana kapan mengapa bagaimana",
}
