"""
Api — единственная точка входа для фронтенда (web/app.js вызывает её
методы через window.pywebview.api.*). Здесь и только здесь живёт вся
логика приложения: состояние конфигурации, звук, глобальный слушатель
мыши, вычисление производных цветов темы, валидация имён кастомных
звуков и т.д. HTML/CSS/JS ничего не решают — они только показывают то,
что вернул Python, и передают сюда события пользователя.

Соглашение об ответах: каждый метод, меняющий состояние, возвращает
словарь с ключом "state" — это полный снимок приложения (см. get_state).
Фронтенд после любого вызова просто перерисовывает себя из state,
никакого локального состояния он не хранит. Методы, которые могут не
получиться (плохой hex, занятое имя звука), дополнительно кладут "ok"
и, если нужно, "reason".
"""

import os
import queue
import shutil
import threading
import uuid

import pygame
import webview
from pynput import mouse

from .colors import (
    clamp_accent_hsv,
    hex_to_hsv,
    hsv_to_hex,
    is_valid_hex,
    lighten,
    blend,
    ACCENT_SAT_RANGE,
    ACCENT_VAL_RANGE,
)
from .config import load_config, save_config
from .constants import (
    BUILTIN_PACK_IDS,
    BUTTONS,
    BUTTON_SHORT,
    BUTTON_TITLES,
    BG_PRESETS,
    DEFAULT_ACCENT,
    DEFAULT_BG,
    PACK_LABELS,
    PATTERN_LABELS,
    RESERVED_SOUND_NAMES,
    THEME_PRESETS,
)
from .paths import CUSTOM_DIR, SOUNDS_DIR
from .sound_library import SoundLibrary

# В разных версиях pywebview тип диалога называется по-разному:
# современный API — webview.FileDialog.OPEN (enum), старый —
# webview.OPEN_DIALOG (числовая константа, помечена устаревшей, но пока
# ещё встречается). Пробуем современный вариант, откатываемся на старый,
# если этой версии pywebview он ещё не завезли.
try:
    _OPEN_DIALOG = webview.FileDialog.OPEN
except AttributeError:
    _OPEN_DIALOG = webview.OPEN_DIALOG


