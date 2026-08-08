import json
import os
import shutil
from datetime import datetime
from typing import Optional


def _get_data_dir() -> str:
    """Thư mục lưu runtime data, ưu tiên profile folder của Anki để không bị mất khi cài bản addon mới."""
    try:
        from aqt import mw
        if mw is not None and getattr(mw, "pm", None) is not None:
            profile = mw.pm.profileFolder()
            if profile:
                data_dir = os.path.join(profile, "json_bulk_importer_data")
                os.makedirs(data_dir, exist_ok=True)
                return data_dir
    except Exception:
        pass
    return os.path.dirname(os.path.abspath(__file__))


_DATA_DIR = _get_data_dir()
_CONFIG_PATH = os.path.join(_DATA_DIR, "user_config.json")
_HISTORY_DIR = os.path.join(_DATA_DIR, "history")


def _migrate_from_legacy() -> None:
    """Di dời user_config.json + history/ từ vị trí cũ (cạnh module) sang data dir mới nếu có."""
    legacy_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.normcase(os.path.abspath(_DATA_DIR)) == os.path.normcase(os.path.abspath(legacy_dir)):
        return
    legacy_config = os.path.join(legacy_dir, "user_config.json")
    if os.path.isfile(legacy_config) and not os.path.isfile(_CONFIG_PATH):
        try:
            shutil.copy2(legacy_config, _CONFIG_PATH)
        except Exception:
            pass
    legacy_history = os.path.join(legacy_dir, "history")
    if os.path.isdir(legacy_history) and not os.path.isdir(_HISTORY_DIR):
        try:
            shutil.copytree(legacy_history, _HISTORY_DIR)
        except Exception:
            pass


_migrate_from_legacy()


def _get_config() -> dict:
    if os.path.isfile(_CONFIG_PATH):
        if os.path.getsize(_CONFIG_PATH) == 0:
            return {"media_fields": {}, "presets": {}}
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                corrupt_backup = f"{_CONFIG_PATH}.corrupt_{timestamp}"
                os.replace(_CONFIG_PATH, corrupt_backup)
                backup_name = os.path.basename(corrupt_backup)
            except Exception:
                backup_name = "unknown (backup failed)"
            
            msg = (
                f"Configuration file is corrupted (invalid JSON) and has been backed up to {backup_name}.\n"
                f"A default configuration will be used. Error details: {e}"
            )
            from aqt import mw
            if mw and getattr(mw, "col", None) is not None:
                from aqt.utils import showWarning
                showWarning(msg)
            else:
                print(msg)
    return {"media_fields": {}, "presets": {}}


def _save_config(config: dict) -> None:
    tmp_path = _CONFIG_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, _CONFIG_PATH)
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise e



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


def get_window_maximized() -> bool:
    """Kiểm tra xem lần trước cửa sổ có được phóng to (maximize) không."""
    config = _get_config()
    return config.get("window_maximized", False)


def set_window_maximized(maximized: bool) -> None:
    """Lưu trạng thái phóng to cửa sổ."""
    config = _get_config()
    config["window_maximized"] = maximized
    _save_config(config)


def get_window_geometry() -> Optional[dict]:
    """Lấy vị trí và kích thước cửa sổ đã lưu lần cuối (None nếu chưa có)."""
    config = _get_config()
    return config.get("window_geometry")


def set_window_geometry(geometry: dict) -> None:
    """Lưu vị trí và kích thước cửa sổ (x, y, w, h)."""
    config = _get_config()
    config["window_geometry"] = geometry
    _save_config(config)

