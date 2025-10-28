from __future__ import annotations

from enum import IntEnum


class PartOfSpeech(IntEnum):
    Unknown = 0
    Noun = 1
    Verb = 2
    IAdjective = 3
    Adverb = 4
    Particle = 5
    Conjunction = 6
    Auxiliary = 7
    Adnominal = 8
    Interjection = 9
    Symbol = 10
    Prefix = 11
    Filler = 12
    Name = 13
    Pronoun = 14
    NaAdjective = 15
    Suffix = 16
    CommonNoun = 17
    SupplementarySymbol = 18
    BlankSpace = 19
    Expression = 20
    NominalAdjective = 21
    Numeral = 22
    PrenounAdjectival = 23
    Counter = 24
    AdverbTo = 25
    NounSuffix = 26


class PartOfSpeechSection(IntEnum):
    None_ = 0
    Amount = 1
    Alphabet = 2
    FullStop = 3
    BlankSpace = 4
    Suffix = 5
    Pronoun = 6
    Independant = 7
    Dependant = 8
    Filler = 9
    Common = 10
    SentenceEndingParticle = 11
    Counter = 12
    ParallelMarker = 13
    BindingParticle = 14
    PotentialAdverb = 15
    CaseMarkingParticle = 16
    IrregularConjunction = 17
    ConjunctionParticle = 18
    AuxiliaryVerbStem = 19
    AdjectivalStem = 20
    CompoundWord = 21
    Quotation = 22
    NounConjunction = 23
    AdverbialParticle = 24
    ConjunctiveParticleClass = 25
    Adverbialization = 26
    AdverbialParticleOrParallelMarkerOrSentenceEndingParticle = 27
    AdnominalAdjective = 28
    ProperNoun = 29
    Special = 30
    VerbConjunction = 31
    PersonName = 32
    FamilyName = 33
    Organization = 34
    NotAdjectiveStem = 35
    Comma = 36
    OpeningBracket = 37
    ClosingBracket = 38
    Region = 39
    Country = 40
    Numeral = 41
    PossibleDependant = 42
    CommonNoun = 43
    SubstantiveAdjective = 44
    PossibleCounterWord = 45
    PossibleSuru = 46
    Juntaijoushi = 47
    PossibleNaAdjective = 48
    VerbLike = 49
    PossibleVerbSuruNoun = 50
    Adjectival = 51
    NaAdjectiveLike = 52
    Name = 53
    Letter = 54
    PlaceName = 55
    TaruAdjective = 56


def to_part_of_speech(pos: str) -> PartOfSpeech:
    p = pos
    if p in {"名詞", "n"}:
        return PartOfSpeech.Noun
    if p == "動詞" or p.startswith("v"):
        return PartOfSpeech.Verb
    if p in {"形容詞", "adj-i", "adj-ix"}:
        return PartOfSpeech.IAdjective
    if p in {"形状詞", "adj-na"}:
        return PartOfSpeech.NaAdjective
    if p in {"副詞", "adv"}:
        return PartOfSpeech.Adverb
    if p in {"助詞", "prt"}:
        return PartOfSpeech.Particle
    if p in {"接続詞", "conj"}:
        return PartOfSpeech.Conjunction
    if p in {"助動詞", "aux", "aux-v"}:
        return PartOfSpeech.Auxiliary
    if p in {"感動詞", "int"}:
        return PartOfSpeech.Interjection
    if p == "記号":
        return PartOfSpeech.Symbol
    if p in {"接頭詞", "接頭辞", "pref"}:
        return PartOfSpeech.Prefix
    if p == "フィラー":
        return PartOfSpeech.Filler
    if p in {
        "名",
        "company",
        "given",
        "place",
        "person",
        "product",
        "ship",
        "surname",
        "unclass",
        "name-fem",
        "name-masc",
        "station",
        "group",
        "char",
        "creat",
        "dei",
        "doc",
        "ev",
        "fem",
        "fict",
        "leg",
        "masc",
        "myth",
        "obj",
        "organization",
        "oth",
        "relig",
        "serv",
        "work",
        "unc",
    }:
        return PartOfSpeech.Name
    if p in {"代名詞", "pn"}:
        return PartOfSpeech.Pronoun
    if p in {"接尾辞", "suf"}:
        return PartOfSpeech.Suffix
    if p == "普通名詞":
        return PartOfSpeech.CommonNoun
    if p == "補助記号":
        return PartOfSpeech.SupplementarySymbol
    if p == "空白":
        return PartOfSpeech.BlankSpace
    if p in {"表現", "exp"}:
        return PartOfSpeech.Expression
    if p in {"形動", "adj-no", "adj-t", "adj-f"}:
        return PartOfSpeech.NominalAdjective
    if p in {"連体詞", "adj-pn"}:
        return PartOfSpeech.PrenounAdjectival
    if p in {"数詞", "num"}:
        return PartOfSpeech.Numeral
    if p in {"助数詞", "ctr"}:
        return PartOfSpeech.Counter
    if p in {"副詞的と", "adv-to"}:
        return PartOfSpeech.AdverbTo
    if p in {"名詞接尾辞", "n-suf"}:
        return PartOfSpeech.NounSuffix
    return PartOfSpeech.Unknown


