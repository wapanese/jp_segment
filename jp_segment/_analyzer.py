from __future__ import annotations

import re

from ._amount import load_amount_combinations
from ._types import (
    PartOfSpeech,
    PartOfSpeechSection,
)
from ._wordinfo import WordInfo

HONORIFICS_SUFFIXES = ["さん", "ちゃん", "くん"]
_MIN_PAIR_LENGTH = 2
_MIN_TRIPLE_LENGTH = 3
_DOUBLE_CHAR_LENGTH = 2
_HIRAGANA_START = 0x3040
_KATAKANA_END = 0x30FF
_HALF_KATAKANA_START = 0xFF66
_HALF_KATAKANA_END = 0xFF9D


_re_clean = re.compile(
    r"[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\uFF21-\uFF3A\uFF41-\uFF5A\uFF10-\uFF19"
    r"\u3005\u3001-\u3003\u3008-\u3011\u3014-\u301F\uFF01-\uFF0F\uFF1A-\uFF1F\uFF3B-\uFF3F"
    r"\uFF5B-\uFF60\uFF62-\uFF65\uFF0E\n\u2026\u3000\u2015\u2500()。\uFF01\uFF1F「」\uFF09]"
)


def preprocess_text(text: str) -> str:
    # Mirrors MorphologicalAnalyser.PreprocessText
    text = text.replace("<", " ").replace(">", " ")
    text = _re_clean.sub("", text)
    text = text.replace("「", "\n「 ")
    text = text.replace("」", " 」\n")
    text = text.replace("〈", " \n〈 ")
    text = text.replace("〉", " 〉\n")
    text = text.replace("《", " \n《 ")
    text = text.replace("》", " 》\n")
    text = text.replace("“", " \n“ ")
    text = text.replace("”", " ”\n")
    text = text.replace("―", " ― ")
    text = text.replace("。", " 。\n")
    text = text.replace("\uff01", " \uff01\n")
    text = text.replace("\uff1f", " \uff1f\n")
    return text.replace("\u2026\r", "。\r").replace("\u2026\n", "。\n")


