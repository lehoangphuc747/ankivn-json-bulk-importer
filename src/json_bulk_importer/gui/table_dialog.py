import json
from typing import Any, List, Optional

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, Qt,
    QApplication, QEvent,
    QColor, QBrush, QTextBrowser,
)

from ..i18n import _t
from ..media import smart_download_media


META_KEY_ORDER = ["__guid__", "__deck__", "__tags__"]


class TablePreviewDialog(QDialog):
    """Popup hiển thị dữ liệu JSON dạng bảng, cho phép chỉnh sửa trực tiếp."""

    def __init__(
        self, cards: List[dict],
        media_mappings: Optional[dict] = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(_t("table_title"))
        self.setMinimumSize(900, 500)

        flags = self.windowFlags()
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        flags &= ~Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        self._original_cards = cards
        self._media_mappings = media_mappings or {}
        self._columns: List[str] = []
        self._preview_mode = False
        self._build_columns(cards)

        self._setup_ui()
        self._populate_table(cards)

    def _build_columns(self, cards: List[dict]) -> None:
        """Gom tất cả unique keys từ các card, meta-keys xếp trước."""
        seen: dict = {}
        for card in cards:
            for key in card:
                if key not in seen:
                    seen[key] = True

        meta_cols = [k for k in META_KEY_ORDER if k in seen]
        content_cols = [k for k in seen if k not in META_KEY_ORDER]
        self._columns = meta_cols + content_cols

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self._columns))
        self.table.setHorizontalHeaderLabels(self._columns)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        self.table.installEventFilter(self)
        self._default_edit_triggers = self.table.editTriggers()
        layout.addWidget(self.table, stretch=1)

        # --- Preview Panel ---
        self.preview_panel = QTextBrowser()
        self.preview_panel.setMaximumHeight(100)
        self.preview_panel.setVisible(False)
        layout.addWidget(self.preview_panel)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(6)

        self.toggle_preview_btn = QPushButton(_t("btn_toggle_preview"))
        self.toggle_preview_btn.setToolTip(_t("tooltip_toggle_preview_mode"))
        self.toggle_preview_btn.clicked.connect(self._on_toggle_preview_mode)
        footer_layout.addWidget(self.toggle_preview_btn)

        paste_btn = QPushButton(_t("btn_paste_excel"))
        paste_btn.setToolTip(_t("tooltip_paste_excel"))
        paste_btn.clicked.connect(self._paste_from_clipboard)
        footer_layout.addWidget(paste_btn)

        prefetch_btn = QPushButton(_t("btn_prefetch"))
        prefetch_btn.setToolTip(_t("tooltip_prefetch"))
        prefetch_btn.clicked.connect(self._on_prefetch_media)
        footer_layout.addWidget(prefetch_btn)

        footer_layout.addStretch()

        save_btn = QPushButton(_t("btn_save_update_json"))
        save_btn.setToolTip(_t("tooltip_save_update_json"))
        save_btn.clicked.connect(self.accept)
        footer_layout.addWidget(save_btn)

        cancel_btn = QPushButton(_t("btn_cancel"))
        cancel_btn.setToolTip(_t("tooltip_cancel"))
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        layout.addLayout(footer_layout)

    def eventFilter(self, obj: Any, event: Any) -> bool:
        if obj is self.table and event.type() == QEvent.Type.KeyPress:
            if (event.key() == Qt.Key.Key_V
                    and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self._paste_from_clipboard()
                return True
        return super().eventFilter(obj, event)

    def _on_toggle_preview_mode(self) -> None:
        """Chuyển đổi giữa Edit Mode và Preview Mode."""
        self._preview_mode = not self._preview_mode
        self._update_preview_toggle()
        
        if self._preview_mode:
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.preview_panel.setVisible(True)
            current = self.table.currentItem()
            if current:
                self._on_cell_clicked(current.row(), current.column())
            elif self.table.rowCount() > 0 and self.table.columnCount() > 0:
                self.table.setCurrentCell(0, 0)
                self._on_cell_clicked(0, 0)
            else:
                self.preview_panel.clear()
        else:
            self.table.setEditTriggers(self._default_edit_triggers)
            self.preview_panel.setVisible(False)

    def _update_preview_toggle(self) -> None:
        if self._preview_mode:
            self.toggle_preview_btn.setToolTip(_t("tooltip_toggle_edit_mode"))
        else:
            self.toggle_preview_btn.setToolTip(_t("tooltip_toggle_preview_mode"))

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Khi click cell trong Preview Mode, hiển thị HTML preview."""
        if not self._preview_mode:
            return
        
        item = self.table.item(row, col)
        if not item:
            self.preview_panel.clear()
            return
        
        html_content = item.text()
        self.preview_panel.setHtml(html_content)

    def _on_current_cell_changed(
        self,
        current_row: int,
        current_col: int,
        previous_row: int,
        previous_col: int,
    ) -> None:
        if self._preview_mode and current_row >= 0 and current_col >= 0:
            self._on_cell_clicked(current_row, current_col)

    def _paste_from_clipboard(self) -> None:
        """Dán dữ liệu TSV (Excel/Sheets) vào bảng. Dòng đầu = header."""
        clipboard = QApplication.clipboard()
        if not clipboard:
            return
        text = clipboard.text()
        if not text or not text.strip():
            QMessageBox.warning(
                self, _t("title_paste"), _t("msg_clipboard_empty")
            )
            return

        lines = text.strip().split("\n")
        if len(lines) < 2:
            QMessageBox.warning(
                self, _t("title_paste"), _t("msg_paste_min_lines")
            )
            return

        headers = [h.strip() for h in lines[0].split("\t")]
        data_rows: List[List[str]] = []
        for line in lines[1:]:
            if line.strip():
                data_rows.append([c.strip() for c in line.split("\t")])

        if not data_rows:
            return

        self._columns = headers
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(data_rows))

        for row_idx, row_data in enumerate(data_rows):
            for col_idx in range(len(headers)):
                value = row_data[col_idx] if col_idx < len(row_data) else ""
                self.table.setItem(
                    row_idx, col_idx,
                    self._make_table_item(headers[col_idx], value),
                )

    def _on_prefetch_media(self) -> None:
        """Tải thử media cho các cột Image/Audio, highlight kết quả."""
        if not mw or not mw.col:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_collection_not_available")
            )
            return

        has_media_cols = any(
            self._media_mappings.get(c, "text") in ("image", "audio")
            for c in self._columns
        )
        if not has_media_cols:
            QMessageBox.information(
                self, _t("title_prefetch"), _t("msg_no_media_fields")
            )
            return

        media_dir = mw.col.media.dir()
        ok_bg = QBrush(QColor(200, 255, 200))
        err_bg = QBrush(QColor(255, 200, 200))
        fetched = 0
        errors = 0

        for col_idx, col_name in enumerate(self._columns):
            ftype = self._media_mappings.get(col_name, "text")
            if ftype not in ("image", "audio"):
                continue

            for row in range(self.table.rowCount()):
                item = self.table.item(row, col_idx)
                if not item:
                    continue
                text = item.text().strip()
                if not text:
                    continue

                tag, err = smart_download_media(text, ftype, media_dir)
                item.setText(tag)

                if err:
                    item.setBackground(err_bg)
                    item.setToolTip(_t("tooltip_media_error", error=err))
                    errors += 1
                else:
                    item.setBackground(ok_bg)
                    item.setToolTip(_t("tooltip_media_ok"))
                    fetched += 1

                QApplication.processEvents()

        QMessageBox.information(
            self, _t("title_prefetch_done"),
            _t("msg_prefetch_done", fetched=fetched, errors=errors),
        )

    def _populate_table(self, cards: List[dict]) -> None:
        """Điền dữ liệu từ list[dict] vào QTableWidget."""
        self.table.setRowCount(len(cards))

        for row, card in enumerate(cards):
            for col_idx, col_name in enumerate(self._columns):
                value = card.get(col_name, "")

                if col_name == "__tags__" and isinstance(value, list):
                    display = ", ".join(str(v) for v in value)
                elif isinstance(value, (dict, list)):
                    display = json.dumps(value, ensure_ascii=False)
                else:
                    display = str(value) if value != "" else ""

                self.table.setItem(
                    row, col_idx, self._make_table_item(col_name, display)
                )
                
        # Tự động điều chỉnh độ rộng cột dựa trên nội dung vừa điền
        self.table.resizeColumnsToContents()

    def _make_table_item(self, col_name: str, display: str) -> QTableWidgetItem:
        item = QTableWidgetItem(display)
        ftype = self._media_mappings.get(col_name, "text")
        if ftype in ("image", "audio"):
            item.setBackground(QBrush(QColor(230, 247, 255)))
            item.setToolTip(_t("tooltip_media_field", type=ftype))
        return item

    def _table_to_cards(self) -> List[dict]:
        """Đọc dữ liệu từ bảng, chuyển ngược lại list[dict]."""
        new_cards: List[dict] = []

        for row in range(self.table.rowCount()):
            card: dict = {}
            for col_idx, col_name in enumerate(self._columns):
                item = self.table.item(row, col_idx)
                text = item.text().strip() if item else ""

                if not text:
                    continue

                if col_name == "__tags__":
                    card[col_name] = [
                        t.strip() for t in text.split(",") if t.strip()
                    ]
                else:
                    card[col_name] = text

            if card:
                new_cards.append(card)

        return new_cards

    def get_json_text(self) -> str:
        """Trả về chuỗi JSON đã format từ dữ liệu bảng."""
        cards = self._table_to_cards()
        return json.dumps(cards, indent=2, ensure_ascii=False)
