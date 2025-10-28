from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

_ASCII_DIGIT_START = 0x30
_ASCII_DIGIT_END = 0x39
_ASCII_UPPER_START = 0x41
_ASCII_UPPER_END = 0x5A
_ASCII_LOWER_START = 0x61
_ASCII_LOWER_END = 0x7A
_FULLWIDTH_DIGIT_START = 0xFF10
_FULLWIDTH_DIGIT_END = 0xFF19
_FULLWIDTH_UPPER_START = 0xFF21
_FULLWIDTH_UPPER_END = 0xFF3A
_FULLWIDTH_LOWER_START = 0xFF41
_FULLWIDTH_LOWER_END = 0xFF5A
_KATAKANA_START = 0x30A0
_KATAKANA_END = 0x30FF
_KATAKANA_SMALL_START = 0x30A1
_KATAKANA_SMALL_END = 0x30F6
_PROLONGED_SOUND_MARK = 0x30FC
_TERM_ROW_MIN_LENGTH = 7
_PRIORITY_FIELD_INDEX = 7
_DEFINITION_FIELD_INDEX = 5


def _is_katakana(ch: str) -> bool:
    code = ord(ch)
    return (_KATAKANA_START <= code <= _KATAKANA_END) or code == _PROLONGED_SOUND_MARK


def _katakana_to_hiragana(s: str) -> str:
    out = []
    for ch in s:
        code = ord(ch)
        if _KATAKANA_SMALL_START <= code <= _KATAKANA_SMALL_END:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


_HIRA_VOWEL = {
    "あ": "あ",
    "い": "い",
    "う": "う",
    "え": "え",
    "お": "お",
    "か": "あ",
    "き": "い",
    "く": "う",
    "け": "え",
    "こ": "お",
    "さ": "あ",
    "し": "い",
    "す": "う",
    "せ": "え",
    "そ": "お",
    "た": "あ",
    "ち": "い",
    "つ": "う",
    "て": "え",
    "と": "お",
    "な": "あ",
    "に": "い",
    "ぬ": "う",
    "ね": "え",
    "の": "お",
    "は": "あ",
    "ひ": "い",
    "ふ": "う",
    "へ": "え",
    "ほ": "お",
    "ま": "あ",
    "み": "い",
    "む": "う",
    "め": "え",
    "も": "お",
    "や": "あ",
    "ゆ": "う",
    "よ": "お",
    "ら": "あ",
    "り": "い",
    "る": "う",
    "れ": "え",
    "ろ": "お",
    "わ": "あ",
    "ゐ": "い",
    "ゑ": "え",
    "を": "お",
    "が": "あ",
    "ぎ": "い",
    "ぐ": "う",
    "げ": "え",
    "ご": "お",
    "ざ": "あ",
    "じ": "い",
    "ず": "う",
    "ぜ": "え",
    "ぞ": "お",
    "だ": "あ",
    "ぢ": "い",
    "づ": "う",
    "で": "え",
    "ど": "お",
    "ば": "あ",
    "び": "い",
    "ぶ": "う",
    "べ": "え",
    "ぼ": "お",
    "ぱ": "あ",
    "ぴ": "い",
    "ぷ": "う",
    "ぺ": "え",
    "ぽ": "お",
}


def _expand_long_vowels(hira: str) -> str:
    # Replace long vowel mark 'ー' with previous vowel; basic heuristic
    out = []
    prev_vowel = ""
    for ch in hira:
        if ch == "ー":
            if prev_vowel:
                out.append(prev_vowel)
            # else drop
            continue
        out.append(ch)
        # update prev_vowel from this kana
        v = _HIRA_VOWEL.get(ch)
        if v:
            prev_vowel = v
    return "".join(out)


def _looks_english(text: str) -> bool:
    return any(ch.isascii() and ch.isalpha() for ch in text)


def _extract_definitions(raw: object) -> list[str]:
    """Flatten Yomitan structured-content definitions into plain English text lines."""
    collected: list[str] = []

    def walk(node: object, lang: str | None) -> None:
        if isinstance(node, str):
            text = node.strip()
            if text and (lang == "en" or (lang is None and _looks_english(text))):
                collected.append(text)
            return
        if isinstance(node, dict):
            node_lang = node.get("lang", lang)
            data = node.get("data")
            if isinstance(data, dict) and data.get("content") == "formsTable":
                return
            if "text" in node and not isinstance(node["text"], dict):
                walk(node["text"], node_lang)
                return
            if "content" in node:
                walk(node["content"], node_lang)
            return
        if isinstance(node, list):
            for child in node:
                walk(child, lang)

    walk(raw, None)
    seen: set[str] = set()
    unique: list[str] = []
    for text in collected:
        if text not in seen:
            seen.add(text)
            unique.append(text)
    return unique


