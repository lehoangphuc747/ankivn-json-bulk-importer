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
- `gui/*` — chỉ điều phối/validate input và gọi core; **không** để logic DB/media trong dialog. Gồm: `main_dialog.py` (dialog chính + sidebar), `config_dialog.py` (media fields), `stats_dialog.py` (chọn stat kèm khi Lấy Deck), `table_dialog.py` (xem/sửa JSON dạng bảng), `search_dialog.py`, `help_dialog.py`, `theme.py`, `resources.py`.
- `core.py` — logic Anki DB: `create_cards_logic()`, `create_new_model()`, `export_deck_to_json_logic()`. `create_cards_logic()` trả `(created, updated, unchanged, warnings)`: nhánh UPDATE chỉ đếm `updated` khi có thay đổi thực (field, tags, deck); nếu khớp mà không đổi gì → `unchanged`. Có `convert_markdown` flag (mặc định False): chuyển field text có dấu hiệu Markdown sang HTML qua `_convert_markdown_if_needed()` (lazy import `markdown`, strip `<p>` nếu chỉ 1 đoạn); bỏ qua field media riêng (`[sound:`, `[media:`, `<img`) và field thuần HTML. Chạy SAU bước media mapping + match lookup (match dùng text gốc).
- `media.py` — `smart_download_media()`, `resolve_media_in_text()` (`[media:...]` legacy), `MEDIA_PATTERN`.
- `config.py` — điểm duy nhất ghi `user_config.json` (media_fields, presets, lang, window_maximized, window_geometry, convert_markdown). Writes atomic qua file `.tmp` + `os.replace`. Preset/history **phải** qua API ở đây, không tự ghi file trong UI.
- `i18n.py` — `_t(key, **kwargs)`; locale nạp từ `locales/{vi,en}.json`.
- `prompt.py` — sinh XML prompt cho AI; `generate_ai_prompt()` nhận role/topic tùy chọn (lấp `<role>`, topic chỉ xuất hiện dưới dạng `<topic>` block khi có giá trị); nếu role bỏ trống dùng placeholder i18n.
- `gui/prompt_dialog.py` — dialog nhập role + chủ đề (tùy chọn) trước khi copy prompt (`_on_copy_prompt` mở dialog → OK mới copy).
- `gui/toggle.py` — `ToggleSwitch` (QAbstractButton vẽ bằng paintEvent, kiểu iOS track xanh `#2196F3` + nút tròn trượt) dùng cho toggle Markdown trong sidebar.
- `hold.py` — **legacy**, nằm ở repo root ngoài `src/` (không đóng gói), không được import; đừng sửa.

## Dữ liệu runtime

- `config.py` ưu tiên lưu runtime data vào **profile folder của Anki** (`mw.pm.profileFolder()/json_bulk_importer_data/`) để **không bị mất khi cài bản addon mới** (Anki thay cả folder addon khi cài `.ankiaddon`). Fallback về `os.path.dirname(__file__)` nếu `mw.pm` chưa sẵn (chạy ngoài Anki).
- `_migrate_from_legacy()` tự động copy `user_config.json` + `history/` từ vị trí cũ (cạnh module) sang data dir mới nếu file mới chưa tồn tại. Lưu ý: bản cài đã có data trong folder addon từ trước bản này **không** được migrate tự động khi update (folder cũ đã bị Anki xóa trước khi code chạy) — cần copy thủ công trước khi cài.
- `user_config.json` + `history/` ở **repo root** là bản track từ thời layout phẳng (trước khi migrate sang `src/`), **không phải** nơi code hiện tại ghi; không tạo thêm file runtime trong `src/`.
- Vì runtime data nằm ngoài `src/`, khi build (`aadt` copy `src/<module>`) data **không lọt vào package**.

## Meta keys (pop trước khi gán field)

