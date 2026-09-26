"""
Пути и файловая структура приложения.

Логика такая же, как в оригинальном main.py: при запуске из собранного
PyInstaller-exe (``sys.frozen``) ресурсы (звуки, web/) читаются из
временной распакованной директории ``_MEIPASS``, а данные, которые нужно
сохранять между запусками (config.json, добавленные пользователем звуки),
пишутся рядом с самим exe. При запуске из исходников — всё рядом с
проектом.

Единственное отличие от оригинала: раньше main.py лежал в корне проекта,
теперь backend/paths.py лежит на один уровень глубже, поэтому в режиме
"из исходников" до корня проекта поднимаемся на директорию выше.
"""

import os
import sys

if getattr(sys, "frozen", False):
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    DATA_DIR = os.path.dirname(sys.executable)
else:
    _BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = os.path.dirname(_BACKEND_DIR)
    DATA_DIR = RESOURCE_DIR

SOUNDS_DIR = os.path.join(RESOURCE_DIR, "sounds")
CUSTOM_DIR = os.path.join(DATA_DIR, "sounds", "custom")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

WEB_DIR = os.path.join(RESOURCE_DIR, "web")
INDEX_HTML = os.path.join(WEB_DIR, "index.html")

os.makedirs(CUSTOM_DIR, exist_ok=True)