def to_hiragana_preserve_long(s: str) -> str:
    s = s.replace("ゎ", "わ").replace("ヮ", "わ")
    return _katakana_to_hiragana(s)


def to_hiragana_expand_long(s: str) -> str:
    s = s.replace("ゎ", "わ").replace("ヮ", "わ")
    hira = _katakana_to_hiragana(s)
    return _expand_long_vowels(hira)


@dataclass
class JmWord:
    word_id: int
    readings: set[str] = field(default_factory=set)
    spellings: set[str] = field(default_factory=set)
    parts_of_speech: list[str] = field(default_factory=list)
    priorities: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)

    def get_priority_score(self, *, is_kana: bool) -> int:
        """Port of Jiten's GetPriorityScore with approximations for Yomitan tags.

        - Recognizes: jiten, ichi(=ichi1), ichi1, ichi2, news1*, news2*, gai1/2, nfNN, spec1/2
        - Applies kana bias for 'uk'.
        """
        pr = self.priorities or []
        if not pr:
            pr = []
        score = 0

        # Highest explicit override
        if any(p == "jiten" for p in pr):
            score += 100

        # Ichi
        if any(p in {"ichi1", "ichi"} for p in pr):
            score += 20
        elif any(p == "ichi2" for p in pr):
            score += 10

        # News; Yomitan encodes as news1k/news2k; accept prefix
        if any(p.startswith("news1") for p in pr):
            score += 15
        if any(p.startswith("news2") for p in pr):
            score += 10

        # Gai1/2
        if any(p in {"gai1", "gai2"} for p in pr):
            score += 5

        # nfXX
        for p in pr:
            if p.startswith("nf") and p[2:].isdigit():
                nf_rank = int(p[2:])
                score += max(0, 5 - round(nf_rank / 10.0))
                break

        if score == 0:
            if any(p == "spec1" for p in pr):
                score += 15
            elif any(p == "spec2" for p in pr):
                score += 5

        # Kana bias for 'uk' (usually kana-only)
        if "uk" in self.parts_of_speech:
            score += 10 if is_kana else -10

        return score


@dataclass
class JmDict:
    lookups: dict[str, list[int]]
    words: dict[int, JmWord]


_CACHE: dict[tuple[Path, ...], JmDict] = {}


def load_jmdict(primary_zip: Path) -> JmDict:
    # Discover all JMdict/JMnedict zips in jmdict folder
    base_dir = primary_zip.parent
    zips = sorted([p for p in base_dir.glob("*.zip") if p.name.lower().startswith(("jmdict", "jmnedict"))])
    if not zips:
        zips = [primary_zip]
    cache_key = tuple(sorted(zips))
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    words: dict[int, JmWord] = {}
    lookups: dict[str, list[int]] = {}

    def ingest_zip(path: Path) -> None:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(".json") or not name.startswith("term_bank_"):
                    continue
                data = json.loads(z.read(name))
                for row in data:
                    if not isinstance(row, list) or len(row) < _TERM_ROW_MIN_LENGTH:
                        continue
                    term = row[0] or ""
                    reading = row[1] or ""
                    pos_str = row[2] or ""
                    seq = row[6] if isinstance(row[6], int) else None
                    if seq is None:
                        continue
                    w = words.get(seq)
                    if w is None:
                        w = JmWord(word_id=seq)
                        words[seq] = w
                    if reading:
                        w.readings.add(reading)
                    if term:
                        w.spellings.add(term)
                        # In Jiten DB, spellings are also included in the Readings list
                        w.readings.add(term)
                    for tag in pos_str.split():
                        if tag and tag not in w.parts_of_speech:
                            w.parts_of_speech.append(tag)
                    # Priorities/tags are in optional field 7 as a space-separated string
                    if (
                        len(row) > _PRIORITY_FIELD_INDEX
                        and isinstance(row[_PRIORITY_FIELD_INDEX], str)
                        and row[_PRIORITY_FIELD_INDEX]
                    ):
                        raw = row[_PRIORITY_FIELD_INDEX].strip()
                        # strip decorations like stars
                        raw = raw.replace("⭐", "").strip()
                        for tok in raw.split():
                            t = tok.strip()
                            if not t:
                                continue
                            # normalize some variants present in Yomitan
                            if t == "ichi":
                                t = "ichi1"
                            if t not in w.priorities:
                                w.priorities.append(t)
                    # Definitions/glosses field (structured content)
                    if len(row) > _DEFINITION_FIELD_INDEX and row[_DEFINITION_FIELD_INDEX]:
                        for definition in _extract_definitions(row[_DEFINITION_FIELD_INDEX]):
                            if definition not in w.definitions:
                                w.definitions.append(definition)

    for z in zips:
        ingest_zip(z)

    # Inject Jiten's hardcoded custom words
    _inject_custom_words(words)

    # Build lookup table
    for word_id, w in words.items():
        # spellings as-is
        for s in w.spellings:
            _lk_add(lookups, s, word_id)
            # width variants for ascii/digits
            hw = _to_halfwidth_ascii(s)
            fw = _to_fullwidth_ascii(s)
            if hw != s:
                _lk_add(lookups, hw, word_id)
            if fw != s:
                _lk_add(lookups, fw, word_id)
        # readings variants
        for r in w.readings:
            key1 = to_hiragana_preserve_long(r)
            key2 = to_hiragana_expand_long(r)
            _lk_add(lookups, key1, word_id)
            if key2 != key1:
                _lk_add(lookups, key2, word_id)
            if all(_is_katakana(ch) for ch in r):
                _lk_add(lookups, r, word_id)
            # also add width-normalized forms for ascii/digits that appear as readings
            hw = _to_halfwidth_ascii(r)
            fw = _to_fullwidth_ascii(r)
            if hw != r:
                _lk_add(lookups, hw, word_id)
            if fw != r:
                _lk_add(lookups, fw, word_id)

    jd = JmDict(lookups=lookups, words=words)
    _CACHE[cache_key] = jd
    return jd


