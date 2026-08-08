# AGENTS.md — JSON Bulk Importer (Anki addon)

Anki addon thuần Python (không webview/React). Chạy **trong Anki**, không có test runner, lint hay typecheck. Mọi xác minh đều phải qua Anki thật: cài addon → restart Anki → menu `AnkiVN` → mở dialog → import thử JSON.

## Vị trí & workflow

- **Repo (dev):** `D:\Vibe Coding\Anki Addons\ankivn-json-bulk-importer` — ngoài `addons21`, chỉ là nơi phát triển.
- **Remote:** `https://github.com/lehoangphuc747/ankivn-json-bulk-importer.git` (origin).
- **Bản cài đang chạy trong Anki:** `C:\Users\ADMIN\AppData\Roaming\Anki2\addons21\json_bulk_importer` — giải nén từ `.ankiaddon` (có `__init__.py` ở root). **Không sửa code trực tiếp ở đây**; sửa ở repo rồi build + cài lại.
- Flow: sửa code trong `src/` → `uvx aadt build -d local` → Anki: Tools → Add-ons → Install from file → chọn `dist/*.ankiaddon` → restart Anki.
- Anki nhận diện addon bằng `__init__.py` ở root thư mục addon; repo theo layout `src/` nên **không được** để trực tiếp trong `addons21`.

## Kiến trúc (cấu trúc `src/` theo AADT)

Toàn bộ source nằm trong `src/json_bulk_importer/` (package module_name trong `addon.json`). Các đường dẫn dưới đây là tương đối với package đó.

- `__init__.py` — entry point: đăng ký menu `AnkiVN` (objectName `sf_ankivn_menu`, dùng chung với SuperFreeTTS) + `show_dialog()` lazy import `gui/main_dialog.py`.
- `gui/*` — chỉ điều phối/validate input và gọi core; **không** để logic DB/media trong dialog.
- `core.py` — logic Anki DB: `create_cards_logic()`, `create_new_model()`, `export_deck_to_json_logic()`.
- `media.py` — `smart_download_media()`, `resolve_media_in_text()` (`[media:...]` legacy), `MEDIA_PATTERN`.
- `config.py` — điểm duy nhất ghi `user_config.json` (media_fields, presets, lang, welcome_shown, window_maximized). Writes atomic qua file `.tmp` + `os.replace`. Preset/history **phải** qua API ở đây, không tự ghi file trong UI.
- `i18n.py` — `_t(key, **kwargs)`; locale nạp từ `locales/{vi,en}.json`.
- `prompt.py` — sinh XML prompt cho AI.
- `hold.py` — **legacy**, nằm ở repo root ngoài `src/` (không đóng gói), không được import; đừng sửa.

## Dữ liệu runtime

- `user_config.json` + `history/` nằm ở **repo root**, ngoài `src/` → tự động bị loại khỏi package khi build.
- Trong bản cài Anki (`addons21\json_bulk_importer\`), chúng được tạo ở ngay thư mục addon (`os.path.dirname(__file__)` trong `config.py`).
- Khi cài bản mới, folder addon được tạo mới (dữ liệu trống) → nếu muốn giữ presets/history, copy `user_config.json` + `history/` từ bản cài cũ sang bản mới.

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

## Build bằng aadt (Anki Addon Dev ToolKit)

Build tool là `aadt`, chạy qua `uvx` (uv đã cài). Cấu hình ở `addon.json` (schema của aadt: `display_name`, `module_name`, `repo_name`, `ankiweb_id`, `author`, `conflicts`, `targets`, `min_anki_version`, `tested_anki_version`).

```powershell
# Build local dev package (giữ debug info) → dist/
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
uvx aadt build -d local

# Build đủ local + ankiweb
uvx aadt build -d all
```

- **Bắt buộc có git tag** (`vX.Y.Z`) — aadt lấy version từ `git describe --tags`; nếu repo có git nhưng chưa có tag, fallback của aadt v1.7.0 bị lỗi. Đặt tag trước khi build: `git tag v0.1.0 && git push --tags`.
- Output vào `dist/<repo_name>-<version>...ankiaddon` (bị gitignore). Cài qua Anki: Tools → Add-ons → Install from file. Anki sẽ giải nén thành folder `json_bulk_importer` trong `addons21`.
- `manifest.json` do aadt sinh từ `addon.json` (thay `meta.json` cũ — đã bỏ). Version point: `min_anki_version`/`tested_anki_version` dạng SemVer.
- `aadt` tự loại khỏi package: `user_config.json`, `history/` (vì ngoài `src/`), `hold.py`, `.git`, `dist/`, `build/`.
- Muốn đổi version: tạo tag mới (không sửa trong build).

### Các lệnh aadt hữu ích

| Lệnh | Công dụng |
|---|---|
| `uvx aadt build -d local\|ankiweb\|all` | Build package (phiên bản mặc định từ tag) |
| `uvx aadt build v1.2.0 -d all` | Build đúng tag/version |
| `uvx aadt manifest` | Chỉ sinh `manifest.json` |
| `uvx aadt clean` | Xóa `dist/` + cache |
| `uvx aadt link` / `aadt link --unlink` | Symlink `src/<module>` vào thư mục addons21 (dev loop) |
| `uvx aadt test` | Link + mở Anki để test |
| `uvx aadt ui` | Compile Qt Designer `.ui` (dự án chưa dùng, `ui/` đang trống) |
| `uvx aadt claude` | Sinh `CLAUDE.md`, `ANKI.md`, `ankidoc/` (AI dev docs) |

Lưu ý: trên Windows, đặt `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` trước khi chạy aadt để tránh lỗi `charmap` encoding với ký tự emoji.

## Git

- Commit theo convention có sẵn: `feat:`, `fix:`, `refactor:`, `revert:`, `fix(ui):`, `chore:`, `docs:`.
- `user_config.json` và một số file `history/*` đã được track (từ trước); file mới trong `history/` thường không commit.
- `AI_AGENT_CONTEXT.md` bị gitignore nhưng vẫn được đóng gói (giờ do aadt copy cả repo, không phải build_addon.py).
- **Version = git tag.** Tạo tag `vX.Y.Z` khi release.

## Tài liệu tham khảo

- `docs/PROJECT_BLUEPRINT.md` — kiến trúc, luồng, JSON mẫu (có thể hơi cũ, đối chiếu code).
- `ANKI.md` + `ankidoc/` — tài liệu Anki core 25.06+ do `aadt claude` sinh.
- `CLAUDE.md` — guideline AI dev của aadt.
- `AI_AGENT_CONTEXT.md` — context + guidelines cũ của agent.
- Chỉ `from aqt.qt import ...` (Anki bundle Qt), không `pip install PyQt`.