def process_special_cases(word_infos: list[WordInfo]) -> list[WordInfo]:
    if not word_infos:
        return word_infos
    special3 = {
        ("な", "の", "で", PartOfSpeech.Expression),
        ("で", "は", "ない", PartOfSpeech.Expression),
        ("それ", "で", "も", PartOfSpeech.Conjunction),
        ("なく", "なっ", "た", PartOfSpeech.Verb),
    }
    special2 = {
        ("じゃ", "ない", PartOfSpeech.Expression),
        ("ええ", "と", PartOfSpeech.Interjection),
        ("どっち", "も", PartOfSpeech.Expression),
        ("そう", "かもしれない", PartOfSpeech.Expression),
        ("ファイル", "名", PartOfSpeech.Noun),
        ("に", "しろ", PartOfSpeech.Expression),
        ("だ", "けど", PartOfSpeech.Conjunction),
        ("だ", "が", PartOfSpeech.Conjunction),
        ("で", "さえ", PartOfSpeech.Expression),
        ("で", "すら", PartOfSpeech.Expression),
        ("と", "いう", PartOfSpeech.Expression),
        ("と", "か", PartOfSpeech.Conjunction),
        ("だ", "から", PartOfSpeech.Conjunction),
        ("これ", "まで", PartOfSpeech.Expression),
        ("それ", "も", PartOfSpeech.Conjunction),
        ("それ", "だけ", PartOfSpeech.Noun),
        ("くせ", "に", PartOfSpeech.Conjunction),
        ("の", "で", PartOfSpeech.Particle),
        ("誰", "も", PartOfSpeech.Expression),
        ("誰", "か", PartOfSpeech.Expression),
        ("すぐ", "に", PartOfSpeech.Adverb),
        ("なん", "か", PartOfSpeech.Particle),
        ("だっ", "た", PartOfSpeech.Expression),
        ("だっ", "たら", PartOfSpeech.Conjunction),
        ("よう", "に", PartOfSpeech.Expression),
        ("ん", "です", PartOfSpeech.Expression),
        ("ん", "だ", PartOfSpeech.Expression),
        ("です", "か", PartOfSpeech.Expression),
    }
    out: list[WordInfo] = []
    i = 0
    while i < len(word_infos):
        w1 = word_infos[i]
        if w1.part_of_speech == PartOfSpeech.Conjunction and w1.text == "で":
            w1 = WordInfo(**{**w1.__dict__, "part_of_speech": PartOfSpeech.Particle})
            out.append(w1)
            i += 1
            continue
        if i + 2 < len(word_infos):
            w2 = word_infos[i + 1]
            w3 = word_infos[i + 2]
            if w1.dictionary_form == "する" and w2.text == "て" and w3.dictionary_form == "くださる":
                neww = WordInfo(**w1.__dict__)
                neww.text = w1.text + w2.text + w3.text
                out.append(neww)
                i += 3
                continue
            found = False
            for a, b, c, pos in special3:
                if w1.text == a and w2.text == b and w3.text == c:
                    neww = WordInfo(**w1.__dict__)
                    neww.text = w1.text + w2.text + w3.text
                    if pos is not None:
                        neww.part_of_speech = pos
                    out.append(neww)
                    i += 3
                    found = True
                    break
            if found:
                continue
        if i + 1 < len(word_infos):
            w2 = word_infos[i + 1]
            found = False
            for a, b, pos in special2:
                if w1.text == a and w2.text == b:
                    neww = WordInfo(**w1.__dict__)
                    neww.text = w1.text + w2.text
                    if pos is not None:
                        neww.part_of_speech = pos
                    out.append(neww)
                    i += 2
                    found = True
                    break
            if found:
                continue
        if w1.text == "でしょう":
            neww = WordInfo(**w1.__dict__)
            neww.part_of_speech = PartOfSpeech.Expression
            neww.pos1 = neww.pos2 = neww.pos3 = PartOfSpeechSection.None_
            out.append(neww)
            i += 1
            continue
        if w1.text == "だし":
            da = WordInfo(
                text="だ",
                dictionary_form="だ",
                part_of_speech=PartOfSpeech.Auxiliary,
                pos1=PartOfSpeechSection.None_,
                pos2=PartOfSpeechSection.None_,
                pos3=PartOfSpeechSection.None_,
                reading="だ",
            )
            shi = WordInfo(
                text="し",
                dictionary_form="し",
                part_of_speech=PartOfSpeech.Conjunction,
                pos1=PartOfSpeechSection.None_,
                pos2=PartOfSpeechSection.None_,
                pos3=PartOfSpeechSection.None_,
                reading="し",
            )
            out.extend((da, shi))
            i += 1
            continue
        if w1.text in {"な", "に"}:
            w1 = WordInfo(**{**w1.__dict__, "part_of_speech": PartOfSpeech.Particle})
        if w1.text == "よう":
            w1 = WordInfo(**{**w1.__dict__, "part_of_speech": PartOfSpeech.Noun})
        if w1.text == "十五":
            w1 = WordInfo(**{**w1.__dict__, "part_of_speech": PartOfSpeech.Numeral})
        out.append(w1)
        i += 1
    return out


