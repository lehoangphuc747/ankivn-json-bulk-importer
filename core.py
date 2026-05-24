from typing import Any, List, Tuple, Optional, Callable

from aqt import mw
from aqt.utils import showInfo
from anki.models import NotetypeDict

from .i18n import _t
from .media import (
    MEDIA_PATTERN, resolve_media_in_text, smart_download_media,
)


def _note_field_str(value: Any) -> str:
    # Anki chỉ chấp nhận chuỗi cho từng ô; JSON null / số / bool nếu không đổi sẽ gây lỗi kiểu.
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def create_new_model(name: str, sample_card: dict, col: Optional[Any] = None) -> Optional[NotetypeDict]:
    if not col:
        if not mw or not mw.col:
            print(_t("core_open_collection"))
            return None
        col = mw.col

    model = col.models.new(name)

    col.models.addField(model, col.models.new_field("Front"))

    answer_parts: List[str] = []
    for key in sample_card.keys():
        if key.startswith("__") or key.lower() == "front":
            continue
        col.models.addField(model, col.models.new_field(key))
        answer_parts.append("{{" + key + "}}")

    template = col.models.new_template("Card 1")
    template["qfmt"] = "{{Front}}"
    template["afmt"] = (
        "<br>".join(answer_parts) if answer_parts else "{{Front}}"
    )
    model["css"] = (
        ".card { font-family: arial; font-size: 20px; "
        "text-align: center; }"
    )
    col.models.addTemplate(model, template)
    col.models.save(model)
    return model



def create_cards_logic(
    deck_name: str,
    note_type_name: str,
    cards: List[dict],
    match_field: Optional[str] = None,
    media_mappings: Optional[dict] = None,
    on_progress_start: Optional[Callable[[str], None]] = None,
    on_progress_update: Optional[Callable[[str], None]] = None,
    on_progress_finish: Optional[Callable[[], None]] = None,
    col: Optional[Any] = None,
) -> Tuple[int, int, List[str]]:
    """Tạo mới hoặc cập nhật thẻ dựa trên __guid__ hoặc Smart Sync (match_field).

    Returns:
        (created_count, updated_count, warnings)
    """
    if not col:
        if not mw or not mw.col:
            raise RuntimeError(_t("core_collection_not_init"))
        col = mw.col

    deck_id = col.decks.id(deck_name)

    model = col.models.by_name(note_type_name)
    if not model:
        if not cards:
            raise ValueError(
                _t("core_notetype_not_found", name=note_type_name)
            )
        model = create_new_model(note_type_name, cards[0], col=col)
        if not model:
            raise ValueError(
                _t("core_notetype_create_fail", name=note_type_name)
            )

    created = 0
    updated = 0
    warnings: List[str] = []

    # Smart Sync: xây cache {field_value: note_id} để tìm note theo nội dung field
    match_cache: dict = {}
    if match_field and model:
        field_names = [f['name'] for f in model['flds']]
        if match_field in field_names:
            field_idx = field_names.index(match_field)
            rows = col.db.all(
                "SELECT id, flds FROM notes WHERE mid = ?", model['id']
            )
            for row_id, flds_str in rows:
                fields = flds_str.split("\x1f")
                if field_idx < len(fields) and fields[field_idx].strip():
                    match_cache[fields[field_idx].strip()] = row_id

    media_dir = col.media.dir()

    if mw:
        mw.checkpoint("Bulk Card Creator")

    if on_progress_start:
        on_progress_start(_t("core_processing"))
    elif mw and getattr(mw, "progress", None):
        mw.progress.start(label=_t("core_processing"), immediate=True)

    try:
        total = len(cards)
        for i, card in enumerate(cards):
            label = _t("core_processing_card", current=i + 1, total=total)
            if on_progress_update:
                on_progress_update(label)
            elif mw and getattr(mw, "progress", None):
                mw.progress.update(label=label)

            card_data = dict(card)

            guid = card_data.pop("__guid__", None)
            target_deck = card_data.pop("__deck__", None)
            _ = card_data.pop("__notetype__", None)
            tags = card_data.pop("__tags__", [])
            if isinstance(tags, str):
                tags = [tags]

            # Xoá tất cả những field meta khác (có đuôi và đầu là __) để tránh lỗi
            for key in list(card_data.keys()):
                if key.startswith("__") and key.endswith("__"):
                    card_data.pop(key, None)

            for key in list(card_data.keys()):
                val = card_data[key]
                if isinstance(val, str) and MEDIA_PATTERN.search(val):
                    card_data[key] = resolve_media_in_text(
                        val, media_dir, warnings, i
                    )

            if media_mappings:
                for key in list(card_data.keys()):
                    ftype = media_mappings.get(key, "text")
                    if ftype in ("image", "audio"):
                        val = card_data[key]
                        if isinstance(val, str) and val.strip():
                            tag, err = smart_download_media(
                                val, ftype, media_dir
                            )
                            card_data[key] = tag
                            if err:
                                warnings.append(
                                    _t("core_media_error",
                                       index=i + 1, field=key, error=err)
                                )

            existing_note_id = None
            if guid:
                existing_note_id = col.db.scalar(
                    "select id from notes where guid = ?", guid
                )

            if not existing_note_id and match_cache and match_field:
                match_value = _note_field_str(card_data.get(match_field, ""))
                if match_value.strip():
                    existing_note_id = match_cache.get(match_value.strip())

            if existing_note_id:
                note = col.get_note(existing_note_id)

                unknown_keys: List[str] = []
                for key, value in card_data.items():
                    if key in note:
                        note[key] = _note_field_str(value)
                    else:
                        unknown_keys.append(key)

                if unknown_keys:
                    warnings.append(
                        _t("core_skip_unknown_update",
                           index=i + 1, guid=guid, keys=unknown_keys)
                    )

                if tags:
                    for tag in tags:
                        tnorm = _note_field_str(tag)
                        if tnorm and tnorm not in note.tags:
                            note.tags.append(tnorm)

                col.update_note(note)

                if target_deck:
                    new_deck_id = col.decks.id(target_deck)
                    for card_obj in note.cards():
                        if card_obj.did != new_deck_id:
                            card_obj.did = new_deck_id
                            card_obj.flush()

                if note.guid:
                    card["__guid__"] = note.guid

                updated += 1

            else:
                note = col.new_note(model)

                if guid:
                    note.guid = guid

                unknown_keys = []
                for key, value in card_data.items():
                    if key in note:
                        note[key] = _note_field_str(value)
                    else:
                        unknown_keys.append(key)

                if unknown_keys:
                    warnings.append(
                        _t("core_skip_unknown_create",
                           index=i + 1, keys=unknown_keys)
                    )

                if tags:
                    note.tags = [
                        _note_field_str(t) for t in tags if _note_field_str(t)
                    ]

                actual_deck_id = deck_id
                if target_deck:
                    actual_deck_id = col.decks.id(target_deck)

                col.add_note(note, actual_deck_id)
                if note.guid:
                    card["__guid__"] = note.guid
                created += 1

    finally:
        if on_progress_finish:
            on_progress_finish()
        elif mw and getattr(mw, "progress", None):
            mw.progress.finish()

    if mw:
        mw.reset()
    return created, updated, warnings


