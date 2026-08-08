from typing import List, Optional
from .i18n import _t

def generate_ai_prompt(
    field_names: List[str],
    media_map: dict,
    role: Optional[str] = None,
    topic: Optional[str] = None,
) -> str:
    if not field_names:
        field_names = ["Front", "Back"]

    fields_str = ", ".join(f'"{f}"' for f in field_names)
    example_obj = ", ".join(f'"{f}": "..."' for f in field_names)

    role_text = role.strip() if role else _t("prompt_expert")
    if topic:
        role_text = role_text.replace("[TOPIC]", topic).replace("[CHỦ_ĐỀ]", topic)

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

    topic_block = ""
    if topic:
        topic_block = (
            "  <topic>\n"
            f"    {topic}\n"
            "  </topic>\n"
        )

    prompt = (
        "<flashcard_json_prompt>\n"
        "  <role>\n"
        f"    {role_text}\n"
        "  </role>\n"
        f"{topic_block}"
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