def to_pos_section(pos: str) -> PartOfSpeechSection:
    p = pos
    if p == "*":
        return PartOfSpeechSection.None_
    if p == "数":
        return PartOfSpeechSection.Amount
    if p == "アルファベット":
        return PartOfSpeechSection.Alphabet
    if p == "句点":
        return PartOfSpeechSection.FullStop
    if p == "空白":
        return PartOfSpeechSection.BlankSpace
    if p in {"接尾", "suf"}:
        return PartOfSpeechSection.Suffix
    if p in {"代名詞", "pn"}:
        return PartOfSpeechSection.Pronoun
    if p == "自立":
        return PartOfSpeechSection.Independant
    if p == "フィラー":
        return PartOfSpeechSection.Filler
    if p == "一般":
        return PartOfSpeechSection.Common
    if p == "非自立":
        return PartOfSpeechSection.Dependant
    if p == "終助詞":
        return PartOfSpeechSection.SentenceEndingParticle
    if p in {"助数詞", "ctr"}:
        return PartOfSpeechSection.Counter
    if p == "並立助詞":
        return PartOfSpeechSection.ParallelMarker
    if p == "係助詞":
        return PartOfSpeechSection.BindingParticle
    if p == "副詞可能":
        return PartOfSpeechSection.PotentialAdverb
    if p == "格助詞":
        return PartOfSpeechSection.CaseMarkingParticle
    if p == "サ変接続":
        return PartOfSpeechSection.IrregularConjunction
    if p == "接続助詞":
        return PartOfSpeechSection.ConjunctionParticle
    if p == "助動詞語幹":
        return PartOfSpeechSection.AuxiliaryVerbStem
    if p == "形容動詞語幹":
        return PartOfSpeechSection.AdjectivalStem
    if p == "連語":
        return PartOfSpeechSection.CompoundWord
    if p == "引用":
        return PartOfSpeechSection.Quotation
    if p == "名詞接続":
        return PartOfSpeechSection.NounConjunction
    if p == "副助詞":
        return PartOfSpeechSection.AdverbialParticle
    if p == "助詞類接続":
        return PartOfSpeechSection.ConjunctiveParticleClass
    if p == "副詞化":
        return PartOfSpeechSection.Adverbialization
    if p == "副助詞\uff0f並立助詞\uff0f終助詞":
        return PartOfSpeechSection.AdverbialParticleOrParallelMarkerOrSentenceEndingParticle
    if p == "連体化":
        return PartOfSpeechSection.AdnominalAdjective
    if p == "固有名詞":
        return PartOfSpeechSection.ProperNoun
    if p == "特殊":
        return PartOfSpeechSection.Special
    if p == "動詞接続":
        return PartOfSpeechSection.VerbConjunction
    if p == "人名":
        return PartOfSpeechSection.PersonName
    if p == "姓":
        return PartOfSpeechSection.FamilyName
    if p == "組織":
        return PartOfSpeechSection.Organization
    if p == "ナイ形容詞語幹":
        return PartOfSpeechSection.NotAdjectiveStem
    if p == "読点":
        return PartOfSpeechSection.Comma
    if p == "括弧開":
        return PartOfSpeechSection.OpeningBracket
    if p == "括弧閉":
        return PartOfSpeechSection.ClosingBracket
    if p == "地域":
        return PartOfSpeechSection.Region
    if p == "国":
        return PartOfSpeechSection.Country
    if p in {"数詞", "num"}:
        return PartOfSpeechSection.Numeral
    if p == "非自立可能":
        return PartOfSpeechSection.PossibleDependant
    if p == "普通名詞":
        return PartOfSpeechSection.CommonNoun
    if p == "名詞的":
        return PartOfSpeechSection.SubstantiveAdjective
    if p == "助数詞可能":
        return PartOfSpeechSection.PossibleCounterWord
    if p == "サ変可能":
        return PartOfSpeechSection.PossibleSuru
    if p == "準体助詞":
        return PartOfSpeechSection.Juntaijoushi
    if p == "形状詞可能":
        return PartOfSpeechSection.PossibleNaAdjective
    if p == "動詞的":
        return PartOfSpeechSection.VerbLike
    if p == "サ変形状詞可能":
        return PartOfSpeechSection.PossibleVerbSuruNoun
    if p == "形容詞的":
        return PartOfSpeechSection.Adjectival
    if p == "名":
        return PartOfSpeechSection.Name
    if p == "文字":
        return PartOfSpeechSection.Letter
    if p == "形状詞的":
        return PartOfSpeechSection.NaAdjectiveLike
    if p == "地名":
        return PartOfSpeechSection.PlaceName
    if p == "タリ":
        return PartOfSpeechSection.TaruAdjective
    return PartOfSpeechSection.None_