class Api:
    def __init__(self):
        # audio ----------------------------------------------------------
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.sound_library = SoundLibrary(SOUNDS_DIR, CUSTOM_DIR)

        # persisted config -------------------------------------------------
        self.config = load_config()
        self.theme_accent = self.config.get("accent", DEFAULT_ACCENT)
        self.app_bg = self.config.get("background", DEFAULT_BG)
        self._recompute_shades()

        # runtime-only state ------------------------------------------------
        self.current_button = "left"
        self.status_message = ""
        self.picker_target = "accent"
        self.picker_hue, self.picker_sat, self.picker_val = hex_to_hsv(self.theme_accent)
        self._pending_custom_path = None

        # attached by main.py once the pywebview window exists, so we can
        # open native file dialogs from here
        self.window = None

        self._reload_all_sounds()

        # Клики обрабатываются в отдельном потоке, НЕ в самом хуке -----------
        # см. подробный разбор у _on_click ниже.
        self._click_queue = queue.Queue()
        self._click_worker = threading.Thread(target=self._click_worker_loop, daemon=True)
        self._click_worker.start()

        # global mouse listener --------------------------------------------
        self.listener = None
        try:
            self.listener = mouse.Listener(on_click=self._on_click)
            self.listener.start()
        except Exception as e:
            self.status_message = f"Не удалось запустить отслеживание кликов: {e}"

    # ============================ СОСТОЯНИЕ ============================
    def get_state(self):
        return {
            "master": self.config.get("master", True),
            "volume": self.config.get("volume", 0.8),
            "release_sound": self.config.get("release_sound", False),
            "bg_pattern": self.config.get("bg_pattern", "none"),
            "current_button": self.current_button,
            "status": self.status_message,
            "colors": {
                "accent": self.theme_accent,
                "background": self.app_bg,
                "body": self.body_hex,
                "outline": self.outline_hex,
                "pattern": self.pattern_hex,
                "stage": self.stage_hex,
                "stage_outline": self.stage_outline_hex,
                "stage_pattern": self.stage_pattern_hex,
            },
            "buttons": {
                name: {
                    "title": BUTTON_TITLES[name],
                    "short": BUTTON_SHORT[name],
                    "enabled": self.config["assignments"][name]["enabled"],
                    "sound_kind": self.config["assignments"][name]["kind"],
                    "sound_id": self.config["assignments"][name]["id"],
                    "sound_label": self._label_for(self.config["assignments"][name]),
                }
                for name in BUTTONS
            },
            "sound_catalog": {
                "builtin": [{"id": pid, "label": PACK_LABELS[pid]} for pid in BUILTIN_PACK_IDS],
                "custom": list(self.config["custom_sounds"].keys()),
            },
            "theme_presets": [{"name": n, "hex": h} for n, h in THEME_PRESETS.items()],
            "bg_presets": [{"name": n, "hex": h} for n, h in BG_PRESETS.items()],
            "pattern_options": [{"id": pid, "label": lbl} for pid, lbl in PATTERN_LABELS.items()],
            "theme_target": self.picker_target,
            "accent_range": {"sat": list(ACCENT_SAT_RANGE), "val": list(ACCENT_VAL_RANGE)},
            "picker": {"hue": self.picker_hue, "sat": self.picker_sat, "val": self.picker_val},
        }

    def _label_for(self, assignment):
        if assignment["kind"] == "builtin":
            return PACK_LABELS.get(assignment["id"], PACK_LABELS["soft"])
        if assignment["id"] in self.config["custom_sounds"]:
            return assignment["id"]
        return PACK_LABELS["soft"]

    def _recompute_shades(self):
        self.body_hex = lighten(self.app_bg, 0.06)
        self.outline_hex = lighten(self.app_bg, 0.16)
        # Раньше приглушённость узора целиком держалась на том, что этот
        # цвет был еле отличим от фона. Теперь основную работу по
        # "сделать его тонким" делает CSS-прозрачность (opacity слоя в
        # style.css), а тут можно спокойно взять более чёткий, узнаваемый
        # цвет линий — он и через полупрозрачность будет смотреться как
        # лёгкая текстура, а не как случайный шум почти цвета фона.
        self.pattern_hex = lighten(self.app_bg, 0.22)
        base_tinted = lighten(self.app_bg, 0.05)
        self.stage_hex = blend(base_tinted, self.theme_accent, 0.10)
        self.stage_outline_hex = blend(self.outline_hex, self.theme_accent, 0.35)
        self.stage_pattern_hex = blend(self.outline_hex, self.theme_accent, 0.55)

    # ===================== ГЛАВНЫЙ ВЫКЛЮЧАТЕЛЬ / ГРОМКОСТЬ =====================
    def toggle_master(self):
        self.config["master"] = not self.config.get("master", True)
        save_config(self.config)
        return {"state": self.get_state()}

    def set_volume(self, value):
        try:
            value = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            value = self.config.get("volume", 0.8)
        self.config["volume"] = value
        save_config(self.config)
        return {"state": self.get_state()}

    def toggle_release_sound(self):
        self.config["release_sound"] = not self.config.get("release_sound", False)
        save_config(self.config)
        return {"state": self.get_state()}

    # ============================ КНОПКИ МЫШИ ============================
    def select_button(self, name):
        if name in BUTTONS:
            self.current_button = name
        return {"state": self.get_state()}

    def set_button_enabled(self, enabled):
        self.config["assignments"][self.current_button]["enabled"] = bool(enabled)
        save_config(self.config)
        return {"state": self.get_state()}

    # ============================ ВЫБОР ЗВУКА ============================
    def select_sound(self, kind, sound_id):
        if kind == "builtin" and sound_id not in BUILTIN_PACK_IDS:
            return {"ok": False, "state": self.get_state()}
        if kind == "custom" and sound_id not in self.config["custom_sounds"]:
            return {"ok": False, "state": self.get_state()}

        enabled = self.config["assignments"][self.current_button]["enabled"]
        self.config["assignments"][self.current_button] = {"kind": kind, "id": sound_id, "enabled": enabled}
        save_config(self.config)
        ok = self._reload_button_sound(self.current_button)
        self._preview(self.current_button)
        return {"ok": ok, "state": self.get_state()}

    def preview_sound(self):
        self._preview(self.current_button)
        return {"state": self.get_state()}

    def _preview(self, button):
        self.sound_library.play(button, "down", self.config.get("volume", 0.8))

    def _reload_all_sounds(self):
        failed = self.sound_library.reload_all(self.config["assignments"], self.config["custom_sounds"])
        self.status_message = (
            "Не найдены звуки: " + ", ".join(BUTTON_SHORT[b] for b in failed) if failed else ""
        )

    def _reload_button_sound(self, button):
        ok = self.sound_library.reload_button(
            button, self.config["assignments"][button], self.config["custom_sounds"]
        )
        self.status_message = f"Ошибка звука ({BUTTON_SHORT[button]}): файл не найден" if not ok else ""
        return ok

    # ======================= ДОБАВЛЕНИЕ СВОЕГО ЗВУКА =======================
    def pick_custom_sound_file(self):
        """Открывает нативный диалог выбора файла и сразу проигрывает
        выбранный звук для предпрослушивания — как и в оригинале, файл
        ещё НИКУДА не копируется, это происходит только после того, как
        пользователь подтвердит имя в confirm_custom_sound_name."""
        if self.window is None:
            return {"ok": False}
        try:
            result = self.window.create_file_dialog(
                _OPEN_DIALOG,
                file_types=("Аудио файлы (*.wav;*.ogg)", "Все файлы (*.*)"),
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}

        if not result:
            return {"ok": False}
        path = result[0]

        try:
            SoundLibrary.play_file(path, self.config.get("volume", 0.8))
        except Exception as e:
            return {"ok": False, "error": str(e)}

        self._pending_custom_path = path
        suggested = os.path.splitext(os.path.basename(path))[0]
        return {"ok": True, "path": path, "suggested_name": suggested}

    def cancel_custom_sound(self):
        self._pending_custom_path = None
        return {"ok": True}

    def confirm_custom_sound_name(self, name, overwrite=False):
        path = self._pending_custom_path
        if not path:
            return {"ok": False, "reason": "no_pending_file"}

        name = (name or "").strip()
        if not name:
            return {"ok": False, "reason": "empty"}
        if name in PACK_LABELS.values() or name in RESERVED_SOUND_NAMES:
            return {"ok": False, "reason": "reserved"}
        if name in self.config["custom_sounds"] and not overwrite:
            return {"ok": False, "reason": "exists", "name": name}

        old_filename = self.config["custom_sounds"].get(name)
        safe_filename = f"{uuid.uuid4().hex[:10]}_{os.path.basename(path)}"
        dest_path = os.path.join(CUSTOM_DIR, safe_filename)
        try:
            shutil.copy(path, dest_path)
            if old_filename and old_filename != safe_filename:
                old_path = os.path.join(CUSTOM_DIR, old_filename)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass

            self.config["custom_sounds"][name] = safe_filename
            enabled = self.config["assignments"][self.current_button]["enabled"]
            self.config["assignments"][self.current_button] = {"kind": "custom", "id": name, "enabled": enabled}
            save_config(self.config)

            self._pending_custom_path = None
            self._reload_button_sound(self.current_button)
            self._preview(self.current_button)
            return {"ok": True, "state": self.get_state()}
        except Exception as e:
            return {"ok": False, "reason": "error", "message": str(e)}

    # ============================ ТЕМА / ЦВЕТ ============================
    def open_theme_popover(self):
        """Каждое открытие панели темы сбрасывает выбор на вкладку
        'Акцент', как и в оригинале."""
        return self.set_theme_target("accent")

    def set_theme_target(self, target):
        if target not in ("accent", "background"):
            target = "accent"
        self.picker_target = target
        current = self.theme_accent if target == "accent" else self.app_bg
        self.picker_hue, self.picker_sat, self.picker_val = hex_to_hsv(current)
        return {"state": self.get_state()}

    def pick_hue(self, rel_x):
        rel_x = max(0.0, min(1.0, float(rel_x)))
        self.picker_hue = rel_x
        hexcolor = hsv_to_hex(self.picker_hue, self.picker_sat, self.picker_val)
        self._commit_color(hexcolor)
        return {"state": self.get_state()}

    def pick_sv(self, rel_x, rel_y):
        rel_x = max(0.0, min(1.0, float(rel_x)))
        rel_y = max(0.0, min(1.0, float(rel_y)))
        sat, val = rel_x, 1.0 - rel_y
        if self.picker_target == "accent":
            _, sat, val = clamp_accent_hsv(self.picker_hue, sat, val)
        hexcolor = hsv_to_hex(self.picker_hue, sat, val)
        self._commit_color(hexcolor)
        return {"state": self.get_state()}

    def apply_hex(self, text):
        text = (text or "").strip()
        if not text.startswith("#"):
            text = "#" + text
        if not is_valid_hex(text):
            return {"ok": False, "state": self.get_state()}
        if self.picker_target == "accent":
            h, s, v = clamp_accent_hsv(*hex_to_hsv(text))
            text = hsv_to_hex(h, s, v)
        self._commit_color(text)
        return {"ok": True, "state": self.get_state()}

    def apply_preset(self, hex_value):
        if not is_valid_hex(hex_value):
            return {"ok": False, "state": self.get_state()}
        self._commit_color(hex_value)
        return {"ok": True, "state": self.get_state()}

    def _commit_color(self, hexcolor):
        if self.picker_target == "accent":
            self.theme_accent = hexcolor
            self.config["accent"] = hexcolor
        else:
            self.app_bg = hexcolor
            self.config["background"] = hexcolor
        self._recompute_shades()
        save_config(self.config)
        # Держим состояние пикера в синхроне, чтобы при следующем pick_sv/
        # pick_hue или переключении вкладки не было скачка значения. Хекс
        # хранит только 8 бит на канал, поэтому обратная конвертация в hsv
        # может увести sat/val на десятые доли процента от зажатой границы —
        # поджимаем ещё раз, чтобы инвариант "аксент никогда не ядовитый"
        # не нарушался даже на такую мелочь.
        h, s, v = hex_to_hsv(hexcolor)
        if self.picker_target == "accent":
            h, s, v = clamp_accent_hsv(h, s, v)
        self.picker_hue, self.picker_sat, self.picker_val = h, s, v

    def set_bg_pattern(self, pattern_id):
        if pattern_id not in PATTERN_LABELS:
            return {"ok": False, "state": self.get_state()}
        self.config["bg_pattern"] = pattern_id
        save_config(self.config)
        return {"ok": True, "state": self.get_state()}

    # ============================ ОКНО (без рамки) ============================
    def minimize_window(self):
        if self.window:
            self.window.minimize()

    def close_window(self):
        if self.window:
            self.window.destroy()

    # ======================== СЛУШАТЕЛЬ МЫШИ / ВЫХОД ========================
    def _on_click(self, x, y, button, pressed):
        """Это САМ системный хук (WH_MOUSE_LL на Windows) — Windows зовёт
        его синхронно на КАЖДЫЙ клик МЫШИ ВО ВСЕЙ системе и ждёт, пока он
        вернётся, прежде чем пропустить клик дальше. Если тут задержаться
        (даже на обращение к self.config или вызов pygame) — можно
        поймать конкуренцию за GIL с потоком, где крутится WebView2, а
        в худшем случае и настоящий взаимный дедлок: тогда зависает не
        только это окно, а курсор мыши во всей Windows. Поэтому здесь —
        ТОЛЬКО положить событие в очередь и сразу вернуться; вся
        реальная логика — в _click_worker_loop, в отдельном потоке."""
        self._click_queue.put((button, pressed))

    def _click_worker_loop(self):
        while True:
            button, pressed = self._click_queue.get()
            try:
                self._handle_click(button, pressed)
            except Exception:
                pass

    def _handle_click(self, button, pressed):
        if not self.config.get("master", True):
            return
        if not pressed and not self.config.get("release_sound", False):
            return

        name = {
            mouse.Button.left: "left",
            mouse.Button.right: "right",
            mouse.Button.middle: "middle",
        }.get(button)

        if not name or not self.config["assignments"][name]["enabled"]:
            return

        self.sound_library.play(name, "down" if pressed else "up", self.config.get("volume", 0.8))

    def shutdown(self):
        save_config(self.config)
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
        try:
            pygame.mixer.quit()
        except Exception:
            pass
