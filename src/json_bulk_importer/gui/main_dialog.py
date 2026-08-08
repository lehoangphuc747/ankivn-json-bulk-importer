import json
import os
from typing import Any, List, Optional

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QCheckBox,
    QPlainTextEdit, QPushButton, QMessageBox, Qt,
    QInputDialog, QFileDialog, QApplication, QSplitter, QWidget, QFontDatabase,
    QScrollArea, QStyle, QSize, QSizePolicy, QIcon, QPixmap, QPainter, QFont,
)
from anki.utils import guid64

from ..config import (
    get_media_mappings, get_presets, save_preset,
    get_history_dir, save_batch_history,
    get_window_maximized, set_window_maximized,
)
from ..core import create_cards_logic, export_deck_to_json_logic
from ..prompt import generate_ai_prompt
from ..i18n import _t, get_supported_langs, get_current_lang, set_lang
from .help_dialog import HelpDialog
from .config_dialog import MediaConfigDialog
from .stats_dialog import StatsConfigDialog, STAT_KEYS
from .table_dialog import TablePreviewDialog
from .search_dialog import SearchSelectDialog
from .resources import get_icon
from .theme import apply_theme


class ClickableComboBox(QComboBox):
    def __init__(self, parent: Any = None, callback: Any = None) -> None:
        super().__init__(parent)
        self.callback = callback
        self.setEditable(False)

    def showPopup(self) -> None:
        if self.callback:
            self.callback()
        else:
            super().showPopup()

    def mousePressEvent(self, event: Any) -> None:
        if self.callback:
            self.callback()
        else:
            super().mousePressEvent(event)


