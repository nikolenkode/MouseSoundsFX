"""
Загрузка и кэширование звуков — встроенных паков и добавленных
пользователем файлов. Без изменений в логике относительно оригинала.
"""

import os

import pygame

from .constants import BUTTONS


class SoundLibrary:
    """reload_button ВСЕГДА перезаписывает кэш для затронутой кнопки, даже
    в None при ошибке — иначе при сбое остаётся звук от ПРЕДЫДУЩЕГО
    выбора, и клики играют не то, что выбрано."""

    def __init__(self, sounds_dir, custom_dir):
        self.sounds_dir = sounds_dir
        self.custom_dir = custom_dir
        self._cache = {}

    def get(self, button, state):
        return self._cache.get(f"{button}_{state}")

    def play(self, button, state, volume):
        snd = self.get(button, state)
        if snd:
            snd.set_volume(volume)
            snd.play()
        return snd is not None

    def reload_all(self, assignments, custom_sounds):
        failed = []
        for button in BUTTONS:
            if not self.reload_button(button, assignments[button], custom_sounds):
                failed.append(button)
        return failed

    def reload_button(self, button, assignment, custom_sounds):
        down = up = None
        ok = True
        try:
            if assignment["kind"] == "builtin":
                pack_id = assignment["id"]
                down = pygame.mixer.Sound(self._builtin_path(pack_id, button, "down"))
                up = pygame.mixer.Sound(self._builtin_path(pack_id, button, "up"))
            else:
                filename = custom_sounds[assignment["id"]]
                snd = pygame.mixer.Sound(os.path.join(self.custom_dir, filename))
                down = up = snd
        except Exception as e:
            ok = False
            print(f"Не удалось загрузить звук для {button}: {e}")

        self._cache[f"{button}_down"] = down
        self._cache[f"{button}_up"] = up
        return ok

    def _builtin_path(self, pack_id, button, state):
        return os.path.join(self.sounds_dir, pack_id, f"{button}_{state}.wav")

    @staticmethod
    def play_file(path, volume):
        snd = pygame.mixer.Sound(path)
        snd.set_volume(volume)
        snd.play()
        return snd
