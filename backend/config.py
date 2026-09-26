"""
Загрузка и сохранение config.json.

Логика 1:1 перенесена из оригинала: любое повреждённое или неизвестное
значение НЕ подменяется тихо на что-то другое — для конкретной настройки
остаётся безопасный дефолт, а не рушится весь конфиг.
"""

import json
import os

from .colors import is_valid_hex
from .constants import BUILTIN_PACK_IDS, BUTTONS, DEFAULT_CONFIG, PATTERN_LABELS
from .paths import CONFIG_PATH


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)

            cfg["master"] = bool(saved.get("master", cfg["master"]))
            cfg["release_sound"] = bool(saved.get("release_sound", cfg["release_sound"]))
            try:
                cfg["volume"] = max(0.0, min(1.0, float(saved.get("volume", cfg["volume"]))))
            except (TypeError, ValueError):
                pass
            if is_valid_hex(saved.get("accent", "")):
                cfg["accent"] = saved["accent"]
            if is_valid_hex(saved.get("background", "")):
                cfg["background"] = saved["background"]
            if saved.get("bg_pattern") in PATTERN_LABELS:
                cfg["bg_pattern"] = saved["bg_pattern"]
            if isinstance(saved.get("custom_sounds"), dict):
                cfg["custom_sounds"] = dict(saved["custom_sounds"])

            saved_assign = saved.get("assignments", {})
            for btn in BUTTONS:
                a = saved_assign.get(btn, {})
                kind, sid = a.get("kind"), a.get("id")
                enabled = bool(a.get("enabled", True))
                if kind == "builtin" and sid in BUILTIN_PACK_IDS:
                    cfg["assignments"][btn] = {"kind": "builtin", "id": sid, "enabled": enabled}
                elif kind == "custom" and sid in cfg["custom_sounds"]:
                    cfg["assignments"][btn] = {"kind": "custom", "id": sid, "enabled": enabled}
        except Exception as e:
            print(f"config.json повреждён, использую значения по умолчанию: {e}")
    return cfg


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Не удалось сохранить config.json: {e}")
