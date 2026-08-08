from aqt import mw
from aqt import gui_hooks
from aqt.qt import QAction, qconnect, QMenu


# ---------------------------------------------------------------------------
# Menu: tìm hoặc tạo menu "AnkiVN" trên thanh menubar
# ---------------------------------------------------------------------------

ANKIVN_MENU_OBJECT_NAME = "sf_ankivn_menu"


def get_or_create_ankivn_menu() -> QMenu:
    """Tìm menu 'AnkiVN' đã có (theo objectName do SuperFreeTTS đặt),
    hoặc tạo mới nếu chưa addon nào tạo."""
    if not mw or not mw.form:
        raise RuntimeError("Main window not ready")

    menubar = mw.form.menubar

    # Ưu tiên tìm theo objectName (chuẩn dùng chung với SuperFreeTTS)
    for action in menubar.actions():
        if action.objectName() == ANKIVN_MENU_OBJECT_NAME:
            menu = action.menu()
            if menu:
                return menu

    # Fallback: tìm theo text hiển thị
    for action in menubar.actions():
        if action.text().replace("&", "") == "AnkiVN":
            menu = action.menu()
            if menu:
                return menu

    # Chưa có → tạo mới, đặt objectName giống SuperFreeTTS để addon sau nhận ra
    ankivn_menu = QMenu("AnkiVN", mw)
    ankivn_menu.setObjectName(ANKIVN_MENU_OBJECT_NAME)
    ankivn_menu.menuAction().setObjectName(ANKIVN_MENU_OBJECT_NAME)

    help_action = None
    for action in menubar.actions():
        if action.text().lower().replace("&", "") == "help":
            help_action = action
            break

    if help_action:
        menubar.insertMenu(help_action, ankivn_menu)
    else:
        menubar.addMenu(ankivn_menu)

    return ankivn_menu


# ---------------------------------------------------------------------------
# Entry: show dialog (lazy import để Anki khởi động nhanh)
# ---------------------------------------------------------------------------

def show_dialog() -> None:
    from .i18n import load_lang_from_config
    load_lang_from_config()

    from .gui.main_dialog import BulkCardCreatorDialog
    dialog = BulkCardCreatorDialog(mw)
    dialog.exec()

# ---------------------------------------------------------------------------
# Welcome Popup Hook
# ---------------------------------------------------------------------------

def check_and_show_welcome() -> None:
    """Hiện Welcome dialog nếu người dùng lần đầu cài hoặc chưa bấm 'Don't show this again'."""
    from .config import get_welcome_shown, set_welcome_shown
    
    if get_welcome_shown():
        return

    from .gui.welcome_dialog import WelcomeDialog
    dialog = WelcomeDialog(mw)
    dialog.exec()

    if dialog.dont_show_again():
        set_welcome_shown(True)

# Gắn Welcome popup vào sự kiện profile_did_open (để không bị lag splash screen)
gui_hooks.profile_did_open.append(check_and_show_welcome)


# ---------------------------------------------------------------------------
# Đăng ký menu "AnkiVN" > "🚀 JSON Bulk Importer - from AnkiVN with ❤️"
# ---------------------------------------------------------------------------

if mw and mw.form:
    ankivn_menu = get_or_create_ankivn_menu()
    action = QAction("JSON Bulk Importer - from AnkiVN with ❤️", mw)
    qconnect(action.triggered, show_dialog)
    ankivn_menu.addAction(action)
