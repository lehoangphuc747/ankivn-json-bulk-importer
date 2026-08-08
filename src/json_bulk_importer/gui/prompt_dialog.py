from typing import Any

from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QSpinBox, QStyle,
)

from ..i18n import _t
from .theme import apply_theme


class PromptConfigDialog(QDialog):
    """Nhập role + các thông số quan trọng để tạo prompt cho AI."""

    def __init__(
        self,
        default_role: str = "",
        default_quantity: int = 10,
        default_topic: str = "",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(_t("prompt_cfg_title"))
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_t("prompt_cfg_description")))

        form = QFormLayout()
        self.role_edit = QLineEdit(default_role)
        self.role_edit.setPlaceholderText(_t("prompt_cfg_role_ph"))
        form.addRow(_t("prompt_cfg_role"), self.role_edit)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 9999)
        self.quantity_spin.setValue(default_quantity)
        form.addRow(_t("prompt_cfg_quantity"), self.quantity_spin)

        self.topic_edit = QLineEdit(default_topic)
        self.topic_edit.setPlaceholderText(_t("prompt_cfg_topic_ph"))
        form.addRow(_t("prompt_cfg_topic"), self.topic_edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton(_t("btn_copy"))
        save_btn.setObjectName("primaryButton")
        save_btn.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton
        ))
        save_btn.clicked.connect(self.accept)
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

    def role(self) -> str:
        return self.role_edit.text().strip()

    def quantity(self) -> int:
        return self.quantity_spin.value()

    def topic(self) -> str:
        return self.topic_edit.text().strip()
