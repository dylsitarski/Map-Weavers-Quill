"""Deterministic provider-neutral room style inheritance and prompt assembly."""

import json

from quill.models import MapStyle, Room

STYLE_KEYS = ("environment", "renderStyle", "palette")


def room_style_prompt(room: Room, style: MapStyle) -> tuple[str, dict[str, str]]:
    unknown = set(room.styleOverrides) - set(STYLE_KEYS)
    if unknown:
        raise ValueError("Unsupported room style overrides: " + ", ".join(sorted(unknown)))
    effective = {}
    for key in STYLE_KEYS:
        value = room.styleOverrides.get(key, "").strip() or str(getattr(style, key))
        if len(value) > 512:
            raise ValueError("Each room style value supports at most 512 characters.")
        effective[key] = value
    prompt = (
        f"Room description: {room.prompt}\n"
        "Style: "
        + json.dumps(effective, sort_keys=True, ensure_ascii=False)
        + f"\nCamera: {style.camera}. Baked lighting: {style.bakedLighting}."
    )
    return prompt, effective