def _lk_add(lookups: dict[str, list[int]], key: str, word_id: int) -> None:
    arr = lookups.get(key)
    if arr is None:
        lookups[key] = [word_id]
    elif not arr or arr[-1] != word_id:
        arr.append(word_id)


def _inject_custom_words(words: dict[int, JmWord]) -> None:
    # Port of JmDictHelper.GetCustomWords
    # 8000000: でした (exp)
    w = JmWord(word_id=8000000)
    w.readings.update(["でした"])  # kana reading
    w.spellings.update(["でした"])  # spelling same
    w.parts_of_speech.extend(["exp"])  # expression
    words[w.word_id] = w

    # 8000001: イクシオトキシン (n)
    w = JmWord(word_id=8000001)
    w.readings.update(["イクシオトキシン"])  # katakana
    w.spellings.update(["イクシオトキシン"])  # spelling
    w.parts_of_speech.extend(["n"])  # noun
    words[w.word_id] = w

    # 8000002: 逢魔 / おうま (exp)
    w = JmWord(word_id=8000002)
    w.readings.update(["逢魔", "おうま"])  # reading + kana
    w.spellings.update(["逢魔"])  # spelling (kanji)
    w.parts_of_speech.extend(["exp"])  # expression
    words[w.word_id] = w


def _to_fullwidth_ascii(s: str) -> str:
    # Only transform ASCII letters and digits to fullwidth
    out = []
    for ch in s:
        o = ord(ch)
        if _ASCII_DIGIT_START <= o <= _ASCII_DIGIT_END:
            out.append(chr(_FULLWIDTH_DIGIT_START + (o - _ASCII_DIGIT_START)))
        elif _ASCII_UPPER_START <= o <= _ASCII_UPPER_END:
            out.append(chr(_FULLWIDTH_UPPER_START + (o - _ASCII_UPPER_START)))
        elif _ASCII_LOWER_START <= o <= _ASCII_LOWER_END:
            out.append(chr(_FULLWIDTH_LOWER_START + (o - _ASCII_LOWER_START)))
        else:
            out.append(ch)
    return "".join(out)


def _to_halfwidth_ascii(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if _FULLWIDTH_DIGIT_START <= o <= _FULLWIDTH_DIGIT_END:
            out.append(chr(_ASCII_DIGIT_START + (o - _FULLWIDTH_DIGIT_START)))
        elif _FULLWIDTH_UPPER_START <= o <= _FULLWIDTH_UPPER_END:
            out.append(chr(_ASCII_UPPER_START + (o - _FULLWIDTH_UPPER_START)))
        elif _FULLWIDTH_LOWER_START <= o <= _FULLWIDTH_LOWER_END:
            out.append(chr(_ASCII_LOWER_START + (o - _FULLWIDTH_LOWER_START)))
        else:
            out.append(ch)
    return "".join(out)
