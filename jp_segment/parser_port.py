from __future__ import annotations

import importlib
import os
import re
import sys
from dataclasses import dataclass

from ._analyzer import apply_pipeline, preprocess_text
from ._types import PartOfSpeech, PartOfSpeechSection, to_part_of_speech
from ._utils import find_resources_dir
from ._wordinfo import WordInfo
from .deconjugator import Deconjugator
from .jmdict_loader import JmDict, JmWord, load_jmdict, to_hiragana_expand_long, to_hiragana_preserve_long
from .segmenter import Segmenter

_CLEAN_RE = re.compile(
    r"[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\uFF21-\uFF3A\uFF41-\uFF5A"
    r"\uFF10-\uFF19\u3005\uFF0E]"
)

_FULLWIDTH_LOWER_A = "\uff41"
_FULLWIDTH_LOWER_Z = "\uff5a"
_FULLWIDTH_UPPER_A = "\uff21"
_FULLWIDTH_UPPER_Z = "\uff3a"
_HIRAGANA_OR_KATAKANA_START = 0x3040
_HIRAGANA_OR_KATAKANA_END = 0x30FF
_LONG_VOWEL_MARK = 0x30FC
_MAX_DECONJ_ATTEMPTS = 3
_MIN_TRIM_LENGTH = 2
_READING_FORM_INDEX = 4


@dataclass
class DeckWord:
    word_id: int
    original_text: str
    reading_index: int
    parts_of_speech: list[PartOfSpeech]