class BulkCardCreatorDialog(QDialog):

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle(_t("main_title"))
        self.setWindowIcon(get_icon("rocket"))
        self.setMinimumSize(700, 500)

        flags = self.windowFlags()
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        flags &= ~Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        if get_window_maximized():
            maximized_state = getattr(Qt.WindowState, "WindowMaximized", None) or getattr(Qt, "WindowMaximized", None)
            if maximized_state is not None:
                self.setWindowState(self.windowState() | maximized_state)

        self._setup_ui()
        apply_theme(self)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(8)

        self._build_setup_panel(left_layout)
        left_layout.addStretch()

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 0, 0, 0)
        right_layout.setSpacing(8)

        self._build_json_workspace(right_layout)
        self._build_action_bar(right_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([300, 700])
        left_panel.setMinimumWidth(0)
        left_panel.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Expanding,
        )
        right_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        first_note_type = self.note_type_combo.currentText()
        if first_note_type:
            self._on_note_type_changed(first_note_type)

    def _build_setup_panel(self, parent_layout: QVBoxLayout) -> None:
        self.setup_panel = QWidget()
        self.setup_panel.setMinimumWidth(0)
        self.setup_panel.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Expanding,
        )
        setup_layout = QVBoxLayout(self.setup_panel)
        setup_layout.setContentsMargins(0, 0, 0, 0)
        setup_layout.setSpacing(5)

        setup_layout.addWidget(QLabel(_t("main_note_type")))
        self.note_type_combo = ClickableComboBox(self, self._on_search_note_type)
        self.note_type_combo.setMinimumWidth(0)
        self.note_type_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self._load_note_types()
        self.note_type_combo.currentTextChanged.connect(self._on_note_type_changed)
        setup_layout.addWidget(self.note_type_combo)

        setup_layout.addWidget(QLabel(_t("main_deck")))
        deck_row = QHBoxLayout()
        deck_row.setSpacing(5)
        self.deck_combo = ClickableComboBox(self, self._on_search_deck)
        self.deck_combo.setMinimumWidth(0)
        self.deck_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self._load_decks()
        deck_row.addWidget(self.deck_combo, stretch=1)

        new_deck_btn = self._make_emoji_button(
            "🎴",
            _t("btn_new_deck"),
            self._on_new_deck,
        )
        deck_row.addWidget(new_deck_btn)
        setup_layout.addLayout(deck_row)

        fetch_deck_btn = self._make_text_button(
            _t("btn_get_deck_data_short"),
            self._on_fetch_deck_data,
            _t("btn_get_deck_data") + "\n" + _t("tooltip_get_deck_data"),
        )
        setup_layout.addWidget(fetch_deck_btn)
        self.stats_btn = self._make_text_button(
            _t("chk_include_stats_short"),
            self._on_choose_stats,
            _t("tooltip_include_stats"),
        )
        self._selected_stats: List[str] = list(STAT_KEYS)
        setup_layout.addWidget(self.stats_btn)

        self.advanced_toggle = self._make_text_button(
            _t("section_advanced_collapsed"),
            self._on_toggle_advanced,
            _t("tooltip_advanced_tools"),
        )
        self.advanced_toggle.setObjectName("advancedToggle")
        self.advanced_toggle.setIcon(get_icon("chevron-down"))
        setup_layout.addWidget(self.advanced_toggle)

        self.advanced_container = QWidget()
        self.advanced_container.setMinimumWidth(0)
        self.advanced_container.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        advanced_layout = QVBoxLayout(self.advanced_container)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(5)

        sync_group = QGroupBox(_t("section_sync_update"))
        self._make_sidebar_group_flexible(sync_group)
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.setContentsMargins(8, 8, 8, 8)
        sync_layout.setSpacing(5)
        sync_layout.addWidget(QLabel(_t("main_smart_sync")))
        self.match_field_combo = QComboBox()
        self.match_field_combo.setMinimumWidth(0)
        self.match_field_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.match_field_combo.addItem(_t("main_smart_sync_none"))
        sync_layout.addWidget(self.match_field_combo)

        self.write_guid_checkbox = QCheckBox(_t("chk_write_guids_short"))
        self.write_guid_checkbox.setMinimumWidth(0)
        self.write_guid_checkbox.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.write_guid_checkbox.setChecked(True)
        self.write_guid_checkbox.setToolTip(_t("tooltip_write_guids"))
        sync_layout.addWidget(self.write_guid_checkbox)

        generate_guid_btn = self._make_text_button(
            _t("btn_generate_guid_short"),
            self._on_generate_guid,
            _t("btn_generate_guid") + "\n" + _t("tooltip_generate_guid"),
        )
        sync_layout.addWidget(generate_guid_btn)
        add_deck_btn = self._make_text_button(
            _t("btn_add_deck_to_json_short"),
            self._on_add_deck_to_json,
            _t("btn_add_deck_to_json") + "\n" + _t("tooltip_add_deck_to_json"),
        )
        sync_layout.addWidget(add_deck_btn)
        advanced_layout.addWidget(sync_group)

        media_ai_group = QGroupBox(_t("section_media"))
        self._make_sidebar_group_flexible(media_ai_group)
        media_ai_layout = QVBoxLayout(media_ai_group)
        media_ai_layout.setContentsMargins(8, 8, 8, 8)
        media_ai_layout.setSpacing(5)
        media_cfg_btn = self._make_text_button(
            _t("btn_media_config_short"),
            self._on_media_config,
            _t("btn_media_config") + "\n" + _t("tooltip_media_config"),
        )
        media_ai_layout.addWidget(media_cfg_btn)
        advanced_layout.addWidget(media_ai_group)

        tools_group = QGroupBox(_t("section_presets_history"))
        self._make_sidebar_group_flexible(tools_group)
        tools_layout = QVBoxLayout(tools_group)
        tools_layout.setContentsMargins(8, 8, 8, 8)
        tools_layout.setSpacing(5)
        tools_layout.addWidget(QLabel(_t("main_preset")))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(0)
        self.preset_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        tools_layout.addWidget(self.preset_combo)
        preset_btn_row = QHBoxLayout()
        preset_btn_row.setSpacing(5)
        load_preset_btn = self._make_text_button(
            _t("btn_load_preset_short"), self._on_load_preset,
            _t("btn_load_preset"),
        )
        preset_btn_row.addWidget(load_preset_btn)
        save_preset_btn = self._make_text_button(
            _t("btn_save_preset_short"), self._on_save_preset,
            _t("btn_save_preset"),
        )
        preset_btn_row.addWidget(save_preset_btn)
        tools_layout.addLayout(preset_btn_row)
        self._load_presets()
        history_btn = self._make_text_button(
            _t("btn_history"),
            self._on_open_history,
            _t("tooltip_open_history"),
        )
        tools_layout.addWidget(history_btn)
        advanced_layout.addWidget(tools_group)

        setup_layout.addWidget(self.advanced_container)
        self.advanced_container.setVisible(False)
        setup_layout.addStretch()

        self.setup_scroll = QScrollArea()
        self.setup_scroll.setWidgetResizable(True)
        self.setup_scroll.setMinimumWidth(0)
        self.setup_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setup_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setup_scroll.setWidget(self.setup_panel)
        parent_layout.addWidget(self.setup_scroll, stretch=1)

    def _build_json_workspace(self, parent_layout: QVBoxLayout) -> None:
        json_group = QGroupBox(_t("section_json"))
        json_layout = QVBoxLayout(json_group)

        json_tools_row = QHBoxLayout()
        json_tools_row.setSpacing(6)

        import_btn = self._make_text_button(
            _t("btn_import_json"),
            self._on_import_json,
            _t("toolbar_import_json"),
            flexible=False,
        )
        json_tools_row.addWidget(import_btn)
        export_btn = self._make_text_button(
            _t("btn_export_json"),
            self._on_export_json,
            _t("toolbar_export_json"),
            flexible=False,
        )
        json_tools_row.addWidget(export_btn)
        table_btn = self._make_text_button(
            _t("btn_view_table"),
            self._on_view_as_table,
            _t("toolbar_view_table"),
            flexible=False,
        )
        json_tools_row.addWidget(table_btn)
        prompt_btn = self._make_text_button(
            _t("btn_copy_prompt"),
            self._on_copy_prompt,
            _t("tooltip_copy_prompt"),
            flexible=False,
        )
        json_tools_row.addWidget(prompt_btn)
        json_tools_row.addStretch()
        json_layout.addLayout(json_tools_row)

        self.json_input = QPlainTextEdit()
        self.json_input.setPlaceholderText(_t("main_json_placeholder"))
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.json_input.setFont(fixed_font)
        self.json_input.textChanged.connect(self._validate_json_realtime)

        json_layout.addWidget(self.json_input, stretch=1)
        parent_layout.addWidget(json_group, stretch=1)

    def _build_action_bar(self, parent_layout: QVBoxLayout) -> None:
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 10, 0, 0)

        action_layout.addWidget(QLabel(_t("lang_label")))
        self.lang_combo = QComboBox()
        supported = get_supported_langs()
        current_lang = get_current_lang()
        for code, display in supported.items():
            self.lang_combo.addItem(display, code)
            if code == current_lang:
                self.lang_combo.setCurrentIndex(self.lang_combo.count() - 1)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        action_layout.addWidget(self.lang_combo)

        help_btn = self._make_emoji_button(
            "🛠️",
            _t("btn_help"),
            self._on_help,
        )
        action_layout.addWidget(help_btn)

        action_layout.addStretch()

        self.create_btn = QPushButton(_t("btn_create_update"))
        self.create_btn.setObjectName("primaryButton")
        self.create_btn.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton
        ))
        self.create_btn.setDefault(True)
        self.create_btn.setMinimumSize(170, 36)
        self.create_btn.clicked.connect(self._on_submit)
        action_layout.addWidget(self.create_btn)

        close_btn = QPushButton(_t("btn_close"))
        close_btn.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton
        ))
        close_btn.setMinimumHeight(36)
        close_btn.setToolTip(_t("tooltip_close"))
        close_btn.clicked.connect(self.close)
        action_layout.addWidget(close_btn)

        parent_layout.addLayout(action_layout)

    def _make_emoji_button(
        self,
        emoji: str,
        tooltip: str,
        callback: Any,
        size: int = 28,
    ) -> QPushButton:
        button = QPushButton()
        button.setFixedSize(size, size)
        button.setIcon(self._emoji_icon(emoji, size))
        button.setIconSize(QSize(size - 8, size - 8))
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        return button

    def _emoji_icon(self, emoji: str, size: int) -> QIcon:
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        font = QFont("Segoe UI Emoji")
        font.setPixelSize(size - 6)
        painter.setFont(font)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        return QIcon(pm)

    def _make_text_button(
        self,
        label: str,
        callback: Any,
        tooltip: Optional[str] = None,
        flexible: bool = True,
    ) -> QPushButton:
        button = QPushButton(label)
        if flexible:
            button.setMinimumWidth(0)
            button.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Fixed,
            )
        else:
            button.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )
        if tooltip:
            button.setToolTip(tooltip)
        button.clicked.connect(callback)
        return button

    def _make_sidebar_group_flexible(self, group: QGroupBox) -> None:
        group.setMinimumWidth(0)
        group.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

    def _validate_json_realtime(self) -> None:
        """Kiểm tra JSON realtime, nếu lỗi thì viền đỏ, nếu đúng thì viền xanh/bình thường."""
        text = self.json_input.toPlainText().strip()
        if not text:
            self.json_input.setStyleSheet("") # Trống thì bình thường
            return

        from aqt.theme import theme_manager
        is_night = False
        try:
            is_night = theme_manager.night_mode
        except Exception:
            pass

        try:
            json.loads(text)
            # Nếu JSON hợp lệ: Viền xanh lá mỏng
            valid_color = "#81C784" if is_night else "#4CAF50"
            self.json_input.setStyleSheet(f"QPlainTextEdit {{ border: 2px solid {valid_color}; border-radius: 4px; }}")
        except json.JSONDecodeError:
            # Nếu JSON lỗi: Viền đỏ báo hiệu
            invalid_color = "#EF5350" if is_night else "#F44336"
            self.json_input.setStyleSheet(f"QPlainTextEdit {{ border: 2px solid {invalid_color}; border-radius: 4px; }}")


    # ---- language ----

    def _on_lang_changed(self, index: int) -> None:
        new_lang = self.lang_combo.itemData(index)
        if new_lang and new_lang != get_current_lang():
            set_lang(new_lang)
            QMessageBox.information(
                self,
                _t("lang_changed_title"),
                _t("lang_changed"),
            )

    def _on_help(self) -> None:
        dialog = HelpDialog(self)
        dialog.exec()

    def _on_toggle_advanced(self) -> None:
        expanded = self.advanced_container.isVisible()
        self.advanced_container.setVisible(not expanded)
        label = _t("section_advanced_expanded") if not expanded else _t("section_advanced_collapsed")
        icon = "chevron-up" if not expanded else "chevron-down"
        self.advanced_toggle.setText(label)
        self.advanced_toggle.setIcon(get_icon(icon))

    # ---- helpers ----

    def _load_note_types(self) -> None:
        self.note_type_combo.clear()
        if mw and mw.col:
            for model in mw.col.models.all():
                self.note_type_combo.addItem(model["name"])

    def _load_decks(self) -> None:
        self.deck_combo.clear()
        if mw and mw.col:
            self.deck_combo.addItem("Bulk Card Creator")
            for deck in mw.col.decks.all_names_and_ids():
                if deck.name != "Bulk Card Creator":
                    self.deck_combo.addItem(deck.name)

    def _on_new_deck(self) -> None:
        name, ok = QInputDialog.getText(
            self, _t("dlg_new_deck_title"), _t("dlg_new_deck_prompt")
        )
        name = name.strip() if name else ""
        if not ok or not name:
            return

        for i in range(self.deck_combo.count()):
            if self.deck_combo.itemText(i) == name:
                self.deck_combo.setCurrentIndex(i)
                return

        self.deck_combo.addItem(name)
        self.deck_combo.setCurrentText(name)

    def _on_search_note_type(self) -> None:
        if not mw or not mw.col:
            return
        items = sorted([model["name"] for model in mw.col.models.all()])
        current = self.note_type_combo.currentText().strip()
        dialog = SearchSelectDialog(_t("title_search_note_type"), items, current, parent=self)
        if dialog.exec():
            selected = dialog.get_selected()
            if selected:
                self.note_type_combo.setCurrentText(selected)

    def _on_search_deck(self) -> None:
        if not mw or not mw.col:
            return
        items = ["Bulk Card Creator"] + sorted([deck.name for deck in mw.col.decks.all_names_and_ids() if deck.name != "Bulk Card Creator"])
        current = self.deck_combo.currentText().strip()
        dialog = SearchSelectDialog(_t("title_search_deck"), items, current, parent=self)
        if dialog.exec():
            selected = dialog.get_selected()
            if selected:
                self.deck_combo.setCurrentText(selected)

    def _load_presets(self) -> None:
        self.preset_combo.clear()
        self.preset_combo.addItem(_t("main_preset_none"))
        for name in sorted(get_presets().keys()):
            self.preset_combo.addItem(name)

    def _on_save_preset(self) -> None:
        raw_text = self.json_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_empty")
            )
            return

        try:
            cards = json.loads(raw_text)
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self, _t("title_json_error"),
                _t("msg_invalid_json", error=str(e)),
            )
            return

        if not isinstance(cards, list):
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_must_be_array")
            )
            return

        name, ok = QInputDialog.getText(
            self, _t("dlg_save_preset_title"), _t("dlg_save_preset_prompt")
        )
        name = name.strip() if name else ""
        if not ok or not name:
            return

        match_text = self.match_field_combo.currentText()
        match_field = None
        if not (match_text.startswith("None") or match_text == _t("main_smart_sync_none")):
            match_field = match_text

        save_preset(name, {
            "note_type": self.note_type_combo.currentText().strip(),
            "deck": self.deck_combo.currentText().strip() or "Bulk Card Creator",
            "match_field": match_field,
            "json_text": raw_text,
        })

        self._load_presets()
        self.preset_combo.setCurrentText(name)
        QMessageBox.information(
            self, _t("title_result"), _t("msg_preset_saved", name=name)
        )

    def _on_load_preset(self) -> None:
        preset_name = self.preset_combo.currentText().strip()
        if not preset_name or preset_name == _t("main_preset_none"):
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_select_preset")
            )
            return

        preset = get_presets().get(preset_name)
        if not isinstance(preset, dict):
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_preset_not_found", name=preset_name)
            )
            return

        note_type = str(preset.get("note_type", "")).strip()
        if note_type:
            self.note_type_combo.setCurrentText(note_type)

        deck = str(preset.get("deck", "")).strip()
        if deck:
            found = False
            for i in range(self.deck_combo.count()):
                if self.deck_combo.itemText(i) == deck:
                    self.deck_combo.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.deck_combo.addItem(deck)
                self.deck_combo.setCurrentText(deck)

        match_field = preset.get("match_field")
        if isinstance(match_field, str) and match_field:
            idx = self.match_field_combo.findText(match_field)
            if idx >= 0:
                self.match_field_combo.setCurrentIndex(idx)
            else:
                self.match_field_combo.setCurrentIndex(0)
        else:
            self.match_field_combo.setCurrentIndex(0)

        json_text = preset.get("json_text", "")
        if isinstance(json_text, str):
            self.json_input.setPlainText(json_text)

        QMessageBox.information(
            self, _t("title_result"), _t("msg_preset_loaded", name=preset_name)
        )

    def _on_generate_guid(self) -> None:
        raw_text = self.json_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_empty")
            )
            return

        try:
            cards = json.loads(raw_text)
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self, _t("title_json_error"),
                _t("msg_invalid_json", error=str(e)),
            )
            return

        if not isinstance(cards, list):
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_must_be_array")
            )
            return

        changed = 0
        for card in cards:
            if not isinstance(card, dict):
                continue
            current_guid = str(card.get("__guid__", "")).strip()
            if not current_guid:
                card["__guid__"] = guid64()
                changed += 1

        self.json_input.setPlainText(json.dumps(cards, indent=2, ensure_ascii=False))
        QMessageBox.information(
            self,
            _t("title_result"),
            _t("msg_guid_generated", count=changed),
        )

    def _on_add_deck_to_json(self) -> None:
        """Add __deck__ to all cards in JSON based on selected deck."""
        raw_text = self.json_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_empty")
            )
            return

        try:
            cards = json.loads(raw_text)
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self, _t("title_json_error"),
                _t("msg_invalid_json", error=str(e)),
            )
            return

        if not isinstance(cards, list):
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_must_be_array")
            )
            return

        deck_name = self.deck_combo.currentText().strip() or "Bulk Card Creator"
        if not deck_name:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_select_deck")
            )
            return

        changed = 0
        for card in cards:
            if not isinstance(card, dict):
                continue
            if "__deck__" not in card:
                card["__deck__"] = deck_name
                changed += 1

        self.json_input.setPlainText(json.dumps(cards, indent=2, ensure_ascii=False))
        QMessageBox.information(
            self,
            _t("title_result"),
            _t("msg_deck_added", deck=deck_name, count=changed),
        )

    def _on_open_history(self) -> None:
        history_dir = get_history_dir()
        try:
            os.startfile(history_dir)
        except Exception:
            QMessageBox.information(
                self,
                _t("title_result"),
                _t("msg_history_path", path=history_dir),
            )

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, _t("btn_import_json"), "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.json_input.setPlainText(content)
        except Exception as e:
            QMessageBox.critical(
                self, _t("title_import_error"), str(e)
            )

    def _on_export_json(self) -> None:
        text = self.json_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_empty")
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, _t("btn_export_json"), "cards.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(
                self, _t("title_export"),
                _t("msg_saved_to", path=path),
            )
        except Exception as e:
            QMessageBox.critical(
                self, _t("title_export_error"), str(e)
            )

    def _on_copy_prompt(self) -> None:
        note_type_name = self.note_type_combo.currentText()
        field_names: List[str] = []
        if mw and mw.col:
            model = mw.col.models.by_name(note_type_name)
            if model:
                field_names = [f['name'] for f in model['flds']]

        if not field_names:
            field_names = ["Front", "Back"]

        media_map = get_media_mappings(note_type_name)
        prompt = generate_ai_prompt(field_names, media_map)

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(prompt)
            QMessageBox.information(
                self, _t("title_copied"),
                _t("msg_prompt_copied"),
            )


    def _on_media_config(self) -> None:
        note_type_name = self.note_type_combo.currentText()
        field_names: List[str] = []
        if mw and mw.col:
            model = mw.col.models.by_name(note_type_name)
            if model:
                field_names = [f['name'] for f in model['flds']]
        if not field_names:
            field_names = ["Front", "Back"]
        dialog = MediaConfigDialog(note_type_name, field_names, parent=self)
        dialog.exec()

    def _on_note_type_changed(self, note_type_name: str) -> None:
        if not note_type_name or not mw or not mw.col:
            return

        model = mw.col.models.by_name(note_type_name)
        if not model:
            template = [{"Front": "insert_your_content_here", "Back": "insert_your_content_here"}]
            field_names = ["Front", "Back"]
        else:
            template_dict = {}
            field_names = []
            for fld in model['flds']:
                template_dict[fld['name']] = "insert_your_content_here"
                field_names.append(fld['name'])
            template = [template_dict]

        formatted_json = json.dumps(template, indent=2, ensure_ascii=False)
        self.json_input.setPlainText(formatted_json)

        self.match_field_combo.clear()
        self.match_field_combo.addItem(_t("main_smart_sync_none"))
        for name in field_names:
            self.match_field_combo.addItem(name)

    # ---- view as table ----

    def _on_view_as_table(self) -> None:
        raw_text = self.json_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_empty")
            )
            return

        try:
            cards = json.loads(raw_text)
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self, _t("title_json_error"),
                _t("msg_fix_json", error=str(e)),
            )
            return

        if not isinstance(cards, list) or not cards:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_must_array")
            )
            return

        for idx, item in enumerate(cards):
            if not isinstance(item, dict):
                QMessageBox.warning(
                    self, _t("title_error"),
                    _t("msg_item_not_object", index=idx + 1),
                )
                return

        mappings = get_media_mappings(self.note_type_combo.currentText())
        dialog = TablePreviewDialog(
            cards, media_mappings=mappings, parent=self
        )
        if dialog.exec():
            updated_json = dialog.get_json_text()
            self.json_input.setPlainText(updated_json)

    # ---- submit ----

    def _on_submit(self) -> None:
        if not mw or not mw.col:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_open_collection")
            )
            return

        raw_text = self.json_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_empty")
            )
            return

        try:
            cards = json.loads(raw_text)
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self, _t("title_json_error"),
                _t("msg_invalid_json", error=str(e)),
            )
            return

        if not isinstance(cards, list):
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_must_be_array")
            )
            return

        if not cards:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_json_array_empty")
            )
            return

        for idx, item in enumerate(cards):
            if not isinstance(item, dict):
                QMessageBox.warning(
                    self, _t("title_error"),
                    _t("msg_item_not_object", index=idx + 1),
                )
                return

        note_type_name = self.note_type_combo.currentText()
        deck_name = self.deck_combo.currentText().strip() or "Bulk Card Creator"

        match_text = self.match_field_combo.currentText()
        match_field = None if match_text.startswith("None") or match_text == _t("main_smart_sync_none") else match_text

        mappings = get_media_mappings(note_type_name)

        try:
            created, updated, warnings = create_cards_logic(
                deck_name, note_type_name, cards,
                match_field=match_field, media_mappings=mappings,
                on_progress_start=lambda label: mw.progress.start(label=label, immediate=True) if (mw and getattr(mw, "progress", None)) else None,
                on_progress_update=lambda label: mw.progress.update(label=label) if (mw and getattr(mw, "progress", None)) else None,
                on_progress_finish=lambda: mw.progress.finish() if (mw and getattr(mw, "progress", None)) else None,
            )
        except Exception as e:
            QMessageBox.critical(self, _t("title_error"), str(e))
            return

        msg = _t("msg_done", created=created, updated=updated)
        if warnings:
            msg += _t("msg_warnings", count=len(warnings))
            msg += "\n".join(warnings[:10])
            if len(warnings) > 10:
                msg += _t("msg_warnings_more", count=len(warnings) - 10)
        if self.write_guid_checkbox.isChecked():
            msg += "\n\n" + _t("msg_guids_written")

        QMessageBox.information(self, _t("title_result"), msg)

        try:
            history_path = save_batch_history({
                "note_type": note_type_name,
                "deck": deck_name,
                "match_field": match_field,
                "created": created,
                "updated": updated,
                "warnings": warnings,
                "write_guid_backfill": self.write_guid_checkbox.isChecked(),
                "cards": cards,
            })
        except Exception as e:
            QMessageBox.warning(
                self,
                _t("title_error"),
                _t("msg_history_save_failed", error=str(e)),
            )
            history_path = None

        if self.write_guid_checkbox.isChecked():
            self.json_input.setPlainText(
                json.dumps(cards, indent=2, ensure_ascii=False)
            )
        else:
            self.json_input.clear()

            # _load_note_types clear combo → mặc định nhảy về item đầu; giữ lại loại note vừa dùng
            saved_note_type = note_type_name.strip()
            self._load_note_types()
            if saved_note_type:
                self.note_type_combo.setCurrentText(saved_note_type)

        if history_path:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(_t("title_result"))
            msg_box.setText(_t("msg_history_saved", path=history_path))
            
            open_btn = msg_box.addButton(_t("btn_open_history_folder"), QMessageBox.ButtonRole.ActionRole)
            close_btn = msg_box.addButton(_t("btn_close"), QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(close_btn)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == open_btn:
                self._on_open_history()

    def _on_choose_stats(self) -> None:
        dialog = StatsConfigDialog(current=self._selected_stats, parent=self)
        if dialog.exec():
            self._selected_stats = dialog.selected_stats()

    def _on_fetch_deck_data(self) -> None:
        deck_name = self.deck_combo.currentText().strip()
        include_stats = bool(self._selected_stats)
        if not deck_name:
            QMessageBox.warning(
                self, _t("title_error"), _t("msg_select_deck_for_export")
            )
            return
            
        try:
            # Gọi hàm xử lý lấy data
            cards_data, found_note_type = export_deck_to_json_logic(
                deck_name,
                include_stats=include_stats,
                stats=self._selected_stats if include_stats else None,
            )
            
            if not cards_data:
                QMessageBox.information(
                    self,
                    _t("title_result"),
                    _t("msg_deck_export_empty", deck=deck_name),
                )
                return
                
            # Đổi loại Note Type tương ứng với deck vừa lấy
            if found_note_type:
                idx = self.note_type_combo.findText(found_note_type)
                if idx >= 0:
                    self.note_type_combo.setCurrentIndex(idx)
                else:
                    self.note_type_combo.addItem(found_note_type)
                    self.note_type_combo.setCurrentText(found_note_type)

            # Chuyển đổi mảng dict thành chuỗi JSON đẹp
            json_text = json.dumps(cards_data, indent=2, ensure_ascii=False)
            
            # Ghi đè vào ô nhập text JSON của giao diện
            self.json_input.setPlainText(json_text)
            
            QMessageBox.information(
                self,
                _t("title_result"),
                _t("msg_deck_export_done", count=len(cards_data), deck=deck_name),
            )
            
        except Exception as e:
            QMessageBox.critical(self, _t("title_deck_export_error"), str(e))

    def done(self, r: int) -> None:
        set_window_maximized(self.isMaximized())
        super().done(r)

    def closeEvent(self, event) -> None:
        set_window_maximized(self.isMaximized())
        super().closeEvent(event)

