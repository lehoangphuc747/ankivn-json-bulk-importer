import base64
import os
from typing import Optional

from aqt.qt import QIcon, QPixmap
from aqt.theme import theme_manager

_ICONS_DIR = os.path.join(os.path.dirname(__file__), "icons")

_STROKE_COLOR = "#000000"


def _current_stroke_color() -> str:
    return "#ffffff" if theme_manager.night_mode else _STROKE_COLOR


def get_icon_path(icon_name: str) -> str:
    """Trả về đường dẫn tuyệt đối tới file icon SVG trong package."""
    path = os.path.join(_ICONS_DIR, icon_name)
    return path if os.path.isfile(path) else ""


def _read_svg(icon_name: str) -> Optional[str]:
    path = get_icon_path(icon_name)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def get_icon(icon_name: str) -> QIcon:
    """Trả về QIcon cho widget, tô nét theo dark/light mode hiện tại.

    SVG lưu nét đen; đọc nội dung, thay màu stroke theo theme rồi nạp từ
    bytes để không phụ thuộc hành vi invertPixels của Anki.
    """
    svg = _read_svg(icon_name)
    if not svg:
        return QIcon()
    svg = svg.replace(_STROKE_COLOR, _current_stroke_color())
    pixmap = QPixmap()
    if not pixmap.loadFromData(svg.encode("utf-8")):
        return QIcon()
    return QIcon(pixmap)


def svg_img_html(icon_name: str, size: int = 18) -> str:
    """Trả về thẻ <img> data-URI nhúng icon SVG cho QTextBrowser.

    Tô màu nét theo theme hiện tại để hiển thị rõ cả dark lẫn light mode.
    """
    svg = _read_svg(icon_name)
    if not svg:
        return ""
    svg = svg.replace(_STROKE_COLOR, _current_stroke_color())
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(
        svg.encode("utf-8")
    ).decode("ascii")
    return (
        f'<img src="{data_uri}" width="{size}" height="{size}" '
        f'style="vertical-align: middle;">'
    )
