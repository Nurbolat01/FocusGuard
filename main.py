import sys
import os
import atexit

from core.storage import StorageManager
from core.process_monitor import ProcessMonitor
from core.web_proxy import LocalProxyServer
from gui.main_window import MainWindow
from utils.sys_proxy import disable_system_proxy

def main():
    # Гарантируем отключение прокси при любом завершении приложения
    atexit.register(disable_system_proxy)

    storage = StorageManager()
    app_data = storage.load_data()

    monitor = ProcessMonitor(storage)
    
    app = MainWindow(storage, monitor)

    # Запускаем локальный прокси для контроля сайтов
    web_proxy = LocalProxyServer(
        app_data=app.games_data,
        storage=storage,
        on_tick_callback=lambda: app.after(0, app.sites_frame.update_list_ui)
    )
    web_proxy.start()

    try:
        app.mainloop()
    finally:
        web_proxy.stop()
        disable_system_proxy()

if __name__ == "__main__":
    main()