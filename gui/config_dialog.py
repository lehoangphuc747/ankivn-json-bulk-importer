from typing import Any, List

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGridLayout, QStyle,
)

from ..config import get_media_mappings, _get_config, _save_config
from ..i18n import _t


class MediaConfigDialog(QDialog):

    def __init__(
        self, note_type_name: str, field_names: List[str],
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(_t("config_title", name=note_type_name))
        self.setMinimumWidth(460)
        self._note_type_name = note_type_name
        self._field_names = field_names
        self._combos: List[QComboBox] = []

        current = get_media_mappings(note_type_name)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_t("config_description")))

        grid = QGridLayout()
        grid.addWidget(QLabel(_t("config_col_field")), 0, 0)
        grid.addWidget(QLabel(_t("config_col_type")), 0, 1)

        for i, name in enumerate(field_names):
            grid.addWidget(QLabel(name), i + 1, 0)
            combo = QComboBox()
            combo.addItems(["Text", "Image", "Audio"])
            saved = current.get(name, "text").lower()
            if saved == "image":
                combo.setCurrentIndex(1)
            elif saved == "audio":
                combo.setCurrentIndex(2)
            grid.addWidget(combo, i + 1, 1)
            self._combos.append(combo)

        layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton(_t("btn_save"))
        save_btn.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton
        ))
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton(_t("btn_cancel"))
        cancel_btn.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton
        ))
        cancel_btn.setToolTip(_t("tooltip_cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _on_save(self) -> None:
        mapping: dict = {}
        for name, combo in zip(self._field_names, self._combos):
            mapping[name] = combo.currentText().lower()
        config = _get_config()
        config["media_fields"][self._note_type_name] = mapping
        _save_config(config)
        self.accept()