class ParserPort:
    def __init__(self, segmenter: Segmenter | None = None) -> None:
        self._resources = find_resources_dir()
        # Load deconjugator rules
        self._deconjugator = Deconjugator(self._resources / "deconjugator.json")
        # Load JMdict (Yomitan) zip from package resources
        jmdict_dir = self._resources / "jmdict"
        jmdict_zip = jmdict_dir / "JMdict_english.zip"
        if not jmdict_zip.exists():
            # fallback to legacy if primary archive missing
            jmdict_zip = jmdict_dir / "JMdict_english_legacy.zip"
        if not jmdict_zip.exists():
            msg = f"JMdict archive not found in resources: {jmdict_dir}"
            raise FileNotFoundError(msg)
        self._jmdict: JmDict = load_jmdict(jmdict_zip)
        self._segmenter = segmenter if segmenter is not None else Segmenter()
        # Debug controls (env-driven)
        self._dbg_enabled = _env_truthy("JP_SEGMENT_DEBUG")
        self._dbg_exact: str | None = os.getenv("JP_SEGMENT_DEBUG_EXACT")
        self._dbg_contains: str | None = os.getenv("JP_SEGMENT_DEBUG_CONTAINS")
        self._dbg_context: str | None = None

    # --- debug helpers ---
    def _should_dbg(self, text: str) -> bool:
        if not self._dbg_enabled:
            return False
        if self._dbg_exact is not None and text != self._dbg_exact:
            return False
        return not (self._dbg_contains is not None and self._dbg_contains not in text)

    def _dbg(self, *args: object) -> None:
        if self._dbg_enabled and (self._dbg_context is None or self._should_dbg(self._dbg_context)):
            print("[JP-SEGMENT DEBUG]", *args, file=sys.stderr)

    def parse_text_tokens(self, text: str) -> list[str]:
        # Set debug context
        self._dbg_context = text
        if self._should_dbg(text):
            self._dbg("TEXT:", repr(text))

        # Step 1: morphological analysis via Segmenter internals
        seg = self._segmenter
        pre = preprocess_text(text)
        if self._should_dbg(text):
            self._dbg("PREPROCESSED:", repr(pre))
        wis = seg._ffi_analyze(pre, morphemes_only=False) if seg._ffi else seg._sudachipy_analyze(pre, morphemes_only=False)
        if self._should_dbg(text):
            self._dbg("MORPHS:", [(w.text, w.part_of_speech.name, w.dictionary_form) for w in wis])
        wis = apply_pipeline(wis, morphemes_only=False)
        if self._should_dbg(text):
            self._dbg("POST-PIPELINE:", [(w.text, w.part_of_speech.name, w.dictionary_form) for w in wis])

        # Step 2: clean as in Parser.ParseText
        cleaned: list[WordInfo] = []
        for w in wis:
            t = _CLEAN_RE.sub("", w.text)
            if not t:
                continue
            t = t.replace("ッー", "")
            if t:
                nw = WordInfo(**w.__dict__)
                nw.text = t
                cleaned.append(nw)
        if self._should_dbg(text):
            self._dbg("CLEANED:", [(w.text, w.part_of_speech.name, w.dictionary_form) for w in cleaned])

        # Step 3: process each word and collect deck words
        processed: list[DeckWord] = []
        for w in cleaned:
            if self._should_dbg(text):
                self._dbg("PROCESS:", w.text, "POS=", w.part_of_speech.name, "DICT=", w.dictionary_form)
            dw = self._process_word(w)
            if dw is not None:
                processed.append(dw)
                if self._should_dbg(text):
                    self._dbg(" ANCHORED:", (dw.original_text, dw.word_id, dw.reading_index))
            elif self._should_dbg(text):
                self._dbg(" NO-ANCHOR:", w.text)

        # Step 4: Rebuild tokens from anchored words + plain gaps
        tokens: list[str] = []
        current = 0
        for dw, pos in self._words_with_positions(processed, text):
            if pos > current:
                tokens.append(text[current:pos])
            tokens.append(dw.original_text)
            current = pos + len(dw.original_text)
        if current < len(text):
            tokens.append(text[current:])
        if self._should_dbg(text):
            self._dbg("TOKENS:", tokens)
        return tokens

    @staticmethod
    def _words_with_positions(processed: list[DeckWord], text: str) -> list[tuple[DeckWord, int]]:
        out: list[tuple[DeckWord, int]] = []
        current = 0
        for w in processed:
            pos = text.find(w.original_text, current)
            if pos >= 0:
                out.append((w, pos))
                current = pos + len(w.original_text)
        return out

    def _process_word(self, w: WordInfo) -> DeckWord | None:
        """Mirror Parser.ProcessWord fallback behavior.

        We repeatedly attempt to anchor the word. On failure, we apply
        fallback simplifications (trim trailing small tsu/long mark/duplicate,
        drop leading honorific 「お」, strip long vowel marks) and retry.

        We also try POS fallbacks (noun⇄verb/adjective).
        """
        # Work on a mutable copy
        cur = WordInfo(**w.__dict__)

        def try_process(cur_w: WordInfo) -> DeckWord | None:
            # Primary path chosen by part of speech
            if (
                cur_w.part_of_speech
                in {PartOfSpeech.Verb, PartOfSpeech.IAdjective, PartOfSpeech.Auxiliary, PartOfSpeech.NaAdjective}
                or cur_w.pos1 == PartOfSpeechSection.Adjectival
            ):
                _ok, dw = self._deconjugate_verb_or_adjective(cur_w)
                if dw is not None:
                    return dw
                # Try as noun if verb/adjective path failed
                _ok2, dw2 = self._deconjugate_word(cur_w)
                return dw2
            _ok, dw = self._deconjugate_word(cur_w)
            if dw is not None:
                return dw
            # Try verb/adjective interpretations if noun path failed
            old_pos = cur_w.part_of_speech
            for alt in (PartOfSpeech.Verb, PartOfSpeech.IAdjective, PartOfSpeech.NaAdjective):
                cur_w.part_of_speech = alt
                _ok2, dw2 = self._deconjugate_verb_or_adjective(cur_w)
                if dw2 is not None:
                    # Restore POS on the object we return to keep original POS in DeckWord parts list
                    cur_w.part_of_speech = old_pos
                    return dw2
            cur_w.part_of_speech = old_pos
            return None

        # Retry loop with bounded attempts
        attempts = 0
        original_surface = w.text
        while attempts < _MAX_DECONJ_ATTEMPTS:
            attempts += 1
            if self._should_dbg(self._dbg_context or ""):
                self._dbg(f"TRY attempt={attempts} text={cur.text} pos={cur.part_of_speech.name}")
            dw = try_process(cur)
            if dw is not None:
                # Preserve the original morphological token as output surface,
                # even if anchoring used a simplified fallback form.
                dw.original_text = original_surface
                return dw

            # Fallback transforms when no match was found
            t = cur.text
            # 1) Trim last char if len>2 and last is っ or ー or duplicate of previous
            if len(t) > _MIN_TRIM_LENGTH and (t[-1] in {"っ", "ー"} or (len(t) >= _MIN_TRIM_LENGTH and t[-1] == t[-2])):
                if self._should_dbg(self._dbg_context or ""):
                    self._dbg(" Fallback: trim-last", repr(t[-1]), "->", repr(t[:-1]))
                cur.text = t[:-1]
                continue
            # 2) Drop honorific お- prefix
            if t.startswith("お"):
                if self._should_dbg(self._dbg_context or ""):
                    self._dbg(" Fallback: drop-honorific 'お' ->", repr(t[1:]))
                cur.text = t[1:]
                continue
            # 3) Remove all long vowel marks if present
            if "ー" in t:
                if self._should_dbg(self._dbg_context or ""):
                    self._dbg(" Fallback: remove-long-marks ->", repr(t.replace("ー", "")))
                cur.text = t.replace("ー", "")
                continue
            # Nothing else to try
            break

        return None

    def _deconjugate_word(self, w: WordInfo) -> tuple[bool, DeckWord | None]:
        text = w.text
        # DEBUG: uncomment for deep tracing
        if self._should_dbg(self._dbg_context or ""):
            self._dbg(" _deconjugate_word ENTER", text, "POS=", w.part_of_speech.name)
        if text.isdigit() or (len(text) == 1 and is_ascii_or_fullwidth_letter(text)):
            return False, None
        cands = self._jmdict.lookups.get(text, [])
        # try kana-normalized key
        hira = to_hiragana_preserve_long(text)
        cands_h = self._jmdict.lookups.get(hira, [])
        if cands_h:
            # merge de-duped
            cands = sorted(set(cands) | set(cands_h))
        if self._should_dbg(self._dbg_context or ""):
            self._dbg("  candidates(words):", len(cands))
        if not cands:
            return False, None
        # Fetch words
        words = {wid: self._jmdict.words[wid] for wid in cands if wid in self._jmdict.words}
        if self._should_dbg(self._dbg_context or ""):
            self._dbg("  words-loaded:", len(words))
        if not words:
            return False, None
        # select matches by POS
        matches: list[JmWord] = []
        for wid in cands:
            jw = words.get(wid)
            if not jw:
                continue
            pos = [to_part_of_speech(p) for p in jw.parts_of_speech]
            if w.part_of_speech in pos:
                matches.append(jw)
        if self._should_dbg(self._dbg_context or ""):
            self._dbg("  pos-matches:", len(matches))
        if matches:
            # highest priority first
            is_kana = _is_kana(text)
            matches.sort(key=lambda m: m.get_priority_score(is_kana=is_kana), reverse=True)
            jm = matches[0]
        else:
            # fallback to first candidate
            jm = words.get(cands[0])
            if not jm:
                return True, None
        # resolve reading index
        idx = self._compute_reading_index(jm, text)
        if idx is None:
            return False, None
        # print('DBG noun ok', text, '->', jm.word_id, 'idx', idx)
        return True, DeckWord(word_id=jm.word_id, original_text=w.text, reading_index=idx, parts_of_speech=[w.part_of_speech])

    def _deconjugate_verb_or_adjective(self, w: WordInfo) -> tuple[bool, DeckWord | None]:
        # deconjugate the surface converted to hiragana,
        # not Sudachi's reading (prevents numbers mapping to unrelated words).
        hira = to_hiragana_expand_long(w.text)
        forms = sorted(self._deconjugator.deconjugate(hira), key=lambda f: len(f.text), reverse=True)
        if self._should_dbg(self._dbg_context or ""):
            self._dbg(" _deconj_verb/adj forms:", [f.text for f in forms[:10]], "(total=", len(forms), ")")
        candidates: list[tuple[str, list[int]]] = []
        for f in forms:
            ids = self._jmdict.lookups.get(f.text)
            if ids:
                candidates.append((f.text, ids))
        if self._should_dbg(self._dbg_context or ""):
            self._dbg("  candidates(forms):", [(k, len(v)) for k, v in candidates[:10]], "(total=", len(candidates), ")")
        if not candidates:
            return True, None
        # prefer base dictionary form
        base_dict = to_hiragana_preserve_long(w.dictionary_form or w.text)
        base_word = to_hiragana_preserve_long(w.text)

        def lift(key: str) -> int:
            if key == base_dict:
                return 0
            if key == base_word:
                return 1
            return 2

        candidates.sort(key=lambda x: lift(x[0]))
        all_ids: list[int] = []
        for _, ids in candidates:
            for i in ids:
                if i not in all_ids:
                    all_ids.append(i)
        words = {wid: self._jmdict.words[wid] for wid in all_ids if wid in self._jmdict.words}
        matches: list[tuple[JmWord, str]] = []
        for key, ids in candidates:
            for wid in ids:
                jw = words.get(wid)
                if not jw:
                    continue
                pos = [to_part_of_speech(p) for p in jw.parts_of_speech]
                if w.part_of_speech in pos:
                    matches.append((jw, key))
        if not matches:
            return False, None
        best = matches[0]
        if self._should_dbg(self._dbg_context or ""):
            self._dbg("  match: id=", best[0].word_id, "key=", best[1])
        idx = self._compute_reading_index(best[0], best[1])
        if idx is None:
            idx = 0
        return True, DeckWord(
            word_id=best[0].word_id, original_text=w.text, reading_index=idx, parts_of_speech=[w.part_of_speech]
        )

    def _surface_reading(self, surface: str) -> str:
        # Tokenize the surface and join reading forms
        if self._segmenter._ffi is not None:
            out = self._segmenter._ffi.process_text(
                self._segmenter._resources / "sudachi.json",
                surface,
                self._segmenter._dictionary_path,
                mode="C",
                print_all=True,
                wakati=False,
            )
            lines = [ln for ln in out.split("\n") if ln and ln != "EOS"]
            readings: list[str] = []
            for ln in lines:
                parts = ln.split("\t")
                if len(parts) > _READING_FORM_INDEX:
                    readings.append(parts[_READING_FORM_INDEX])
            return "".join(readings)
        # SudachiPy
        sudachi_dictionary = importlib.import_module("sudachipy.dictionary")
        sudachi_tokenizer = importlib.import_module("sudachipy.tokenizer")
        tokenizer = sudachi_dictionary.Dictionary().create()
        mode = sudachi_tokenizer.Tokenizer.SplitMode.C
        tokens = tokenizer.tokenize(mode, surface)
        return "".join(t.reading_form() or "" for t in tokens)

    @staticmethod
    def _compute_reading_index(jm: JmWord, surface_or_reading: str) -> int | None:
        readings = list(jm.readings)
        # Debug: ensure behavior consistent (can be toggled by commenting)
        # print('CRI readings', readings, 'query', surface_or_reading)
        # exact spelling
        try:
            return readings.index(surface_or_reading)
        except ValueError:
            pass
        hira_key = to_hiragana_preserve_long(surface_or_reading)
        hira_readings = [to_hiragana_preserve_long(r) for r in readings]
        try:
            return hira_readings.index(hira_key)
        except ValueError:
            pass
        hira_key2 = to_hiragana_expand_long(surface_or_reading)
        hira_readings2 = [to_hiragana_expand_long(r) for r in readings]
        try:
            return hira_readings2.index(hira_key2)
        except ValueError:
            return None

    @staticmethod
    def _anchor_subwords(_w: WordInfo) -> list[DeckWord]:
        return []


def is_ascii_or_fullwidth_letter(s: str) -> bool:
    c = s[0]
    return (
        ("a" <= c <= "z")
        or ("A" <= c <= "Z")
        or (_FULLWIDTH_LOWER_A <= c <= _FULLWIDTH_LOWER_Z)
        or (_FULLWIDTH_UPPER_A <= c <= _FULLWIDTH_UPPER_Z)
    )


def _is_kana(s: str) -> bool:
    for ch in s:
        o = ord(ch)
        if not (_HIRAGANA_OR_KATAKANA_START <= o <= _HIRAGANA_OR_KATAKANA_END or o == _LONG_VOWEL_MARK):
            return False
    return True


def _env_truthy(name: str) -> bool:
    v = os.getenv(name)
    if v is None:
        return False
    v = v.strip().lower()
    return v in {"1", "true", "yes", "on"}
