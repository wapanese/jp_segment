from __future__ import annotations

import os
import platform
from pathlib import Path

_HIRAGANA_START = 0x3040
_HIRAGANA_END = 0x309F
_KATAKANA_START = 0x30A0
_KATAKANA_END = 0x30FF
_CJK_UNIFIED_START = 0x4E00
_CJK_UNIFIED_END = 0x9FAF
_HALF_KATAKANA_START = 0xFF66
_HALF_KATAKANA_END = 0xFF9D


def to_full_width_digits(text: str) -> str:
    mapping = str.maketrans(
        {
            "0": "\uff10",
            "1": "\uff11",
            "2": "\uff12",
            "3": "\uff13",
            "4": "\uff14",
            "5": "\uff15",
            "6": "\uff16",
            "7": "\uff17",
            "8": "\uff18",
            "9": "\uff19",
        }
    )
    return text.translate(mapping)


def is_romaji_only(text: str) -> bool:
    # Conservative: true if no hiragana/katakana/kanji present
    for ch in text:
        code = ord(ch)
        if (
            _HIRAGANA_START <= code <= _HIRAGANA_END  # Hiragana
            or _KATAKANA_START <= code <= _KATAKANA_END  # Katakana
            or _CJK_UNIFIED_START <= code <= _CJK_UNIFIED_END  # CJK Unified Ideographs
            or _HALF_KATAKANA_START <= code <= _HALF_KATAKANA_END  # Halfwidth Katakana
        ):
            return False
    return True


def platform_lib_name() -> str | None:
    sys = platform.system().lower()
    if sys.startswith("win"):
        return "sudachi_lib.dll"
    if sys == "linux":
        return "libsudachi_lib.so"
    return None


def find_resources_dir() -> Path:
    """Return the package-local resources directory."""
    resources = Path(__file__).resolve().parent / "resources"
    if not resources.exists():
        msg = f"Resource directory missing: {resources}"
        raise FileNotFoundError(msg)
    return resources


def detect_system_dic(explicit: str | None = None) -> Path | None:
    """Resolve the Sudachi system dictionary location."""
    if explicit:
        path = Path(explicit)
        return path if path.exists() else None
    env_var = os.getenv("JP_SEGMENT_SYSTEM_DIC")
    if env_var:
        path = Path(env_var)
        if path.exists():
            return path
    resources = find_resources_dir()
    dic = resources / "system.dic"
    return dic if dic.exists() else None
