import os
import time
import threading
import psutil
from utils.notifier import show_windows_toast

class ProcessMonitor:
    def __init__(self, storage_manager, on_state_changed_callback=None):
        self.storage = storage_manager
        self.on_state_changed = on_state_changed_callback
        self.is_monitoring = False

    def start(self, games_data):
        self.is_monitoring = True
        thread = threading.Thread(target=self._monitor_loop, args=(games_data,), daemon=True)
        thread.start()

    def stop(self):
        self.is_monitoring = False

    def force_kill_process(self, process_name):
        os.system(f'taskkill /F /IM "{process_name}" /T >nul 2>&1')

    def _monitor_loop(self, games_data):
        while self.is_monitoring:
            games = games_data.get("games", {})
            if not games:
                time.sleep(1)
                continue

            running_procs = set()
            for proc in psutil.process_iter(['name']):
                try:
                    p_name = proc.info['name']
                    if p_name:
                        running_procs.add(p_name.lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            state_changed = False

            for proc_name, info in list(games.items()):
                limit_sec = info["limit_minutes"] * 60

                if proc_name in running_procs:
                    if info["seconds_used"] >= limit_sec:
                        self.force_kill_process(proc_name)
                        show_windows_toast(
                            title="⛔ Время вышло!",
                            msg=f"Игровой лимит для '{info.get('display_name', proc_name)}' исчерпан. Игра была закрыта.",
                            sound_type="hand"
                        )
                    else:
                        info["seconds_used"] += 1
                        left_sec = limit_sec - info["seconds_used"]
                        display_title = info.get("display_name", proc_name)

                        # Предупреждение за 5 минут
                        if left_sec == 300 and not info.get("notified_5m", False):
                            info["notified_5m"] = True
                            show_windows_toast(
                                title="⏳ Осталось 5 минут",
                                msg=f"Завершайте раунд в '{display_title}'. До закрытия осталось 5 минут.",
                                sound_type="reminder"
                            )

                        # Предупреждение за 1 минуту
                        if left_sec == 60 and not info.get("notified_1m", False):
                            info["notified_1m"] = True
                            show_windows_toast(
                                title="⚠️ Осталась 1 минута!",
                                msg=f"Внимание! '{display_title}' закроется через 60 секунд. Сохраняйтесь!",
                                sound_type="alarm"
                            )

                        state_changed = True

            if state_changed:
                self.storage.save_data(games_data)
                if self.on_state_changed:
                    self.on_state_changed()

            time.sleep(1)