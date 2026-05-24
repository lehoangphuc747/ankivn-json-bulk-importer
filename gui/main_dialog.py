import json
import os
from typing import Any, List, Optional

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QCheckBox,
    QPlainTextEdit, QPushButton, QMessageBox, Qt,
    QInputDialog, QFileDialog, QApplication, QSplitter, QWidget, QFontDatabase,
    QScrollArea, QStyle, QSize, QSizePolicy,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QColor, QBrush,
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
from .table_dialog import TablePreviewDialog
from .search_dialog import SearchSelectDialog


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
        self.setMinimumSize(950, 600)

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

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Nhập thẻ (Import)
        self.import_tab = self._build_import_tab()
        self.tabs.addTab(self.import_tab, _t("tab_import"))

        # Tab 2: Xuất thẻ (Export)
        self.export_tab = self._build_export_tab()
        self.tabs.addTab(self.export_tab, _t("tab_export"))

        # Tab 3: Trợ lý AI (Prompts)
        self.prompt_tab = self._build_prompt_tab()
        self.tabs.addTab(self.prompt_tab, _t("tab_ai_helper"))

        # Load initial values
        self._load_note_types()
        self._load_decks()
        self._load_presets()

        first_note_type = self.note_type_combo.currentText()
        if first_note_type:
            self._on_note_type_changed(first_note_type)

    def _build_import_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Header Row (Language & Help)
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel(_t("lang_label")))
        self.lang_combo = QComboBox()
        supported = get_supported_langs()
        current_lang = get_current_lang()
        for code, display in supported.items():
            self.lang_combo.addItem(display, code)
            if code == current_lang:
                self.lang_combo.setCurrentIndex(self.lang_combo.count() - 1)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        header_row.addWidget(self.lang_combo, stretch=1)

        help_btn = self._make_icon_button(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton),
            _t("btn_help"),
            self._on_help,
        )
        header_row.addWidget(help_btn)
        layout.addLayout(header_row)

        # 2. Config Row (Note Type & Deck)
        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(10)

        # Note Type
        nt_layout = QVBoxLayout()
        nt_layout.setSpacing(2)
        nt_layout.addWidget(QLabel(_t("main_note_type")))
        self.note_type_combo = ClickableComboBox(self, self._on_search_note_type)
        self.note_type_combo.setMinimumWidth(200)
        self.note_type_combo.currentTextChanged.connect(self._on_note_type_changed)
        nt_layout.addWidget(self.note_type_combo)
        cfg_row.addLayout(nt_layout, stretch=1)

        # Deck
        deck_layout = QVBoxLayout()
        deck_layout.setSpacing(2)
        deck_layout.addWidget(QLabel(_t("main_deck")))
        deck_input_row = QHBoxLayout()
        deck_input_row.setSpacing(5)
        self.deck_combo = ClickableComboBox(self, self._on_search_deck)
        self.deck_combo.setMinimumWidth(200)
        deck_input_row.addWidget(self.deck_combo, stretch=1)

        new_deck_btn = self._make_icon_button(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            _t("btn_new_deck"),
            self._on_new_deck,
        )
        deck_input_row.addWidget(new_deck_btn)
        deck_layout.addLayout(deck_input_row)
        cfg_row.addLayout(deck_layout, stretch=1)
        
        layout.addLayout(cfg_row)

        # 3. Main Splitter (JSON thô | Live Preview Table)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel (JSON Input & tools)
        json_panel = QWidget()
        json_layout = QVBoxLayout(json_panel)
        json_layout.setContentsMargins(0, 0, 0, 0)
        json_layout.setSpacing(5)

        # JSON tools row
        json_tools_row = QHBoxLayout()
        json_tools_row.setSpacing(6)
        
        import_btn = self._make_text_button(_t("btn_import_json"), self._on_import_json, _t("toolbar_import_json"), flexible=False)
        json_tools_row.addWidget(import_btn)
        
        export_btn = self._make_text_button(_t("btn_export_json"), self._on_export_json, _t("toolbar_export_json"), flexible=False)
        json_tools_row.addWidget(export_btn)
        
        prompt_btn = self._make_text_button(_t("btn_copy_prompt"), self._on_copy_prompt, _t("tooltip_copy_prompt"), flexible=False)
        json_tools_row.addWidget(prompt_btn)

        json_tools_row.addStretch()
        json_layout.addLayout(json_tools_row)

        self.json_input = QPlainTextEdit()
        self.json_input.setPlaceholderText(_t("main_json_placeholder"))
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.json_input.setFont(fixed_font)
        self.json_input.textChanged.connect(self._validate_json_realtime)
        json_layout.addWidget(self.json_input, stretch=1)
        
        # Right Panel (Live Preview Table)
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(5)
        
        preview_layout.addWidget(QLabel(_t("table_title") or "Bảng xem trước (Live Preview):"))
        self.live_table_preview = QTableWidget()
        self.live_table_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.live_table_preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        preview_layout.addWidget(self.live_table_preview, stretch=1)

        splitter.addWidget(json_panel)
        splitter.addWidget(preview_panel)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, stretch=1)

        # 4. Advanced Config (Group Box)
        advanced_group = QGroupBox(_t("section_advanced_collapsed") or "Công cụ nâng cao")
        adv_layout = QHBoxLayout(advanced_group)
        adv_layout.setContentsMargins(8, 8, 8, 8)
        adv_layout.setSpacing(10)

        # Smart Sync
        sync_layout = QVBoxLayout()
        sync_layout.setSpacing(2)
        sync_layout.addWidget(QLabel(_t("main_smart_sync")))
        self.match_field_combo = QComboBox()
        self.match_field_combo.addItem(_t("main_smart_sync_none"))
        adv_layout.addLayout(sync_layout, stretch=1)

        # Options Checklist
        opts_layout = QVBoxLayout()
        self.write_guid_checkbox = QCheckBox(_t("chk_write_guids_short"))
        self.write_guid_checkbox.setChecked(True)
        self.write_guid_checkbox.setToolTip(_t("tooltip_write_guids"))
        opts_layout.addWidget(self.write_guid_checkbox)
        
        generate_guid_btn = self._make_text_button(_t("btn_generate_guid_short"), self._on_generate_guid, _t("tooltip_generate_guid"))
        opts_layout.addWidget(generate_guid_btn)
        adv_layout.addLayout(opts_layout, stretch=1)

        # Media & Presets
        media_preset_layout = QVBoxLayout()
        media_preset_layout.setSpacing(2)
        media_cfg_btn = self._make_text_button(_t("btn_media_config_short"), self._on_media_config, _t("tooltip_media_config"))
        media_preset_layout.addWidget(media_cfg_btn)
        
        # Presets dropdown
        preset_row = QHBoxLayout()
        preset_row.setSpacing(5)
        self.preset_combo = QComboBox()
        preset_row.addWidget(self.preset_combo, stretch=1)
        
        load_preset_btn = self._make_text_button(_t("btn_load_preset_short"), self._on_load_preset, _t("btn_load_preset"))
        preset_row.addWidget(load_preset_btn)
        
        save_preset_btn = self._make_text_button(_t("btn_save_preset_short"), self._on_save_preset, _t("btn_save_preset"))
        preset_row.addWidget(save_preset_btn)
        
        media_preset_layout.addLayout(preset_row)
        adv_layout.addLayout(media_preset_layout, stretch=2)

        # History & Deck Tools
        hist_deck_layout = QVBoxLayout()
        hist_deck_layout.setSpacing(2)
        history_btn = self._make_text_button(_t("btn_history"), self._on_open_history, _t("tooltip_open_history"))
        hist_deck_layout.addWidget(history_btn)
        
        add_deck_btn = self._make_text_button(_t("btn_add_deck_to_json_short"), self._on_add_deck_to_json, _t("tooltip_add_deck_to_json"))
        hist_deck_layout.addWidget(add_deck_btn)
        
        adv_layout.addLayout(hist_deck_layout, stretch=1)

        layout.addWidget(advanced_group)

        # 5. Action Row
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.create_btn = QPushButton(_t("btn_create_update"))
        self.create_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.create_btn.setDefault(True)
        self.create_btn.setMinimumSize(170, 36)
        self.create_btn.clicked.connect(self._on_submit)
        action_layout.addWidget(self.create_btn)

        close_btn = QPushButton(_t("btn_close"))
        close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        close_btn.setMinimumHeight(36)
        close_btn.setToolTip(_t("tooltip_close"))
        close_btn.clicked.connect(self.close)
        action_layout.addWidget(close_btn)

        layout.addLayout(action_layout)

        return widget

    def _build_export_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Deck Source Row
        source_layout = QHBoxLayout()
        source_layout.setSpacing(10)
        
        source_layout.addWidget(QLabel(_t("main_deck")))
        self.export_deck_combo = ClickableComboBox(self, self._on_search_export_deck)
        self.export_deck_combo.setMinimumWidth(250)
        self.export_deck_combo.currentTextChanged.connect(self._on_export_deck_changed)
        source_layout.addWidget(self.export_deck_combo, stretch=1)

        self.export_include_stats_checkbox = QCheckBox(_t("chk_include_stats_short"))
        self.export_include_stats_checkbox.setToolTip(_t("tooltip_include_stats"))
        self.export_include_stats_checkbox.stateChanged.connect(lambda: self._on_export_deck_changed(self.export_deck_combo.currentText()))
        source_layout.addWidget(self.export_include_stats_checkbox)

        source_layout.addStretch()
        layout.addLayout(source_layout)

        # 2. Preview Table
        layout.addWidget(QLabel(_t("table_title") or "Bảng xem trước (Live Preview):"))
        self.export_preview_table = QTableWidget()
        self.export_preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.export_preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.export_preview_table, stretch=1)

        # 3. Actions Row
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.export_load_to_import_btn = QPushButton(_t("btn_load_to_import") or "Nạp sang Tab Nhập")
        self.export_load_to_import_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.export_load_to_import_btn.clicked.connect(self._on_export_load_to_import)
        action_layout.addWidget(self.export_load_to_import_btn)

        self.export_save_file_btn = QPushButton(_t("btn_export_json") or "Lưu thành File JSON")
        self.export_save_file_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.export_save_file_btn.clicked.connect(self._on_export_save_file)
        self.export_save_file_btn.setDefault(True)
        self.export_save_file_btn.setMinimumHeight(36)
        action_layout.addWidget(self.export_save_file_btn)

        layout.addLayout(action_layout)

        return widget

    def _build_prompt_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Note Type selection
        selection_layout = QHBoxLayout()
        selection_layout.setSpacing(10)
        selection_layout.addWidget(QLabel(_t("main_note_type")))
        self.prompt_note_type_combo = ClickableComboBox(self, self._on_search_prompt_note_type)
        self.prompt_note_type_combo.setMinimumWidth(250)
        self.prompt_note_type_combo.currentTextChanged.connect(self._update_prompt_text)
        selection_layout.addWidget(self.prompt_note_type_combo, stretch=1)
        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        # 2. Prompt Text Area
        layout.addWidget(QLabel(_t("btn_copy_prompt") or "Prompt mẫu cho AI (ChatGPT/Claude/Gemini):"))
        self.prompt_text_area = QPlainTextEdit()
        self.prompt_text_area.setReadOnly(True)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.prompt_text_area.setFont(fixed_font)
        layout.addWidget(self.prompt_text_area, stretch=1)

        # 3. Actions Row
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.prompt_copy_btn = QPushButton(_t("btn_copy_prompt") or "Sao chép Prompt")
        self.prompt_copy_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.prompt_copy_btn.clicked.connect(self._on_copy_prompt_tab)
        self.prompt_copy_btn.setMinimumHeight(36)
        self.prompt_copy_btn.setDefault(True)
        action_layout.addWidget(self.prompt_copy_btn)

        layout.addLayout(action_layout)

        return widget

    def _make_icon_button(
        self,
        icon: Any,
        tooltip: str,
        callback: Any,
        size: int = 28,
    ) -> QPushButton:
        button = QPushButton()
        button.setIcon(icon)
        button.setIconSize(QSize(size - 8, size - 8))
        button.setFixedSize(size, size)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        return button

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
            cards = json.loads(text)
            # Nếu JSON hợp lệ: Viền xanh lá mỏng
            valid_color = "#81C784" if is_night else "#4CAF50"
            self.json_input.setStyleSheet(f"QPlainTextEdit {{ border: 2px solid {valid_color}; border-radius: 4px; }}")
            if isinstance(cards, list):
                self._update_live_table(cards)
            else:
                self.live_table_preview.setRowCount(0)
        except json.JSONDecodeError:
            # Nếu JSON lỗi: Viền đỏ báo hiệu
            invalid_color = "#EF5350" if is_night else "#F44336"
            self.json_input.setStyleSheet(f"QPlainTextEdit {{ border: 2px solid {invalid_color}; border-radius: 4px; }}")
            self.live_table_preview.setRowCount(0)


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

    # ---- helpers ----

    def _load_note_types(self) -> None:
        self.note_type_combo.clear()
        if hasattr(self, "prompt_note_type_combo"):
            self.prompt_note_type_combo.clear()
        if mw and mw.col:
            for model in mw.col.models.all():
                self.note_type_combo.addItem(model["name"])
                if hasattr(self, "prompt_note_type_combo"):
                    self.prompt_note_type_combo.addItem(model["name"])

    def _load_decks(self) -> None:
        self.deck_combo.clear()
        if hasattr(self, "export_deck_combo"):
            self.export_deck_combo.clear()
        if mw and mw.col:
            self.deck_combo.addItem("Bulk Card Creator")
            if hasattr(self, "export_deck_combo"):
                self.export_deck_combo.addItem("Bulk Card Creator")
            for deck in mw.col.decks.all_names_and_ids():
                if deck.name != "Bulk Card Creator":
                    self.deck_combo.addItem(deck.name)
                    if hasattr(self, "export_deck_combo"):
                        self.export_deck_combo.addItem(deck.name)

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
                if hasattr(self, "export_deck_combo"):
                    idx = self.export_deck_combo.findText(name)
                    if idx >= 0:
                        self.export_deck_combo.setCurrentIndex(idx)
                return

        self.deck_combo.addItem(name)
        self.deck_combo.setCurrentText(name)
        if hasattr(self, "export_deck_combo"):
            self.export_deck_combo.addItem(name)
            self.export_deck_combo.setCurrentText(name)

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

    def _on_search_export_deck(self) -> None:
        if not mw or not mw.col:
            return
        items = ["Bulk Card Creator"] + sorted([deck.name for deck in mw.col.decks.all_names_and_ids() if deck.name != "Bulk Card Creator"])
        current = self.export_deck_combo.currentText().strip()
        dialog = SearchSelectDialog(_t("title_search_deck"), items, current, parent=self)
        if dialog.exec():
            selected = dialog.get_selected()
            if selected:
                self.export_deck_combo.setCurrentText(selected)

    def _on_search_prompt_note_type(self) -> None:
        if not mw or not mw.col:
            return
        items = sorted([model["name"] for model in mw.col.models.all()])
        current = self.prompt_note_type_combo.currentText().strip()
        dialog = SearchSelectDialog(_t("title_search_note_type"), items, current, parent=self)
        if dialog.exec():
            selected = dialog.get_selected()
            if selected:
                self.prompt_note_type_combo.setCurrentText(selected)

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

    def _update_live_table(self, cards: List[dict]) -> None:
        self.live_table_preview.clear()
        if not cards or not isinstance(cards, list):
            self.live_table_preview.setRowCount(0)
            self.live_table_preview.setColumnCount(0)
            return

        seen: dict = {}
        for card in cards:
            if isinstance(card, dict):
                for key in card:
                    if key not in seen:
                        seen[key] = True

        from .table_dialog import META_KEY_ORDER
        meta_cols = [k for k in META_KEY_ORDER if k in seen]
        content_cols = [k for k in seen if k not in META_KEY_ORDER]
        columns = meta_cols + content_cols

        self.live_table_preview.setColumnCount(len(columns))
        self.live_table_preview.setHorizontalHeaderLabels(columns)
        self.live_table_preview.setRowCount(len(cards))

        note_type_name = self.note_type_combo.currentText()
        media_mappings = get_media_mappings(note_type_name) or {}

        for row, card in enumerate(cards):
            if not isinstance(card, dict):
                continue
            for col_idx, col_name in enumerate(columns):
                value = card.get(col_name, "")
                if col_name == "__tags__" and isinstance(value, list):
                    display = ", ".join(str(v) for v in value)
                elif isinstance(value, (dict, list)):
                    display = json.dumps(value, ensure_ascii=False)
                else:
                    display = str(value) if value != "" else ""

                item = QTableWidgetItem(display)
                ftype = media_mappings.get(col_name, "text")
                if ftype in ("image", "audio"):
                    item.setBackground(QBrush(QColor(230, 247, 255)))
                self.live_table_preview.setItem(row, col_idx, item)

        self.live_table_preview.resizeColumnsToContents()

    def _on_export_deck_changed(self, deck_name: str) -> None:
        if not deck_name:
            self.export_preview_table.setRowCount(0)
            return
        try:
            if not mw or not mw.col:
                return
            deck = mw.col.decks.by_name(deck_name)
            if not deck:
                self.export_preview_table.setRowCount(0)
                return

            cards_data, _ = export_deck_to_json_logic(deck_name, include_stats=self.export_include_stats_checkbox.isChecked())
            self._update_export_table(cards_data)
        except Exception:
            self.export_preview_table.setRowCount(0)

    def _update_export_table(self, cards: List[dict]) -> None:
        self.export_preview_table.clear()
        if not cards:
            self.export_preview_table.setRowCount(0)
            self.export_preview_table.setColumnCount(0)
            return

        seen: dict = {}
        for card in cards:
            for key in card:
                if key not in seen:
                    seen[key] = True

        from .table_dialog import META_KEY_ORDER
        meta_cols = [k for k in META_KEY_ORDER if k in seen]
        content_cols = [k for k in seen if k not in META_KEY_ORDER]
        columns = meta_cols + content_cols

        self.export_preview_table.setColumnCount(len(columns))
        self.export_preview_table.setHorizontalHeaderLabels(columns)
        self.export_preview_table.setRowCount(len(cards))

        for row, card in enumerate(cards):
            for col_idx, col_name in enumerate(columns):
                value = card.get(col_name, "")
                if col_name == "__tags__" and isinstance(value, list):
                    display = ", ".join(str(v) for v in value)
                elif isinstance(value, (dict, list)):
                    display = json.dumps(value, ensure_ascii=False)
                else:
                    display = str(value) if value != "" else ""

                self.export_preview_table.setItem(row, col_idx, QTableWidgetItem(display))

        self.export_preview_table.resizeColumnsToContents()

    def _on_export_save_file(self) -> None:
        deck_name = self.export_deck_combo.currentText().strip()
        if not deck_name:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, _t("btn_export_json"), f"{deck_name}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return

        try:
            cards_data, _ = export_deck_to_json_logic(deck_name, include_stats=self.export_include_stats_checkbox.isChecked())
            if not cards_data:
                QMessageBox.information(self, _t("title_result"), _t("msg_deck_export_empty", deck=deck_name))
                return

            with open(path, "w", encoding="utf-8") as f:
                json.dump(cards_data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self, _t("title_export"),
                _t("msg_saved_to", path=path),
            )
        except Exception as e:
            QMessageBox.critical(self, _t("title_export_error"), str(e))

    def _on_export_load_to_import(self) -> None:
        deck_name = self.export_deck_combo.currentText().strip()
        if not deck_name:
            return

        try:
            cards_data, found_note_type = export_deck_to_json_logic(deck_name, include_stats=self.export_include_stats_checkbox.isChecked())
            if not cards_data:
                QMessageBox.information(self, _t("title_result"), _t("msg_deck_export_empty", deck=deck_name))
                return

            # Load Note Type if found
            if found_note_type:
                idx = self.note_type_combo.findText(found_note_type)
                if idx >= 0:
                    self.note_type_combo.setCurrentIndex(idx)

            json_text = json.dumps(cards_data, indent=2, ensure_ascii=False)
            self.json_input.setPlainText(json_text)
            self.tabs.setCurrentIndex(0) # Switch back to Import tab
        except Exception as e:
            QMessageBox.critical(self, _t("title_deck_export_error"), str(e))

    def _update_prompt_text(self) -> None:
        note_type_name = self.prompt_note_type_combo.currentText()
        if not note_type_name:
            self.prompt_text_area.clear()
            return
        field_names: List[str] = []
        if mw and mw.col:
            model = mw.col.models.by_name(note_type_name)
            if model:
                field_names = [f['name'] for f in model['flds']]

        if not field_names:
            field_names = ["Front", "Back"]

        media_map = get_media_mappings(note_type_name)
        prompt = generate_ai_prompt(field_names, media_map)
        self.prompt_text_area.setPlainText(prompt)

    def _on_copy_prompt_tab(self) -> None:
        prompt = self.prompt_text_area.toPlainText()
        if not prompt:
            return
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(prompt)
            QMessageBox.information(
                self, _t("title_copied"),
                _t("msg_prompt_copied"),
            )

    def done(self, r: int) -> None:
        set_window_maximized(self.isMaximized())
        super().done(r)

    def closeEvent(self, event) -> None:
        set_window_maximized(self.isMaximized())
        super().closeEvent(event)

