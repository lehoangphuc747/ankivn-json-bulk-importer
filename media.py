import os
import re
import shutil
import uuid
import urllib.request
from typing import List, Tuple, Optional


CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/svg+xml": ".svg", "image/bmp": ".bmp",
    "audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/ogg": ".ogg",
    "audio/flac": ".flac", "audio/mp4": ".m4a", "audio/aac": ".aac",
}

MEDIA_PATTERN = re.compile(r'\[media:(.*?)\]')
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp'}
AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}


def smart_download_media(
    source: str, media_type: str, media_dir: str,
) -> Tuple[str, Optional[str]]:
    """Tải/copy media vào collection.media.

    Returns:
        (anki_tag, error_or_None)
    """
    source = source.strip()
    if not source or "<img" in source or "[sound:" in source:
        return source, None

    try:
        ext = os.path.splitext(source)[1].lower()

        if source.startswith(("http://", "https://")):
            unique_base = f"bulk_{uuid.uuid4().hex[:8]}"
            req = urllib.request.Request(source, headers={
                "User-Agent": "Mozilla/5.0 Anki BulkCardCreator"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                ct = resp.headers.get("Content-Type", "").split(";")[0].strip()
                data = resp.read()

            if not (ext and ext in (IMAGE_EXTS | AUDIO_EXTS)):
                ext = CONTENT_TYPE_EXT.get(
                    ct, ".mp3" if media_type == "audio" else ".jpg"
                )
            unique_name = unique_base + ext
            dest = os.path.join(media_dir, unique_name)
            with open(dest, "wb") as f:
                f.write(data)

        elif os.path.isfile(source):
            if not ext:
                ext = ".mp3" if media_type == "audio" else ".png"
            unique_name = f"bulk_{uuid.uuid4().hex[:8]}{ext}"
            dest = os.path.join(media_dir, unique_name)
            shutil.copy2(source, dest)

        else:
            return source, f"Not found: {source}"

        if media_type == "audio":
            return f"[sound:{unique_name}]", None
        return f'<img src="{unique_name}">', None

    except Exception as e:
        return source, str(e)


def resolve_media_in_text(
    text: str, media_dir: str, warnings: List[str], card_idx: int,
) -> str:
    """Tìm [media:URL_or_PATH], tải/copy vào collection.media, thay bằng tag Anki."""

    def _replace(m: re.Match) -> str:
        source = m.group(1).strip()
        ext = os.path.splitext(source)[1].lower()
        if not ext:
            ext = ".png"
        unique_name = f"bulk_{uuid.uuid4().hex[:8]}{ext}"
        dest = os.path.join(media_dir, unique_name)
        try:
            if source.startswith(("http://", "https://")):
                urllib.request.urlretrieve(source, dest)
            elif os.path.isfile(source):
                shutil.copy2(source, dest)
            else:
                warnings.append(
                    f"Card #{card_idx+1}: media not found: {source}"
                )
                return m.group(0)
        except Exception as e:
            warnings.append(
                f"Card #{card_idx+1}: media error ({source}): {e}"
            )
            return m.group(0)
        if ext in AUDIO_EXTS:
            return f"[sound:{unique_name}]"
        return f'<img src="{unique_name}">'

    return MEDIA_PATTERN.sub(_replace, text)
