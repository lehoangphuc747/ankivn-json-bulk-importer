import json
import os
from datetime import datetime


_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "user_config.json")
_HISTORY_DIR = os.path.join(os.path.dirname(__file__), "history")


def _get_config() -> dict:
    if os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"media_fields": {}, "presets": {}}


def _save_config(config: dict) -> None:
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_media_mappings(note_type_name: str) -> dict:
    """Trả về {field_name: 'text'|'image'|'audio'} cho Note Type."""
    return _get_config().get("media_fields", {}).get(note_type_name, {})


def get_presets() -> dict:
    """Trả về {preset_name: preset_data} của người dùng."""
    return _get_config().get("presets", {})


def save_preset(name: str, preset_data: dict) -> None:
    """Lưu hoặc cập nhật một preset theo tên."""
    config = _get_config()
    presets = config.setdefault("presets", {})
    presets[name] = preset_data
    _save_config(config)


def get_history_dir() -> str:
    """Trả về thư mục lưu lịch sử batch, tạo nếu chưa có."""
    os.makedirs(_HISTORY_DIR, exist_ok=True)
    return _HISTORY_DIR


def save_batch_history(record: dict) -> str:
    """Lưu một record lịch sử batch ra file JSON riêng."""
    history_dir = get_history_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"history_{timestamp}_{os.getpid()}.json"
    file_path = os.path.join(history_dir, file_name)

    payload = dict(record)
    payload.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return file_path


def get_welcome_shown() -> bool:
    """Kiểm tra xem người dùng đã chọn 'Don't show this again' cho Welcome popup chưa."""
    config = _get_config()
    return config.get("welcome_shown", False)


def set_welcome_shown(shown: bool) -> None:
    """Lưu tuỳ chọn tắt Welcome popup vĩnh viễn."""
    config = _get_config()
    config["welcome_shown"] = shown
    _save_config(config)
