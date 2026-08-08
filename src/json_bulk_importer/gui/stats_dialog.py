from typing import Any, List, Optional

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGridLayout, QStyle, QButtonGroup, Qt,
)

from ..i18n import _t
from .theme import apply_theme


STAT_KEYS = [
    "created_at",
    "modified_at",
    "reps",
    "lapses",
    "ivl",
    "ease",
]

STAT_LABEL_KEYS = {
    "created_at": "stat_created_at",
    "modified_at": "stat_modified_at",
    "reps": "stat_reps",
    "lapses": "stat_lapses",
    "ivl": "stat_ivl",
    "ease": "stat_ease",
}


class StatsConfigDialog(QDialog):
    """Chọn các stat nào sẽ được kèm khi Get Deck."""

    def __init__(
        self,
        current: Optional[List[str]] = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(_t("stats_title"))
        self.setMinimumWidth(420)
        self._checkboxes: List[QCheckBox] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(False)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_t("stats_description")))

        grid = QGridLayout()
        grid.addWidget(QLabel(_t("stats_col_stat")), 0, 0)
        grid.addWidget(QLabel(_t("stats_col_include")), 0, 1)

        selected = set(current or STAT_KEYS)
        for i, key in enumerate(STAT_KEYS):
            grid.addWidget(QLabel(_t(STAT_LABEL_KEYS[key])), i + 1, 0)
            cb = QCheckBox()
            cb.setChecked(key in selected)
            cb.setProperty("stat_key", key)
            self._group.addButton(cb)
            self._checkboxes.append(cb)
            grid.addWidget(cb, i + 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton(_t("btn_save"))
        save_btn.setObjectName("primaryButton")
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
        apply_theme(self)

    def _on_save(self) -> None:
        self.accept()

    def selected_stats(self) -> List[str]:
        return [cb.property("stat_key") for cb in self._checkboxes if cb.isChecked()]
