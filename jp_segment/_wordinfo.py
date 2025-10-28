from __future__ import annotations

from dataclasses import dataclass

from ._types import PartOfSpeech, PartOfSpeechSection, to_part_of_speech, to_pos_section

_SUDACHI_MIN_FIELDS = 6
_POS_PARTS_MIN = 4
_READING_FIELD_INDEX = 4
_POS_INDEX_SECOND = 1
_POS_INDEX_THIRD = 2
_POS_INDEX_FOURTH = 3


@dataclass
class WordInfo:
    text: str = ""
    part_of_speech: PartOfSpeech = PartOfSpeech.Unknown
    pos1: PartOfSpeechSection = PartOfSpeechSection.None_
    pos2: PartOfSpeechSection = PartOfSpeechSection.None_
    pos3: PartOfSpeechSection = PartOfSpeechSection.None_
    normalized_form: str = ""
    dictionary_form: str = ""
    reading: str = ""
    is_invalid: bool = False

    @classmethod
    def from_sudachi_line(cls, line: str) -> WordInfo:
        parts = line.split("\t")
        if len(parts) < _SUDACHI_MIN_FIELDS:
            return cls(is_invalid=True)
        pos_parts = parts[1].split(",")
        if len(pos_parts) < _POS_PARTS_MIN:
            return cls(is_invalid=True)
        reading = parts[_READING_FIELD_INDEX] if len(parts) > _READING_FIELD_INDEX else ""
        return cls(
            text=parts[0],
            part_of_speech=to_part_of_speech(pos_parts[0]),
            pos1=to_pos_section(pos_parts[_POS_INDEX_SECOND]),
            pos2=to_pos_section(pos_parts[_POS_INDEX_THIRD]),
            pos3=to_pos_section(pos_parts[_POS_INDEX_FOURTH]),
            normalized_form=parts[2],
            dictionary_form=parts[3],
            reading=reading,
        )

    @classmethod
    def from_fields(
        cls,
        surface: str,
        pos: list[str],
        normalized: str,
        dictionary: str,
        reading: str,
    ) -> WordInfo:
        # pos is expected to be length >= 4
        p0 = to_part_of_speech(pos[0]) if pos else PartOfSpeech.Unknown
        p1 = to_pos_section(pos[_POS_INDEX_SECOND]) if len(pos) > _POS_INDEX_SECOND else PartOfSpeechSection.None_
        p2 = to_pos_section(pos[_POS_INDEX_THIRD]) if len(pos) > _POS_INDEX_THIRD else PartOfSpeechSection.None_
        p3 = to_pos_section(pos[_POS_INDEX_FOURTH]) if len(pos) > _POS_INDEX_FOURTH else PartOfSpeechSection.None_
        return cls(
            text=surface,
            part_of_speech=p0,
            pos1=p1,
            pos2=p2,
            pos3=p3,
            normalized_form=normalized,
            dictionary_form=dictionary,
            reading=reading,
        )

    def has_section(self, s: PartOfSpeechSection) -> bool:
        return s in {self.pos1, self.pos2, self.pos3}