- `__guid__` — tìm note cũ bằng `select id from notes where guid = ?`; nhánh UPDATE nếu trúng.
- `__match_field__` fallback (Smart Sync): build cache `{field_value: note_id}` từ `SELECT id, flds FROM notes WHERE mid = ?`, parse theo delimiter `\x1f`. **Thứ tự: `__guid__` trước, match_field sau** — không đảo.
- `__deck__` — deck đích mỗi card; `__notetype__` — note type mỗi card; `__tags__` — string hoặc list.
- Ô nhập tags + nút "Thêm Tags vào JSON" nằm ở **sidebar chính** (dưới hàng nút Lấy Deck/Kèm thống kê, không phải trong advanced). Tags phân tách bằng dấu phẩy hoặc khoảng trắng, autocomplete từ `mw.col.tags.all()`. Bấm nút → thêm `__tags__` (list) vào object JSON **chưa có** `__tags__`; không ghi đè tags đã có.
- Gõ tags vào ô nhập sẽ **tự động cập nhật** `__tags__` trong JSON qua `_on_tags_auto_apply()` **chỉ khi key `__tags__` đã tồn tại** trên object; không thêm mới key vào object đang thiếu.
- Đổi deck trong combo sẽ tự cập nhật `__deck__` trong JSON **chỉ khi key `__deck__` đã tồn tại** trên object (template mẫu); không thêm mới key vào object đang thiếu.
- Template JSON sinh khi chọn Note Type điền sẵn `__notetype__`, `__deck__`, `__tags__`, `__guid__` (mục đích là template mẫu).
- `_apply_meta_from_json()` (main_dialog, gọi sau khi Import JSON từ file) đọc `__notetype__`/`__deck__` từ object đầu tiên → **tự chọn** combo bên trái (thêm item vào combo nếu chưa có), dùng `blockSignals` để KHÔNG trigger `_on_note_type_changed`/`_on_deck_changed` (tránh ghi đè JSON).
- Mọi key `__x__` khác trong JSON đều bị pop/bỏ qua.

## Bất biến bắt buộc khi sửa

1. Mọi field note ghi qua `_note_field_str()` (ép string; None → "").
2. Chỉ gán key tồn tại trong note (`if key in note`); key lạ → skip + warning. Không ghi bừa key JSON vào note.
3. Giữ `mw.checkpoint(...)` + `mw.progress.start/update/finish` + `mw.reset()` trong mọi batch.
4. Truy cập dữ liệu chỉ qua `mw.col` (models/decks/db/note APIs), không bypass.
5. Media output chỉ dùng tag Anki chuẩn: `<img src="...">` hoặc `[sound:...]`.
6. Nút Sinh GUID / Add Deck into JSON / Thêm Tags vào JSON: **chỉ thêm cho object thiếu key**, không ghi đè `__guid__`/`__deck__`/`__tags__` đã có. Auto-apply khi gõ tags/đổi deck cũng **không** tạo key mới, chỉ cập nhật key đã tồn tại.
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

- **Quy trình build có tên version (bắt buộc):** trước khi build, commit xong → **tạo git tag mới** tại HEAD rồi build từ tag đó, để tên file ra đúng `dist/ankivn-json-bulk-importer-vX.Y.Z.ankiaddon`:
  ```
  git tag vX.Y.Z
  uvx aadt build -d local
  ```
  Không dùng `aadt build current` hay `aadt build dev` — chúng ra tên file theo commit hash (`...-8385db2.ankiaddon`) hoặc lỗi; aadt chỉ lấy version từ tag.
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
- `AI_AGENT_CONTEXT.md` bị gitignore và **không** được đóng gói (aadt chỉ copy `src/<module>`; file ngoài `src/` không vào package).
- **Version = git tag.** Tạo tag `vX.Y.Z` khi release.

## Tài liệu tham khảo

- `docs/PROJECT_BLUEPRINT.md` — kiến trúc, luồng, JSON mẫu (có thể hơi cũ, đối chiếu code).
- `ANKI.md` + `ankidoc/` — tài liệu Anki core 25.06+ do `aadt claude` sinh.
- `CLAUDE.md` — guideline AI dev của aadt. **Cẩn thận:** nó nhắc `uv sync --group dev`, `uv ruff check`, `uv ty check`, pytest và `.venv` — repo này **không có** dev group, `.venv`, `tests/`; `pyproject.toml` chỉ khai báo package. Không chạy những lệnh đó.
- `AI_AGENT_CONTEXT.md` — context + guidelines cũ của agent.
- Chỉ `from aqt.qt import ...` (Anki bundle Qt), không `pip install PyQt`.
