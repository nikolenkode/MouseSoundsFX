"""
Цветовая математика: валидация hex, смешение, осветление, HSV-конвертация.

Перенесено из оригинального main.py без изменений в логике — это тот же
код, что считал цвета для Canvas, просто теперь его результат уходит не
в itemconfig(fill=...), а в JSON, который читает CSS через переменные.
"""

import colorsys


def is_valid_hex(s):
    if not isinstance(s, str) or len(s) != 7 or not s.startswith("#"):
        return False
    try:
        int(s[1:], 16)
        return True
    except ValueError:
        return False


def blend(hex_a, hex_b, t):
    a, b = hex_a.lstrip("#"), hex_b.lstrip("#")
    ar, ag, ab = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
    br, bg, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    r = int(ar + (br - ar) * t)
    g = int(ag + (bg - ag) * t)
    bl = int(ab + (bb - ab) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


def lighten(hex_color, amount):
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_hsv(hex_color):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return colorsys.rgb_to_hsv(r, g, b)


def hsv_to_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


# Свой акцентный цвет ограничен этим диапазоном насыщенности/яркости,
# чтобы нельзя было выбрать "ядовитый" неоновый цвет.
ACCENT_SAT_RANGE = (0.20, 0.65)
ACCENT_VAL_RANGE = (0.45, 0.80)


def clamp_accent_hsv(h, s, v):
    """Не даёт выбрать 'ядовитый' неоновый цвет — зажимает насыщенность
    и яркость в приятный диапазон, оставляя весь диапазон оттенков."""
    s = max(ACCENT_SAT_RANGE[0], min(ACCENT_SAT_RANGE[1], s))
    v = max(ACCENT_VAL_RANGE[0], min(ACCENT_VAL_RANGE[1], v))
    return h, s, v
