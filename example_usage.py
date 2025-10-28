from __future__ import annotations

from dataclasses import dataclass

from jp_segment import segment
from jp_segment._analyzer import apply_pipeline, preprocess_text
from jp_segment._wordinfo import WordInfo
from jp_segment.parser_port import _CLEAN_RE, DeckWord, ParserPort
from jp_segment.segmenter import Segmenter


@dataclass(frozen=True)
class MatchResult:
    surface: str
    start_index: int
    word_id: int
    spellings: list[str]
    readings: list[str]
    analyzer_parts_of_speech: list[str]
    dictionary_parts_of_speech: list[str]
    definitions: list[str]


def collect_matches(text: str) -> list[MatchResult]:
    parser = ParserPort()
    segmenter = Segmenter()

    preprocessed = preprocess_text(text)
    word_infos = (
        segmenter._ffi_analyze(preprocessed, morphemes_only=False)
        if segmenter._ffi
        else segmenter._sudachipy_analyze(preprocessed, morphemes_only=False)
    )
    word_infos = apply_pipeline(word_infos, morphemes_only=False)

    cleaned: list[WordInfo] = []
    for info in word_infos:
        cleaned_text = _CLEAN_RE.sub("", info.text).replace("ッー", "")
        if not cleaned_text:
            continue
        copy_info = WordInfo(**info.__dict__)
        copy_info.text = cleaned_text
        cleaned.append(copy_info)

    processed: list[DeckWord] = []
    for info in cleaned:
        deck_word = parser._process_word(info)
        if deck_word is not None:
            processed.append(deck_word)

    matches: list[MatchResult] = []
    for deck_word, start_index in parser._words_with_positions(processed, text):
        jm_word = parser._jmdict.words.get(deck_word.word_id)
        if jm_word is None:
            continue
        matches.append(
            MatchResult(
                surface=text[start_index : start_index + len(deck_word.original_text)],
                start_index=start_index,
                word_id=jm_word.word_id,
                spellings=sorted(jm_word.spellings),
                readings=sorted(jm_word.readings),
                analyzer_parts_of_speech=sorted(pos.name for pos in deck_word.parts_of_speech),
                dictionary_parts_of_speech=list(jm_word.parts_of_speech),
                definitions=list(jm_word.definitions),
            )
        )
    return matches


def main() -> None:
    text = "図書館で本を借りました。"
    tokens = segment(text)
    print("Tokens:", tokens)

    matches = collect_matches(text)
    if matches:
        print("Matched dictionary entries:")
        for match in matches:
            spellings = ", ".join(match.spellings) or "<none>"
            readings = ", ".join(match.readings) or "<none>"
            analyzer_pos = ", ".join(match.analyzer_parts_of_speech) or "<unknown>"
            dictionary_pos = ", ".join(match.dictionary_parts_of_speech) or "<none>"
            definitions = "; ".join(match.definitions) or "<none>"
            print(
                f"  - '{match.surface}' (index {match.start_index}) -> word_id={match.word_id}, "
                f"spellings=[{spellings}], readings=[{readings}], "
                f"analyzer_pos=[{analyzer_pos}], dictionary_pos=[{dictionary_pos}], "
                f"definitions=[{definitions}]"
            )
    else:
        print("No dictionary matches were found.")


if __name__ == "__main__":
    main()
