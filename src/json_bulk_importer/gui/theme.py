import os

from aqt.qt import QDialog, QWidget

from .resources import get_icon_path

_PRIMARY = "#000000"
_ON_PRIMARY = "#ffffff"
_INK = "#000000"
_INK_DEEP = "#090909"
_CHARCOAL = "#525252"
_BODY = "#737373"
_MUTE = "#a3a3a3"
_CANVAS = "#ffffff"
_SURFACE_SOFT = "#fafafa"
_HAIRLINE = "#e5e5e5"
_HAIRLINE_STRONG = "#d4d4d4"
_FOCUS = "rgba(59, 130, 246, 0.5)"

_CHECK_SVG = get_icon_path("check.svg")
_CHEVRON_SVG = get_icon_path("chevron-down.svg")


def _url(path: str) -> str:
    """Chuyển đường dẫn tuyệt đối thành url(...) dùng trong QSS."""
    if not path:
        return ""
    return 'url("{}")'.format(path.replace("\\", "/"))


def build_qss() -> str:
    check_url = _url(_CHECK_SVG)
    chevron_url = _url(_CHEVRON_SVG)

    return f"""
QDialog, QMainWindow {{
    background-color: {_CANVAS};
    color: {_INK};
}}
QLabel {{
    color: {_INK};
}}
QLabel[dim="true"] {{
    color: {_BODY};
}}

QGroupBox {{
    background-color: {_CANVAS};
    border: 1px solid {_HAIRLINE};
    border-radius: 12px;
    margin-top: 16px;
    padding: 14px 12px 12px 12px;
    font-weight: 500;
    color: {_INK};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    top: -6px;
    padding: 2px 6px;
    background-color: {_CANVAS};
    color: {_INK};
    font-weight: 600;
}}

QPushButton {{
    background-color: {_SURFACE_SOFT};
    color: {_INK};
    border: 1px solid {_HAIRLINE_STRONG};
    border-radius: 18px;
    padding: 6px 16px;
    min-height: 22px;
    font-weight: 500;
}}
QPushButton:hover {{
    border-color: {_CHARCOAL};
    background-color: {_CANVAS};
}}
QPushButton:pressed {{
    background-color: {_HAIRLINE};
}}
QPushButton:disabled {{
    color: {_MUTE};
    background-color: {_SURFACE_SOFT};
    border-color: {_HAIRLINE};
}}
QPushButton#primaryButton {{
    background-color: {_PRIMARY};
    color: {_ON_PRIMARY};
    border-color: {_PRIMARY};
}}
QPushButton#primaryButton:hover {{
    background-color: {_INK_DEEP};
}}
QPushButton#primaryButton:pressed {{
    background-color: #1a1a1a;
}}

QLineEdit, QPlainTextEdit, QTextEdit {{
    background-color: {_CANVAS};
    color: {_INK};
    border: 1px solid {_HAIRLINE};
    border-radius: 10px;
    padding: 6px 10px;
    selection-background-color: #e5e5e5;
    selection-color: {_INK};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {_INK};
}}

QComboBox {{
    background-color: {_CANVAS};
    color: {_INK};
    border: 1px solid {_HAIRLINE};
    border-radius: 10px;
    padding: 4px 8px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {_CHARCOAL};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: {chevron_url};
    width: 14px;
    height: 14px;
}}
QComboBox QAbstractItemView {{
    background-color: {_CANVAS};
    color: {_INK};
    border: 1px solid {_HAIRLINE};
    selection-background-color: {_SURFACE_SOFT};
    selection-color: {_INK};
    outline: 0;
}}

QCheckBox {{
    color: {_INK};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {_HAIRLINE_STRONG};
    border-radius: 4px;
    background-color: {_CANVAS};
}}
QCheckBox::indicator:hover {{
    border-color: {_INK};
}}
QCheckBox::indicator:checked {{
    background-color: {_PRIMARY};
    border-color: {_PRIMARY};
    image: {check_url};
}}

QListWidget {{
    background-color: {_CANVAS};
    color: {_INK};
    border: 1px solid {_HAIRLINE};
    border-radius: 10px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 8px;
}}
QListWidget::item:selected {{
    background-color: {_PRIMARY};
    color: {_ON_PRIMARY};
}}
QListWidget::item:hover:!selected {{
    background-color: {_SURFACE_SOFT};
}}

QTableWidget {{
    background-color: {_CANVAS};
    color: {_INK};
    border: 1px solid {_HAIRLINE};
    border-radius: 10px;
    gridline-color: {_HAIRLINE};
    selection-background-color: {_PRIMARY};
    selection-color: {_ON_PRIMARY};
}}
QHeaderView::section {{
    background-color: {_SURFACE_SOFT};
    color: {_CHARCOAL};
    border: none;
    border-bottom: 1px solid {_HAIRLINE};
    border-right: 1px solid {_HAIRLINE};
    padding: 6px 8px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background-color: {_SURFACE_SOFT};
    border: none;
    border-bottom: 1px solid {_HAIRLINE};
}}

QSplitter::handle {{
    background-color: {_HAIRLINE};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

QScrollArea {{
    background-color: {_CANVAS};
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background-color: {_HAIRLINE_STRONG};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {_CHARCOAL};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background-color: {_HAIRLINE_STRONG};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QMessageBox {{
    background-color: {_CANVAS};
}}
"""


def apply_theme(widget: QWidget) -> None:
    """Áp stylesheet Ollama-style lên widget (thường là dialog)."""
    if widget is not None:
        widget.setStyleSheet(build_qss())