def export_deck_to_json_logic(deck_name: str, include_stats: bool = False) -> Tuple[List[dict], str]:
    """Xuất tất cả notes trong một deck ra định dạng List[dict] chuẩn của addon."""
    from aqt import mw
    if not mw or not mw.col:
        raise RuntimeError("Anki collection is not open.")

    col = mw.col
    
    # Tìm tất cả ID của các card nằm trong deck được chọn
    query = f'"deck:{deck_name}"'
    card_ids = col.find_cards(query)
    
    exported_notes = {}
    note_type_name = ""
    
    # Chunk card IDs to avoid SQLite query limit
    chunk_size = 900
    model_cache = {}
    deck_name_cache = {}
    
    for i in range(0, len(card_ids), chunk_size):
        chunk = card_ids[i:i + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        # Query cards and notes in a single SQL query
        rows = col.db.all(f"""
            SELECT c.id, c.nid, c.did, c.reps, c.lapses, c.ivl, c.factor,
                   n.guid, n.mid, n.mod, n.tags, n.flds
            FROM cards c
            JOIN notes n ON c.nid = n.id
            WHERE c.id IN ({placeholders})
        """, *chunk)
        
        for row in rows:
            cid, nid, did, reps, lapses, ivl, factor, guid, mid, mod, tags_str, flds_str = row
            if nid in exported_notes:
                continue
                
            if mid not in model_cache:
                model_cache[mid] = col.models.get(mid)
            model = model_cache[mid]
            if not model:
                continue
                
            if not note_type_name:
                note_type_name = model["name"]

            # Lấy tên deck thực tế của card (giữ nguyên vị trí sub-deck)
            if did not in deck_name_cache:
                deck_obj = col.decks.get(did)
                deck_name_cache[did] = deck_obj["name"] if deck_obj else deck_name
            actual_deck_name = deck_name_cache[did]
                
            # Convert space-separated tag string to list, falling back safely
            if hasattr(col.tags, "split"):
                tags = col.tags.split(tags_str)
            else:
                tags = [t for t in tags_str.strip().split(" ") if t]
            
            note_dict = {
                "__guid__": guid,
                "__deck__": actual_deck_name,
                "__notetype__": model["name"],
                "__tags__": tags,
            }
            
            if include_stats:
                ease = factor / 10 if factor else 250
                note_dict.update({
                    "__created_at__": nid,
                    "__modified_at__": mod,
                    "__reps__": reps,
                    "__lapses__": lapses,
                    "__ivl__": ivl,
                    "__ease__": ease,
                })
                
            # Split fields
            field_values = flds_str.split("\x1f")
            field_names = [f["name"] for f in model["flds"]]
            for idx, val in enumerate(field_values):
                if idx < len(field_names):
                    note_dict[field_names[idx]] = val
                    
            exported_notes[nid] = note_dict

    return list(exported_notes.values()), note_type_name


