"""
Mouse Sound FX (MSFX) — точка входа.

Вся логика приложения — в backend/ (чистый Python, без единой строчки
разметки). Всё, что пользователь видит, — в web/ (HTML/CSS/JS). Мост
между ними — pywebview: он открывает нативное окно с системным
веб-движком и пробрасывает backend.api.Api как window.pywebview.api,
доступный из app.js.

Запуск: python main.py
Подробный лог (для диагностики): python main.py --debug
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

import webview

from backend.api import Api
from backend.paths import INDEX_HTML

DEBUG = "--debug" in sys.argv or os.environ.get("MSFX_DEBUG") == "1"

WEBVIEW2_URL = "https://developer.microsoft.com/en-us/microsoft-edge/webview2/"

# Официальный GUID компонента WebView2 Runtime — один и тот же во всех
# установках, под ним Evergreen-инсталлятор Microsoft регистрирует себя
# в реестре. Проверяем сразу несколько мест: EdgeUpdate может писать в
# HKCU (непривилегированная установка на одного пользователя) или в
# HKLM/HKLM+WOW6432Node (установка на всех пользователей, 64-битный реестр).
_WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def _fatal_error(title, message):
    """Показывается, только если что-то ломается ДО того, как успело
    открыться окно pywebview (например, звуковое устройство недоступно,
    или не нашёлся нормальный веб-движок) — в этот момент показать ошибку
    внутри ещё не существующего окна невозможно, поэтому используется
    отдельное системное окно."""
    print(f"{title}: {message}")
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass
    sys.exit(1)


def _pythonnet_present():
    try:
        import clr  # noqa: F401
        return True
    except Exception:
        return False


def _webview2_present():
    import winreg

    paths = [
        (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_GUID}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_GUID}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_GUID}"),
    ]
    for hive, path in paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                version, _ = winreg.QueryValueEx(key, "pv")
                if version:
                    return True
        except OSError:
            continue
    return False


def _check_webview2_stack():
    """На Windows проверяем ДО открытия окна, а не полагаемся на то, что
    webview.start() сам пожалуется, если современный движок недоступен —
    у pywebview даже при явно указанном gui есть задокументированное
    поведение тихо откатываться на другой бэкенд, если запрошенный
    недоступен (см. changelog: "Fallback to Winforms when QT is forced,
    but not available" — то же самое подразумевается и для остальных
    бэкендов). Без этой проверки заранее приложение просто открылось бы
    через mshtml (Internet Explorer) без единой ошибки — а он не
    поддерживает ни CSS-переменные (весь вид ломается на
    белый/бесцветный), ни async/await в JS (окно становится
    некликабельным), да и работает заметно медленнее и тяжелее для
    системы на старте, отсюда и подтормаживание мыши в момент запуска."""
    if not sys.platform.startswith("win"):
        return

    if not _pythonnet_present():
        _fatal_error(
            "Не найден пакет pythonnet",
            "Без пакета pythonnet приложение не может воспользоваться "
            "современным движком (WebView2) и работать не будет "
            "нормально.\n\n"
            "Установите его командой:\n"
            '   python -m pip install "pywebview[winforms]" --upgrade --force-reinstall\n\n'
            "После этого запустите программу заново.",
        )

    if not _webview2_present():
        _fatal_error(
            "Не найден WebView2 Runtime",
            "На этом компьютере не найден компонент Windows Microsoft "
            "Edge WebView2 Runtime, без которого интерфейс приложения "
            "не может отобразиться правильно.\n\n"
            "1. Скачайте и установите его отсюда:\n"
            f"   {WEBVIEW2_URL}\n"
            "   (обычно нужен пункт 'Evergreen Bootstrapper')\n\n"
            "2. Если он вроде уже стоит — откройте 'Параметры Windows' -> "
            "'Приложения' -> найдите 'Microsoft Edge WebView2 Runtime' -> "
            "'Изменить' -> 'Восстановить'.\n\n"
            "3. Перезапустите программу после установки.",
        )


def main():
    _check_webview2_stack()

    try:
        api = Api()
    except Exception as e:
        _fatal_error("Ошибка запуска", f"Не удалось запустить Mouse Sound FX:\n{e}")
        return

    # Настройка области, за которую можно таскать безрамочное окно —
    # нужно назначить ДО create_window/start. easy_drag=False здесь не
    # заработал (проверено на реальной машине): перетаскивание за
    # .pywebview-drag-region у pywebview завязано именно на режим
    # easy_drag=True — так и в официальном API-референсе ("To control
    # dragging on an element basis, see drag area"), и в чужом реальном
    # фиксе точно такой же проблемы (коммит так и назывался — "Try to
    # make header moving work": easy_drag=False -> True + явное
    # присвоение DRAG_REGION_SELECTOR — и у них заработало).
    webview.settings["DRAG_REGION_SELECTOR"] = ".pywebview-drag-region"

    window = webview.create_window(
        "Mouse Sound FX",
        INDEX_HTML,
        js_api=api,
        width=760,
        height=630,
        resizable=False,
        background_color=api.app_bg,
        frameless=True,
        easy_drag=True,
        shadow=True,
    )
    # Своя шапка (web/index.html, .logo с классом pywebview-drag-region)
    # отвечает за перетаскивание окна; кнопки "свернуть"/"закрыть" —
    # свои, справа (Api.minimize_window/close_window).
    #
    # Клики по-прежнему идут через очередь (Api._on_click), а не
    # обрабатываются прямо в системном хуке мыши — это чинило реальное
    # зависание курсора мыши насмерть и никак не связано с настройками
    # drag выше; трогать не нужно.
    # Методы Api, открывающие нативный диалог выбора файла, обращаются к
    # окну — привязываем его уже после создания.
    api.window = window
    window.events.closing += api.shutdown

    gui = "edgechromium" if sys.platform.startswith("win") else None
    try:
        webview.start(debug=DEBUG, gui=gui)
    except Exception as e:
        api.shutdown()
        _fatal_error(
            "Не удалось открыть окно",
            f"WebView2 найден в системе, но окно всё равно не открылось.\n\n"
            f"Попробуйте: python main.py --debug — это покажет подробный "
            f"лог и консоль разработчика.\n\n"
            f"Техническая информация: {e}",
        )


if __name__ == "__main__":
    main()
