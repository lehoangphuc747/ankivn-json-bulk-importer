from typing import List
from .i18n import _t

def generate_ai_prompt(field_names: List[str], media_map: dict) -> str:
    if not field_names:
        field_names = ["Front", "Back"]

    fields_str = ", ".join(f'"{f}"' for f in field_names)
    example_obj = ", ".join(f'"{f}": "..."' for f in field_names)

    media_notes: List[str] = []
    for f in field_names:
        ft = media_map.get(f, "text")
        if ft == "image":
            media_notes.append(
                _t("prompt_image_field", field=f)
            )
        elif ft == "audio":
            media_notes.append(
                _t("prompt_audio_field", field=f)
            )

    media_rules = "\n".join(
        f"    <rule>{note}</rule>" for note in media_notes
    )
    if not media_rules:
        media_rules = f"    <rule>{_t('prompt_no_media_rules')}</rule>"

    prompt = (
        "<flashcard_json_prompt>\n"
        f"  <role>{_t('prompt_expert')}</role>\n"
        "  <input>\n"
        f"    <quantity>{_t('prompt_quantity_placeholder')}</quantity>\n"
        f"    <topic>{_t('prompt_topic_placeholder')}</topic>\n"
        "  </input>\n"
        "  <output_format>\n"
        "    <type>json_array</type>\n"
        f"    <fields>{fields_str}</fields>\n"
        f"    <contract>{_t('prompt_format', fields=fields_str)}</contract>\n"
        "  </output_format>\n"
        "  <rules>\n"
        f"{media_rules}\n"
        "  </rules>\n"
        "  <example><![CDATA[\n"
        f"[{{{example_obj}}}]\n"
        "  ]]></example>\n"
        f"  <final_instruction>{_t('prompt_json_only')}</final_instruction>\n"
        "</flashcard_json_prompt>"
    )
    return prompt
