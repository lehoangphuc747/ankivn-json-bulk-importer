from typing import Any, List, Tuple, Optional

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


def create_new_model(name: str, sample_card: dict) -> Optional[NotetypeDict]:
    if not mw or not mw.col:
        showInfo(_t("core_open_collection"))
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
        "text-align: center; color: black; background-color: white; }"
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
) -> Tuple[int, int, List[str]]:
    """Tạo mới hoặc cập nhật thẻ dựa trên __guid__ hoặc Smart Sync (match_field).

    Returns:
        (created_count, updated_count, warnings)
    """
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
        model = create_new_model(note_type_name, cards[0])
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

    mw.checkpoint("Bulk Card Creator")
    mw.progress.start(label=_t("core_processing"), immediate=True)

    try:
        total = len(cards)
        for i, card in enumerate(cards):
            mw.progress.update(
                label=_t("core_processing_card", current=i + 1, total=total)
            )

            card_data = dict(card)

            guid = card_data.pop("__guid__", None)
            target_deck = card_data.pop("__deck__", None)
            tags = card_data.pop("__tags__", [])
            if isinstance(tags, str):
                tags = [tags]

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
        mw.progress.finish()

    mw.reset()
    return created, updated, warnings
