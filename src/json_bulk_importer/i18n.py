import json
import os
from typing import Any

from .config import _get_config, _save_config

_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")

_SUPPORTED_LANGS = {"vi": "Tiếng Việt", "en": "English"}
_DEFAULT_LANG = "vi"

_strings: dict = {}
_current_lang: str = _DEFAULT_LANG


def get_supported_langs() -> dict:
    """Trả về dict {code: display_name} của các ngôn ngữ được hỗ trợ."""
    return dict(_SUPPORTED_LANGS)


def get_current_lang() -> str:
    return _current_lang


def set_lang(lang_code: str) -> None:
    """Đổi ngôn ngữ và lưu vào config."""
    global _current_lang, _strings
    if lang_code not in _SUPPORTED_LANGS:
        lang_code = _DEFAULT_LANG
    _current_lang = lang_code
    _strings = _load_locale(lang_code)

    config = _get_config()
    config["lang"] = lang_code
    _save_config(config)


def load_lang_from_config() -> None:
    """Đọc ngôn ngữ đã lưu trong user_config.json và nạp locale tương ứng."""
    global _current_lang, _strings
    config = _get_config()
    lang_code = config.get("lang", _DEFAULT_LANG)
    if lang_code not in _SUPPORTED_LANGS:
        lang_code = _DEFAULT_LANG
    _current_lang = lang_code
    _strings = _load_locale(lang_code)


def _load_locale(lang_code: str) -> dict:
    path = os.path.join(_LOCALES_DIR, f"{lang_code}.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _t(key: str, **kwargs: Any) -> str:
    """Tra cứu chuỗi dịch theo key. Hỗ trợ format: _t("msg", name="Anki")."""
    text = _strings.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
