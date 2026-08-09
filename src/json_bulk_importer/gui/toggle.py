from typing import Any

from aqt.qt import (
    QAbstractButton, QColor, QPen, QRectF, QSize, QSizePolicy, Qt, QPainter,
    QVariantAnimation,
)


class ToggleSwitch(QAbstractButton):
    """Toggle switch kiểu iOS, thay cho QCheckBox thường.

    Vẽ track bo tròn (xám khi tắt, xanh khi bật) + nút trắng tròn trượt qua
    lại có animation. Style tương tự CSS toggle chuẩn web (#2196F3).
    """

    def __init__(self, parent: Any = None, checked: bool = False) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(52, 28)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._pos = 1.0 if checked else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.valueChanged.connect(self._on_anim_value)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(52, 28)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        target = 1.0 if checked else 0.0
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_anim_value(self, value: Any) -> None:
        self._pos = float(value)
        self.update()

    def paintEvent(self, event: Any) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        track = QRectF(1.5, 1.5, w - 3, h - 3)
        if self.isChecked():
            track_color = QColor("#2196F3")
            border_color = QColor("#2196F3")
        else:
            track_color = QColor("#e2e2e2")
            border_color = QColor("#d4d4d4")

        p.setPen(QPen(border_color, 1.5))
        p.setBrush(track_color)
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        knob_d = track.height() - 8
        x = track.left() + 4 + self._pos * (track.width() - knob_d - 8)
        y = track.center().y() - knob_d / 2
        knob = QRectF(x, y, knob_d, knob_d)
        p.setPen(QPen(QColor("#f0f0f0"), 1))
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(knob)
        p.end()
