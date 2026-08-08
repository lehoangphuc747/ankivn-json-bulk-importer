from typing import Any

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTextBrowser, QPushButton,
    Qt, QStyle,
)

from ..i18n import _t


class HelpDialog(QDialog):

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle(_t("help_title"))
        self.setMinimumSize(760, 620)

        flags = self.windowFlags()
        flags |= Qt.WindowType.WindowMinimizeButtonHint
        flags |= Qt.WindowType.WindowMaximizeButtonHint
        flags &= ~Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        tabs = QTabWidget()
        tabs.addTab(self._build_browser(self._build_en_html()), _t("help_tab_en"))
        tabs.addTab(self._build_browser(self._build_vi_html()), _t("help_tab_vi"))
        layout.addWidget(tabs)

        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        close_btn = QPushButton(_t("btn_close"))
        close_btn.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton
        ))
        close_btn.setToolTip(_t("tooltip_close"))
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        layout.addLayout(footer_layout)

    def _build_browser(self, html: str) -> QTextBrowser:
        browser = QTextBrowser()
        browser.setHtml(html)
        return browser

    def _build_en_html(self) -> str:
        return """
        <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; }
            h1 { margin-bottom: 0.2em; }
            h2 { margin-top: 1.1em; margin-bottom: 0.3em; }
            ul { margin-top: 0.3em; }
            code { background: #f2f2f2; padding: 1px 4px; border-radius: 3px; }
          </style>
        </head>
        <body>
          <h1>🚀 JSON Bulk Importer - from AnkiVN with ❤️</h1>
          <p>Simple workflow: choose a note type, prepare JSON, preview it, then create or update cards.</p>
          <p><b>Website:</b> <a href="https://ankivn.com">https://ankivn.com</a></p>

          <h2>1. Setup</h2>
          <ul>
            <li><b>Note Type</b>: picks the Anki model used for field mapping.</li>
            <li><b>Deck</b>: selects the target deck for new cards.</li>
            <li><b>Smart Sync</b>: matches existing notes by field when <code>__guid__</code> is missing.</li>
            <li><b>Field Media Config</b>: marks fields as Image or Audio so URLs are downloaded automatically.</li>
          </ul>

          <h2>2. Tools</h2>
          <ul>
            <li><b>Save / Load Preset</b>: store and restore note type, deck, match field, and JSON text.</li>
            <li><b>Generate GUID</b>: fills missing <code>__guid__</code> values in the current JSON.</li>
            <li><b>Add Deck into JSON</b>: writes the selected deck into each object that does not already have <code>__deck__</code>.</li>
            <li><b>History</b>: opens the folder where batch history JSON files are stored.</li>
          </ul>

          <h2>3. JSON Input</h2>
          <ul>
            <li>Paste a JSON array of card objects into the editor.</li>
            <li>Use <b>Import JSON</b> and <b>Export JSON</b> to load or save a file.</li>
            <li><b>Copy Prompt for AI</b> creates a ready-to-use prompt based on the selected note type.</li>
          </ul>

          <h2>4. Table Preview</h2>
          <ul>
            <li><b>View as Table</b> opens an editable preview before importing.</li>
            <li><b>Toggle Preview Mode</b> in the table dialog shows HTML rendering for richer cells.</li>
            <li><b>Paste from Excel</b> supports TSV paste from spreadsheets.</li>
            <li><b>Pre-fetch Media</b> tests image/audio URLs before creating cards.</li>
          </ul>

          <h2>5. Create / Update</h2>
          <ul>
            <li><b>Create / Update Cards</b> imports the JSON into Anki.</li>
            <li><b>Write __guid__ back into JSON</b> keeps the generated or matched GUIDs for future reuse.</li>
          </ul>

          <h2>6. Tips</h2>
          <ul>
            <li>Use <code>__deck__</code>, <code>__tags__</code>, and <code>__guid__</code> as optional meta keys.</li>
            <li>Keep JSON as a list of objects: <code>[{...}, {...}]</code>.</li>
            <li>If you only want to preview or edit, use Table Preview before clicking Create / Update.</li>
          </ul>
        </body>
        </html>
        """

    def _build_vi_html(self) -> str:
        return """
        <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; }
            h1 { margin-bottom: 0.2em; }
            h2 { margin-top: 1.1em; margin-bottom: 0.3em; }
            ul { margin-top: 0.3em; }
            code { background: #f2f2f2; padding: 1px 4px; border-radius: 3px; }
          </style>
        </head>
        <body>
          <h1>🚀 JSON Bulk Importer - from AnkiVN with ❤️</h1>
          <p>Luồng dùng đơn giản: chọn note type, chuẩn bị JSON, xem trước rồi tạo hoặc cập nhật thẻ.</p>
          <p><b>Website:</b> <a href="https://ankivn.com">https://ankivn.com</a></p>

          <h2>1. Thiết lập</h2>
          <ul>
            <li><b>Loại thẻ</b>: chọn model Anki để map field.</li>
            <li><b>Bộ thẻ</b>: chọn deck đích cho thẻ mới.</li>
            <li><b>Smart Sync</b>: khớp note cũ theo field khi <code>__guid__</code> chưa có.</li>
            <li><b>Cấu hình Media Field</b>: đánh dấu field là Image hoặc Audio để tự tải URL.</li>
          </ul>

          <h2>2. Công cụ</h2>
          <ul>
            <li><b>Lưu / Nạp Preset</b>: lưu và khôi phục note type, deck, field khớp và JSON.</li>
            <li><b>Sinh GUID</b>: điền các giá trị <code>__guid__</code> còn thiếu trong JSON hiện tại.</li>
            <li><b>Thêm Deck vào JSON</b>: ghi deck đã chọn vào object nào chưa có <code>__deck__</code>.</li>
            <li><b>History</b>: mở thư mục lưu các file lịch sử batch dạng JSON.</li>
          </ul>

          <h2>3. Dữ liệu JSON</h2>
          <ul>
            <li>Dán một mảng JSON gồm các object thẻ vào ô nhập.</li>
            <li>Dùng <b>Import JSON</b> và <b>Export JSON</b> để mở hoặc lưu file.</li>
            <li><b>Copy Prompt cho AI</b> tạo prompt sẵn dựa trên note type đang chọn.</li>
          </ul>

          <h2>4. Xem dạng Bảng</h2>
          <ul>
            <li><b>Xem dạng Bảng</b> mở giao diện xem trước có thể sửa.</li>
            <li><b>Toggle Preview Mode</b> trong bảng cho phép xem HTML render của ô.</li>
            <li><b>Dán từ Excel</b> hỗ trợ dán TSV từ spreadsheet.</li>
            <li><b>Tải thử Media</b> kiểm tra URL ảnh/âm thanh trước khi tạo thẻ.</li>
          </ul>

          <h2>5. Tạo / Cập nhật</h2>
          <ul>
            <li><b>Tạo / Cập nhật Thẻ</b> đưa JSON vào Anki.</li>
            <li><b>Tự ghi __guid__ vào JSON</b> giữ lại GUID đã sinh hoặc đã khớp để dùng cho lần sau.</li>
          </ul>

          <h2>6. Mẹo dùng</h2>
          <ul>
            <li>Các meta key tùy chọn gồm <code>__deck__</code>, <code>__tags__</code>, và <code>__guid__</code>.</li>
            <li>JSON nên là danh sách object: <code>[{...}, {...}]</code>.</li>
            <li>Nếu chỉ muốn xem/sửa, hãy dùng bảng trước rồi mới bấm Tạo / Cập nhật.</li>
          </ul>
        </body>
        </html>
        """
