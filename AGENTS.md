# AGENTS.md — JSON Bulk Importer (Anki addon)

Anki addon thuần Python (không webview/React). Chạy **trong Anki**, không có test runner, lint hay typecheck. Mọi xác minh đều phải qua Anki thật: cài addon → restart Anki → menu `AnkiVN` → mở dialog → import thử JSON.

## Kiến trúc

- `__init__.py` — entry point: đăng ký menu `AnkiVN` (objectName `sf_ankivn_menu`, dùng chung với SuperFreeTTS) + `show_dialog()` lazy import `gui/main_dialog.py`.
- `gui/*` — chỉ điều phối/validate input và gọi core; **không** để logic DB/media trong dialog.
- `core.py` — logic Anki DB: `create_cards_logic()`, `create_new_model()`, `export_deck_to_json_logic()`.
- `media.py` — `smart_download_media()`, `resolve_media_in_text()` (`[media:...]` legacy), `MEDIA_PATTERN`.
- `config.py` — điểm duy nhất ghi `user_config.json` (media_fields, presets, lang, welcome_shown, window_maximized). Writes atomic qua file `.tmp` + `os.replace`. Preset/history **phải** qua API ở đây, không tự ghi file trong UI.
- `i18n.py` — `_t(key, **kwargs)`; locale nạp từ `locales/{vi,en}.json`.
- `prompt.py` — sinh XML prompt cho AI.
- `hold.py` — **legacy**, không được import; đừng sửa.

## Meta keys (pop trước khi gán field)

- `__guid__` — tìm note cũ bằng `select id from notes where guid = ?`; nhánh UPDATE nếu trúng.
- `__match_field__` fallback (Smart Sync): build cache `{field_value: note_id}` từ `SELECT id, flds FROM notes WHERE mid = ?`, parse theo delimiter `\x1f`. **Thứ tự: `__guid__` trước, match_field sau** — không đảo.
- `__deck__` — deck đích mỗi card; `__notetype__` — note type mỗi card; `__tags__` — string hoặc list.
- Mọi key `__x__` khác trong JSON đều bị pop/bỏ qua.

## Bất biến bắt buộc khi sửa

1. Mọi field note ghi qua `_note_field_str()` (ép string; None → "").
2. Chỉ gán key tồn tại trong note (`if key in note`); key lạ → skip + warning. Không ghi bừa key JSON vào note.
3. Giữ `mw.checkpoint(...)` + `mw.progress.start/update/finish` + `mw.reset()` trong mọi batch.
4. Truy cập dữ liệu chỉ qua `mw.col` (models/decks/db/note APIs), không bypass.
5. Media output chỉ dùng tag Anki chuẩn: `<img src="...">` hoặc `[sound:...]`.
6. Nút Sinh GUID / Add Deck into JSON: **chỉ thêm cho object thiếu key**, không ghi đè `__guid__`/`__deck__` đã có.
7. Sau batch, nếu bật Write GUID: backfill `__guid__` vào object JSON cả nhánh CREATE lẫn UPDATE.
8. History ghi file JSON riêng vào `history/` (qua `save_batch_history`), không nhồi vào `user_config.json`.

## i18n

- Mọi text hiển thị dùng `_t(key, ...)`, không hardcode.
- Mỗi key mới phải thêm vào **cả** `locales/vi.json` và `locales/en.json`.
- Hỗ trợ format kwargs: `_t("msg", name="Anki")`.

## Build addon

```
python build_addon.py
```

Tạo `JSON_Bulk_Importer_AnkiVN_<timestamp>.ankiaddon` ở repo root. `build_addon.py` liệt kê trắng đen file (exclude `user_config.json`, `history/`, `hold.py`, `.gitignore`, build script). Nếu thêm module/folder mới, cập nhật `INCLUDE_FILES`/`INCLUDE_DIRS`.

## Git

- Commit theo convention có sẵn: `feat:`, `fix:`, `refactor:`, `revert:`, `fix(ui):`, `chore:`, `docs:`.
- `user_config.json` và một số file `history/*` đã được track (từ trước); file mới trong `history/` thường không commit.
- `AI_AGENT_CONTEXT.md` bị gitignore nhưng vẫn được đóng gói vào `.ankiaddon` qua `build_addon.py`.

## Tài liệu tham khảo

- `docs/PROJECT_BLUEPRINT.md` — kiến trúc, luồng, JSON mẫu (có thể hơi cũ, đối chiếu code).
- `AI_AGENT_CONTEXT.md` — context + guidelines cũ của agent.
- Chỉ `from aqt.qt import ...` (Anki bundle Qt), không `pip install PyQt`.
