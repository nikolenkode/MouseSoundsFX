"""
Предметно-прикладные константы: кнопки мыши, звуковые паки, пресеты темы,
дефолтный конфиг. Всё, что раньше валидировало config.json и определяло
поведение приложения — здесь, без изменений в логике.

Чисто визуальные подписи интерфейса (текст кнопки "Добавить свой звук",
заголовки разделов и т.п.) сознательно НЕ хранятся тут — это уже разметка
web/index.html. Здесь остаётся только то, что влияет на поведение и
валидацию.
"""

BUILTIN_PACK_IDS = ["soft", "sharp", "deep"]
PACK_LABELS = {"soft": "Мягкий", "sharp": "Резкий", "deep": "Глубокий"}

# Эти два текста дублируют подписи, которые фронтенд показывает для пункта
# "добавить свой звук" и разделителя в выпадающем списке. Само отображение
# живёт в web/, а тут — только правило валидации: пользователь не должен
# суметь назвать свой звук так, чтобы он был неотличим от служебного пункта.
RESERVED_SOUND_NAMES = {"➕ Добавить свой...", "─── Свои звуки ───"}

THEME_PRESETS = {
    "Индиго": "#5b6fce",
    "Малахит": "#3d9970",
    "Аметист": "#9568b0",
    "Ежевика": "#b8567a",
    "Терракота": "#cc7a52",
    "Бирюза": "#3f9baa",
}
DEFAULT_ACCENT = THEME_PRESETS["Индиго"]

BG_PRESETS = {
    "Графит": "#151517",
    "Чёрная": "#0b0b0c",
    "Синяя ночь": "#0e1320",
    "Тёплая": "#181410",
    "Изумруд": "#0c1613",
}
DEFAULT_BG = BG_PRESETS["Графит"]

PATTERN_LABELS = {
    "none": "Нет",
    "honeycomb": "Соты",
    "waves": "Волны",
    "diamond": "Ромб",
    "dots": "Точки",
    "grid": "Сетка",
    "stripes": "Полосы",
}
DEFAULT_PATTERN = "none"

BUTTONS = ["left", "right", "middle"]
BUTTON_TITLES = {"left": "Левая кнопка", "right": "Правая кнопка", "middle": "Колесо"}
BUTTON_SHORT = {"left": "ЛКМ", "right": "ПКМ", "middle": "Колесо"}

DEFAULT_CONFIG = {
    "master": True,
    "volume": 0.8,
    "accent": DEFAULT_ACCENT,
    "background": DEFAULT_BG,
    "bg_pattern": DEFAULT_PATTERN,
    "release_sound": False,
    "assignments": {
        "left": {"kind": "builtin", "id": "soft", "enabled": True},
        "right": {"kind": "builtin", "id": "soft", "enabled": True},
        "middle": {"kind": "builtin", "id": "soft", "enabled": True},
    },
    "custom_sounds": {},
}
