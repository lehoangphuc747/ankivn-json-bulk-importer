from typing import Any, List, Optional
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QStyle, Qt,
)
from ..i18n import _t


class SearchSelectDialog(QDialog):
    def __init__(self, title: str, items: List[str], current_item: str = "", parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 500)
        self.selected_item = None
        
        # Add flags to remove the context help button
        flags = self.windowFlags()
        flags &= ~Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(flags)
        
        layout = QVBoxLayout(self)
        
        # Search input
        search_layout = QHBoxLayout()
        search_label = QLabel(_t("search_label") if _t("search_label") != "search_label" else "Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(_t("search_placeholder") if _t("search_placeholder") != "search_placeholder" else "Type to search...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # List of items
        self.list_widget = QListWidget()
        self.items = items
        self.populate_list(items)
        layout.addWidget(self.list_widget)
        
        # Highlight current item if it exists in the list
        if current_item:
            matching_items = self.list_widget.findItems(current_item, Qt.MatchFlag.MatchExactly)
            if matching_items:
                self.list_widget.setCurrentItem(matching_items[0])
                
        # Connect search text change
        self.search_input.textChanged.connect(self.on_search_changed)
        # Double click item to select and close
        self.list_widget.itemDoubleClicked.connect(self.on_select)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.select_btn = QPushButton(_t("btn_select") if _t("btn_select") != "btn_select" else "Select")
        self.select_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.select_btn.clicked.connect(self.on_select)
        btn_layout.addWidget(self.select_btn)
        
        self.close_btn = QPushButton(_t("btn_close"))
        self.close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)

    def populate_list(self, items: List[str]) -> None:
        self.list_widget.clear()
        for item in items:
            self.list_widget.addItem(item)

    def on_search_changed(self, text: str) -> None:
        filtered = [item for item in self.items if text.lower() in item.lower()]
        self.populate_list(filtered)

    def on_select(self) -> None:
        current = self.list_widget.currentItem()
        if current:
            self.selected_item = current.text()
            self.accept()
        else:
            self.reject()
            
    def get_selected(self) -> Optional[str]:
        return self.selected_item
