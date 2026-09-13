import os
import json
import datetime

DATA_FILE = "games_config.json"

def get_today_str():
    return str(datetime.date.today())

class StorageManager:
    def __init__(self, data_file=DATA_FILE):
        self.data_file = data_file

    def load_data(self):
        today = get_today_str()
        default_structure = {
            "date": today,
            "games": {},
            "sites": {}  # Структура: {"youtube.com": {"limit_minutes": 30, "seconds_used": 0, "blocked": False}}
        }

        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    if "sites" not in data:
                        data["sites"] = {}

                    # Сброс дневных лимитов при смене даты
                    if data.get("date") != today:
                        data["date"] = today
                        for game in data.get("games", {}).values():
                            game["seconds_used"] = 0
                            game["notified_5m"] = False
                            game["notified_1m"] = False
                        for site in data.get("sites", {}).values():
                            site["seconds_used"] = 0
                            site["blocked"] = False
                            
                    return data
            except Exception:
                pass
        return default_structure

    def save_data(self, games_data):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(games_data, f, ensure_ascii=False, indent=2)