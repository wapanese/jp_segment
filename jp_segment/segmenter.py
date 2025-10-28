from __future__ import annotations

import importlib
import re
from pathlib import Path

from ._ffi import SudachiFFI
from ._utils import detect_system_dic, find_resources_dir, is_romaji_only, to_full_width_digits
from ._wordinfo import WordInfo


class Segmenter:
    def __init__(self, dictionary_path: str | Path | None = None) -> None:
        self._resources = find_resources_dir()
        dic = detect_system_dic(str(dictionary_path) if dictionary_path else None)
        if dic is None:
            msg = "system.dic not found. Set JP_SEGMENT_SYSTEM_DIC or pass dictionary_path."
            raise FileNotFoundError(msg)
        self._dictionary_path = dic
        self._ffi: SudachiFFI | None = None
        self._ensure_backend()

    def _ensure_backend(self) -> None:
        # Prefer native FFI; fall back to SudachiPy
        try:
            self._ffi = SudachiFFI()
        except Exception:
            self._ffi = None

    def _ffi_analyze(self, text: str, *, morphemes_only: bool = False) -> list[WordInfo]:
        assert self._ffi is not None
        config = self._resources / ("sudachi_nouserdic.json" if morphemes_only else "sudachi.json")
        mode = "A" if morphemes_only else "C"
        # Clean like Jiten's interop
        cleaned = re.sub(
            (
                r"[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\uFF21-\uFF3A\uFF41-\uFF5A\uFF10-\uFF19"
                r"\u3005\u3001-\u3003\u3008-\u3011\u3014-\u301F\uFF01-\uFF0F\uFF1A-\uFF1F\uFF3B-\uFF3F"
                r"\uFF5B-\uFF60\uFF62-\uFF65\uFF0E\n\u2026\u3000\u2015\u2500() \u300D]"
            ),
            "",
            to_full_width_digits(text),
        )
        if is_romaji_only(cleaned):
            return []
        out = self._ffi.process_text(config, cleaned, self._dictionary_path, mode=mode, print_all=True, wakati=False)
        lines = [ln for ln in out.split("\n") if ln and ln != "EOS"]
        wis = [WordInfo.from_sudachi_line(ln) for ln in lines]
        return [w for w in wis if not w.is_invalid]

    def _sudachipy_analyze(self, text: str, *, morphemes_only: bool = False) -> list[WordInfo]:
        sudachi_dictionary = importlib.import_module("sudachipy.dictionary")
        sudachi_tokenizer = importlib.import_module("sudachipy.tokenizer")

        cfg = {
            "systemDict": str(self._dictionary_path),
            "characterDefinitionFile": str(self._resources / "char.def"),
            "inputTextPlugin": [
                {"class": "sudachipy.plugin.input_text.DefaultInputTextPlugin"},
                {
                    "class": "sudachipy.plugin.input_text.ProlongedSoundMarkPlugin",
                    "prolongedSoundMarks": [
                        "ー",
                        "-",
                        "\u2053",
                        "\u301c",
                        "\u3030",
                    ],
                    "replacementSymbol": "ー",
                },
                {
                    "class": "sudachipy.plugin.input_text.IgnoreYomiganaPlugin",
                    "leftBrackets": ["(", "\uff08"],
                    "rightBrackets": [")", "\uff09"],
                    "maxYomiganaLength": 4,
                },
            ],
            "oovProviderPlugin": [
                {
                    "class": "sudachipy.plugin.oov.MeCabOovPlugin",
                    "charDef": str(self._resources / "char.def"),
                    "unkDef": str(self._resources / "unk.def"),
                },
                {
                    "class": "sudachipy.plugin.oov.SimpleOovPlugin",
                    "oovPOS": ["補助記号", "一般", "*", "*", "*", "*"],
                    "leftId": 5968,
                    "rightId": 5968,
                    "cost": 3857,
                },
            ],
            "pathRewritePlugin": [
                {"class": "sudachipy.plugin.path_rewrite.JoinNumericPlugin", "enableNormalize": True},
                {
                    "class": "sudachipy.plugin.path_rewrite.JoinKatakanaOovPlugin",
                    "oovPOS": ["名詞", "普通名詞", "一般", "*", "*", "*"],
                    "minLength": 3,
                },
            ],
            "userDict": [] if morphemes_only else [str(self._resources / "user_dic.dic")],
        }

        tokenizer = sudachi_dictionary.Dictionary(dict_type=None, config_path_or_dict=cfg).create()
        mode = getattr(sudachi_tokenizer.Tokenizer.SplitMode, "A" if morphemes_only else "C")
        tokens = tokenizer.tokenize(mode, text)
        wis: list[WordInfo] = []
        for t in tokens:
            pos = list(t.part_of_speech())
            wis.append(
                WordInfo.from_fields(
                    surface=t.surface(),
                    pos=pos,
                    normalized=t.normalized_form(),
                    dictionary=t.dictionary_form(),
                    reading=t.reading_form() or "",
                )
            )
        return wis

    def segment(self, text: str, dictionary_path: str | Path | None = None) -> list[str]:
        from .parser_port import ParserPort

        segmenter_for_parser = self if dictionary_path is None else self.__class__(dictionary_path=dictionary_path)
        parser = ParserPort(segmenter=segmenter_for_parser)
        return parser.parse_text_tokens(text)


# No post-segmentation adapters: output is driven by JMdict anchoring + gaps


def segment(text: str, dictionary_path: str | Path | None = None) -> list[str]:
    return Segmenter(dictionary_path=dictionary_path).segment(text)