def combine_prefixes(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if current.part_of_speech == PartOfSpeech.Prefix and current.normalized_form != "御":
            text = current.text + nxt.text
            current = WordInfo(**nxt.__dict__)
            current.text = text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_amounts(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    combos = load_amount_combinations()
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if (current.has_section(PartOfSpeechSection.Amount) or current.has_section(PartOfSpeechSection.Numeral)) and (
            (current.text, nxt.text) in combos
        ):
            text = current.text + nxt.text
            current = WordInfo(**nxt.__dict__)
            current.text = text
            current.part_of_speech = PartOfSpeech.Noun
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_tte(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if current.text.endswith("っ") and nxt.text.startswith("て"):
            current.text += nxt.text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_verb_dependants(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if nxt.has_section(PartOfSpeechSection.Dependant) and current.part_of_speech == PartOfSpeech.Verb:
            current.text += nxt.text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_verb_possible_dependants(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if (
            nxt.has_section(PartOfSpeechSection.PossibleDependant)
            and current.part_of_speech == PartOfSpeech.Verb
            and nxt.dictionary_form in {"得る", "する", "しまう", "おる", "きる", "こなす", "いく", "貰う", "いる", "ない"}
        ):
            current.text += nxt.text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_verb_dependants_suru(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    i = 0
    while i < len(word_infos):
        cur = word_infos[i]
        if i + 1 < len(word_infos):
            nxt = word_infos[i + 1]
            if (
                cur.has_section(PartOfSpeechSection.PossibleSuru)
                and nxt.dictionary_form == "する"
                and nxt.text not in {"する", "しない"}
            ):
                comb = WordInfo(**cur.__dict__)
                comb.text += nxt.text
                comb.part_of_speech = PartOfSpeech.Verb
                out.append(comb)
                i += 2
                continue
        out.append(WordInfo(**cur.__dict__))
        i += 1
    return out


def combine_verb_dependants_teiru(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_TRIPLE_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    i = 0
    while i < len(word_infos):
        cur = word_infos[i]
        if i + 2 < len(word_infos):
            n1 = word_infos[i + 1]
            n2 = word_infos[i + 2]
            if cur.part_of_speech == PartOfSpeech.Verb and n1.dictionary_form == "て" and n2.dictionary_form == "いる":
                comb = WordInfo(**cur.__dict__)
                comb.text += n1.text + n2.text
                out.append(comb)
                i += 3
                continue
        out.append(WordInfo(**cur.__dict__))
        i += 1
    return out


def combine_adverbial_particle(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if (
            nxt.has_section(PartOfSpeechSection.AdverbialParticle)
            and nxt.dictionary_form in {"だり", "たり"}
            and current.part_of_speech == PartOfSpeech.Verb
        ):
            current.text += nxt.text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_conjunctive_particle(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = [word_infos[0]]
    for i in range(1, len(word_infos)):
        current = word_infos[i]
        prev = out[-1]
        combined = False
        if (
            current.has_section(PartOfSpeechSection.ConjunctionParticle)
            and current.text in {"て", "で", "ちゃ", "ば"}
            and (prev.part_of_speech in {PartOfSpeech.Verb, PartOfSpeech.IAdjective, PartOfSpeech.Auxiliary})
        ):
            prev.text += current.text
            combined = True
        if not combined:
            out.append(current)
    return out


def combine_auxiliary(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = [word_infos[0]]
    for i in range(1, len(word_infos)):
        cur = word_infos[i]
        prev = out[-1]
        if cur.part_of_speech != PartOfSpeech.Auxiliary:
            out.append(cur)
            continue
        prev_conjugatable = prev.part_of_speech in {
            PartOfSpeech.Verb,
            PartOfSpeech.IAdjective,
            PartOfSpeech.NaAdjective,
            PartOfSpeech.Auxiliary,
        } or prev.has_section(PartOfSpeechSection.Adjectival)
        cur_not_na_or_ni = cur.text not in {"な", "に"}
        desu_sequence_allowed = cur.dictionary_form != "です" or (
            prev.part_of_speech == PartOfSpeech.Verb and cur.dictionary_form == "です" and cur.text in {"でし", "でした"}
        )
        cur_not_aux_form = cur.dictionary_form not in {"らしい", "べし", "ようだ", "やがる"}
        cur_not_disallowed = cur.text not in {"なら", "だろう"}
        if prev_conjugatable and cur_not_na_or_ni and desu_sequence_allowed and cur_not_aux_form and cur_not_disallowed:
            prev.text += cur.text
        else:
            out.append(cur)
    return out


def combine_auxiliary_verb_stem(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if (
            nxt.has_section(PartOfSpeechSection.AuxiliaryVerbStem)
            and nxt.text not in {"ように", "よう", "みたい"}
            and word_infos[i - 1].part_of_speech in {PartOfSpeech.Verb, PartOfSpeech.IAdjective}
        ):
            current.text += nxt.text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_suffix(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if (nxt.part_of_speech == PartOfSpeech.Suffix or nxt.has_section(PartOfSpeechSection.Suffix)) and (
            nxt.dictionary_form in {"っこ", "さ", "がる"}
            or (nxt.dictionary_form == "ら" and word_infos[i - 1].part_of_speech == PartOfSpeech.Pronoun)
        ):
            current.text += nxt.text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def combine_particles(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    i = 0
    while i < len(word_infos):
        cur = word_infos[i]
        if i + 1 < len(word_infos):
            nxt = word_infos[i + 1]
            combined = ""
            if cur.text == "に" and nxt.text == "は":
                combined = "には"
            elif cur.text == "と" and nxt.text == "は":
                combined = "とは"
            elif cur.text == "で" and nxt.text == "は":
                combined = "では"
            elif cur.text == "の" and nxt.text == "に":
                combined = "のに"
            if combined:
                nw = WordInfo(**cur.__dict__)
                nw.text = combined
                out.append(nw)
                i += 2
                continue
        out.append(WordInfo(**cur.__dict__))
        i += 1
    return out


def combine_final(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    current = WordInfo(**word_infos[0].__dict__)
    for i in range(1, len(word_infos)):
        nxt = word_infos[i]
        if nxt.text == "ば" and word_infos[i - 1].part_of_speech == PartOfSpeech.Verb:
            current.text += nxt.text
        else:
            out.append(current)
            current = WordInfo(**nxt.__dict__)
    out.append(current)
    return out


def separate_suffix_honorifics(word_infos: list[WordInfo]) -> list[WordInfo]:
    if len(word_infos) < _MIN_PAIR_LENGTH:
        return word_infos
    out: list[WordInfo] = []
    for w in word_infos:
        current = WordInfo(**w.__dict__)
        separated = False
        for h in HONORIFICS_SUFFIXES:
            if (
                current.text.endswith(h)
                and len(current.text) > len(h)
                and (current.has_section(PartOfSpeechSection.PersonName) or current.has_section(PartOfSpeechSection.ProperNoun))
            ):
                current.text = current.text[: -len(h)]
                current.dictionary_form = current.dictionary_form.removesuffix(h)
                suffix = WordInfo(text=h, part_of_speech=PartOfSpeech.Suffix, reading=h, dictionary_form=h)
                out.extend((current, suffix))
                separated = True
                break
        if not separated:
            out.append(current)

    return out


def filter_misparse(word_infos: list[WordInfo]) -> list[WordInfo]:
    res = []
    for w in word_infos:
        ww = WordInfo(**w.__dict__)
        if ww.text in {"なん", "フン", "ふん"}:
            ww.part_of_speech = PartOfSpeech.Prefix
        if ww.text == "そう":
            ww.part_of_speech = PartOfSpeech.Adverb
        if ww.text == "おい":
            ww.part_of_speech = PartOfSpeech.Interjection
        if ww.text == "つ" and ww.part_of_speech == PartOfSpeech.Suffix:
            ww.part_of_speech = PartOfSpeech.Counter
        is_loose_kana = (
            (len(ww.text) == 1 and _is_kana_str(ww.text))
            or (len(ww.text) == _DOUBLE_CHAR_LENGTH and _is_kana_str(ww.text[0]) and ww.text[1] == "ー")
            or ww.text in {"エナ", "えな"}
        )
        if ww.text in {"そ", "ー", "る", "ま", "ふ", "ち", "ほ", "す", "じ", "なさ"} or (
            ww.part_of_speech == PartOfSpeech.Noun and is_loose_kana
        ):
            continue
        res.append(ww)
    return res


def _is_kana_str(s: str) -> bool:
    for ch in str(s):
        code = ord(ch)
        if not (_HIRAGANA_START <= code <= _KATAKANA_END or _HALF_KATAKANA_START <= code <= _HALF_KATAKANA_END):
            return False
    return True


def apply_pipeline(word_infos: list[WordInfo], *, morphemes_only: bool = False) -> list[WordInfo]:
    if morphemes_only:
        return word_infos

    w = word_infos
    w = process_special_cases(w)
    w = combine_prefixes(w)
    w = combine_amounts(w)
    w = combine_tte(w)
    w = combine_auxiliary_verb_stem(w)
    w = combine_adverbial_particle(w)
    w = combine_suffix(w)
    w = combine_auxiliary(w)
    w = combine_verb_dependants(w)
    w = combine_verb_possible_dependants(w)
    w = combine_verb_dependants_suru(w)
    w = combine_verb_dependants_teiru(w)
    w = combine_conjunctive_particle(w)
    w = combine_particles(w)
    w = combine_final(w)
    w = separate_suffix_honorifics(w)
    return filter_misparse(w)


# Note: no extra post-pipeline splitting rules here;
