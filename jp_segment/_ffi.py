from __future__ import annotations

from ctypes import CDLL, c_bool, c_char, c_char_p, c_void_p, cast
from pathlib import Path

from ._utils import find_resources_dir, platform_lib_name


class SudachiFFI:
    def __init__(self, lib_path: Path | None = None) -> None:
        if lib_path is None:
            name = platform_lib_name()
            if not name:
                msg = "Unsupported platform for native Sudachi library"
                raise OSError(msg)
            lib_path = find_resources_dir() / name
        if not lib_path.exists():
            msg = f"Sudachi native library not found: {lib_path}"
            raise FileNotFoundError(msg)
        self._lib = CDLL(str(lib_path))
        # Set signatures
        self._lib.process_text_ffi.argtypes = [
            c_char_p,  # config path
            c_char_p,  # input text
            c_char_p,  # dictionary path
            c_char,  # mode ('A'/'B'/'C')
            c_bool,  # printAll
            c_bool,  # wakati
        ]
        self._lib.process_text_ffi.restype = c_void_p

        self._lib.free_string.argtypes = [c_void_p]
        self._lib.free_string.restype = None

    def process_text(
        self,
        config_path: Path,
        text: str,
        dictionary_path: Path,
        *,
        mode: str = "C",
        print_all: bool = True,
        wakati: bool = False,
    ) -> str:
        # Encode inputs
        cfg = str(config_path).encode("utf-8")
        dic = str(dictionary_path).encode("utf-8")
        inp = text.encode("utf-8")
        ptr = self._lib.process_text_ffi(cfg, inp, dic, c_char(ord(mode)), c_bool(print_all), c_bool(wakati))
        if not ptr:
            return ""
        try:
            as_cchar_p = cast(ptr, c_char_p)
            out = as_cchar_p.value.decode("utf-8") if as_cchar_p.value else ""
        finally:
            self._lib.free_string(ptr)
        return out
