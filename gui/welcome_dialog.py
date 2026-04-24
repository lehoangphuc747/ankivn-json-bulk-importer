import os
from typing import Any

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, 
    QTextBrowser, Qt, QStyle,
)

from ..i18n import _t

class WelcomeDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle(_t("welcome_title"))
        self.setMinimumSize(600, 520)
        
        # Add flags to remove the context help button
        flags = self.windowFlags()
        flags &= ~Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        layout = QVBoxLayout(self)

        # HTML Content
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        
        # Tối ưu giao diện: Hỗ trợ tốt cho cả Light Mode và Dark Mode trên Anki
        # Trau chuốt lại câu từ mượt mà, chuyên nghiệp nhưng vẫn gần gũi
        html_content = """
        <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 10px; line-height: 1.6;">
            
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #0078d7; margin-bottom: 5px; font-size: 24px;">🎉 Chào mừng bạn đến với<br>JSON Bulk Importer</h2>
                <p style="font-style: italic; margin-top: 0; font-size: 15px;">— from AnkiVN with ❤️ —</p>
            </div>

            <p style="font-size: 15px;">
                Chào bạn, mình là <b>Phúc</b> – Admin của cộng đồng <b>Anki Việt Nam</b> (hơn 50.000 thành viên) và trang web <a href="https://ankivn.com" style="color: #0078d7; text-decoration: none;"><b>ankivn.com</b></a>. 
                Mục tiêu lớn nhất của mình là lan tỏa những giá trị tích cực và sức mạnh của Anki đến với cộng đồng học tập.
            </p>
            <p style="font-size: 15px;">
                Hy vọng rằng Add-on này sẽ là công cụ đắc lực, giúp bạn tạo và quản lý thẻ Anki một cách <b>nhanh chóng và tiện lợi nhất!</b>
            </p>

            <hr style="border: 0; border-top: 1px solid #ccc; margin: 20px 0;">

            <h3 style="color: #0078d7; margin-bottom: 10px; font-size: 18px;">👋 Kết nối với mình:</h3>
            <ul style="font-size: 15px; margin-top: 0; padding-left: 25px;">
                <li style="margin-bottom: 5px;"><b>Facebook:</b> <a href="https://www.facebook.com/tui.la.phuc747/" style="color: #0078d7; text-decoration: none;">tui.la.phuc747</a></li>
                <li style="margin-bottom: 5px;"><b>TikTok:</b> <a href="https://www.tiktok.com/@phuclee.anki" style="color: #0078d7; text-decoration: none;">@phuclee.anki</a></li>
                <li><b>Group Anki Việt Nam:</b> <a href="https://www.facebook.com/groups/ankivocabulary/" style="color: #0078d7; text-decoration: none;">Tham gia cộng đồng</a></li>
            </ul>

            <div style="border: 2px dashed #d81b60; padding: 15px; border-radius: 8px; margin: 25px 0;">
                <h3 style="color: #d81b60; margin-top: 0; text-align: center; font-size: 18px;">💖 Đôi lời về việc Donate</h3>
                <p style="text-align: center; font-size: 16px; font-weight: bold; color: #d81b60; margin: 10px 0;">"Tui hông nhận donate đâu nha!" 😆</p>
                <p style="font-size: 15px;">
                    Nếu bạn thấy Add-on này hữu ích và có nhã ý ủng hộ, xin hãy dùng số tiền đó để làm những việc ý nghĩa hơn như: quan tâm, giúp đỡ gia đình, bố mẹ, những người xung quanh, gửi về <b>Mặt trận Tổ quốc Việt Nam</b>, cúng dường, hoặc đóng góp cho các quỹ thiện nguyện.
                </p>
                <p style="font-size: 15px; margin-bottom: 0;">
                    <i>Gợi ý từ mình:</i> <a href="https://vukimhanh.com/mot-cau-chuyen-dep/" style="color: #d81b60; text-decoration: none; font-weight: bold;">Phòng khám Phước Thiện của BS Lý Minh Tâm</a> 
                    (<a href="https://www.facebook.com/reel/1150160139962288" style="color: #d81b60; text-decoration: none;">Xem Video</a>).
                </p>
            </div>

            <p style="text-align: center; font-size: 15px; margin-top: 15px;">
                ⭐ Nếu bạn thấy Add-on có ích, xin đừng quên <b>cho tui 1 Thumbs Up (Upvote)</b> tại đây nhé:<br>
                <a href="https://ankiweb.net/shared/info/829928463" style="color: #0078d7; text-decoration: none; font-weight: bold; font-size: 16px;">🔥 Đánh giá trên AnkiWeb 🔥</a>
            </p>

            <p style="text-align: center; font-size: 16px; color: #0078d7; font-weight: bold; margin-top: 20px;">
                ✨ Chúc cả nhà học hành ngày càng tiến bộ, luôn vui vẻ, khoẻ mạnh và bình an! ✨
            </p>
            
        </div>
        """
        self.browser.setHtml(html_content)
        layout.addWidget(self.browser)

        # Bottom row: Checkbox and Close button
        bottom_layout = QHBoxLayout()
        
        self.dont_show_cb = QCheckBox(_t("welcome_dont_show_again"))
        bottom_layout.addWidget(self.dont_show_cb)
        
        bottom_layout.addStretch()
        
        self.close_btn = QPushButton(_t("btn_close"))
        self.close_btn.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton
        ))
        self.close_btn.setToolTip(_t("tooltip_close"))
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setDefault(True)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)

    def dont_show_again(self) -> bool:
        return self.dont_show_cb.isChecked()
