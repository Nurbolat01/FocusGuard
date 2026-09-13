import os
import sys
import threading
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

from gui.steam_picker import SteamPickerWindow
from gui.sites_page import SitesPageFrame

class MainWindow(ctk.CTk):
    def __init__(self, storage_manager, monitor):
        super().__init__()

        self.storage = storage_manager
        self.monitor = monitor
        self.games_data = self.storage.load_data()

        self.selected_exe = None
        self.tray_icon = None

        self.title("Focus Guard PC")
        self.geometry("620x650")
        self.resizable(False, False)

        icon_path = os.path.abspath(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        elif os.path.exists("icon.ico"):
            self.iconbitmap("icon.ico")

        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.setup_ui()

        # Обратный вызов обновления UI при изменении данных
        self.monitor.on_state_changed = lambda: self.after(0, self.update_games_list_ui)
        self.monitor.start(self.games_data)

    def setup_ui(self):
        # Шапка
        self.header_label = ctk.CTkLabel(
            self, 
            text="🛡️ Focus Guard PC", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.header_label.pack(pady=(10, 5))

        # Переключатель вкладок (Игры / Сайты)
        self.tabview = ctk.CTkTabview(self, width=580, height=550)
        self.tabview.pack(padx=10, pady=5, fill="both", expand=True)

        self.tab_games = self.tabview.add("🎮 Игры и Программы")
        self.tab_sites = self.tabview.add("🌐 Сайты")

        # --- ВКЛАДКА ИГР ---
        self.setup_games_tab()

        # --- ВКЛАДКА САЙТОВ ---
        self.sites_frame = SitesPageFrame(self.tab_sites, self.storage, self.games_data)
        self.sites_frame.pack(fill="both", expand=True)

    def setup_games_tab(self):
        # Панель добавления игр
        self.add_frame = ctk.CTkFrame(self.tab_games)
        self.add_frame.pack(padx=10, pady=10, fill="x")

        self.steam_btn = ctk.CTkButton(
            self.add_frame,
            text="🎮 Выбрать из Steam",
            fg_color="#1e3799",
            hover_color="#0c2461",
            command=self.open_steam_picker
        )
        self.steam_btn.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

        self.proc_entry = ctk.CTkEntry(
            self.add_frame, 
            placeholder_text="Название игры или .exe", 
            width=220
        )
        self.proc_entry.grid(row=1, column=0, padx=10, pady=10)

        self.time_entry = ctk.CTkEntry(
            self.add_frame, 
            placeholder_text="Мин. (напр. 60)", 
            width=100
        )
        self.time_entry.grid(row=1, column=1, padx=5, pady=10)

        self.add_btn = ctk.CTkButton(
            self.add_frame, 
            text="Добавить", 
            width=100, 
            command=self.add_game
        )
        self.add_btn.grid(row=1, column=2, padx=10, pady=10)

        # Список игр
        self.scroll_frame = ctk.CTkScrollableFrame(self.tab_games, height=330)
        self.scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.update_games_list_ui()

    def open_steam_picker(self):
        SteamPickerWindow(self, self.on_steam_game_selected)

    def on_steam_game_selected(self, display_name, exe_name):
        self.selected_exe = exe_name
        self.proc_entry.delete(0, "end")
        self.proc_entry.insert(0, display_name)

    def add_game(self):
        display_input = self.proc_entry.get().strip()
        limit_str = self.time_entry.get().strip()

        if not display_input or not limit_str.isdigit():
            return

        limit_minutes = int(limit_str)
        
        if self.selected_exe:
            proc_name = self.selected_exe
            display_name = display_input
        else:
            proc_name = display_input.lower()
            if not proc_name.endswith(".exe"):
                proc_name += ".exe"
            display_name = display_input

        self.games_data["games"][proc_name] = {
            "display_name": display_name,
            "limit_minutes": limit_minutes,
            "seconds_used": 0,
            "notified_5m": False,
            "notified_1m": False
        }
        
        self.storage.save_data(self.games_data)
        self.selected_exe = None
        self.proc_entry.delete(0, "end")
        self.time_entry.delete(0, "end")
        self.update_games_list_ui()

    def remove_game(self, proc_name):
        if proc_name in self.games_data["games"]:
            del self.games_data["games"][proc_name]
            self.storage.save_data(self.games_data)
            self.update_games_list_ui()

    def update_games_list_ui(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        games = self.games_data.get("games", {})
        if not games:
            empty_lbl = ctk.CTkLabel(
                self.scroll_frame, 
                text="Список пуст. Выберите игру из Steam выше.", 
                text_color="gray"
            )
            empty_lbl.pack(pady=20)
            return

        for proc_name, info in games.items():
            card = ctk.CTkFrame(self.scroll_frame)
            card.pack(fill="x", pady=5, padx=5)

            display_title = info.get("display_name", proc_name)
            limit_sec = info["limit_minutes"] * 60
            used_sec = info["seconds_used"]
            left_sec = max(0, limit_sec - used_sec)
            
            left_min = left_sec // 60
            left_s = left_sec % 60

            status_color = "#2ed573" if left_sec > 0 else "#ff4757"
            status_text = f"{left_min}м {left_s}с / {info['limit_minutes']}м"

            lbl_title = ctk.CTkLabel(
                card, 
                text=f"{display_title}\n({proc_name})", 
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
                justify="left"
            )
            lbl_title.pack(side="left", padx=10, pady=10)

            lbl_status = ctk.CTkLabel(
                card, 
                text=status_text, 
                text_color=status_color,
                font=ctk.CTkFont(weight="bold")
            )
            lbl_status.pack(side="left", padx=15, pady=10)

            del_btn = ctk.CTkButton(
                card, 
                text="❌", 
                width=30, 
                fg_color="#ff4757", 
                hover_color="#ff6b81",
                command=lambda p=proc_name: self.remove_game(p)
            )
            del_btn.pack(side="right", padx=10, pady=10)

    # --- ТРЕЙ ---
    def create_tray_image(self):
        icon_path = os.path.abspath(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        elif os.path.exists("icon.ico"):
            return Image.open("icon.ico")
        
        image = Image.new('RGB', (64, 64), color=(30, 144, 255))
        d = ImageDraw.Draw(image)
        d.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
        return image

    def hide_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            menu = pystray.Menu(
                pystray.MenuItem("Открыть Focus Guard", self.show_from_tray),
                pystray.MenuItem("Выход", self.quit_app)
            )
            self.tray_icon = pystray.Icon("FocusGuard", self.create_tray_image(), "Focus Guard PC", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.deiconify()

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.monitor.stop()
        self.destroy()
        sys.exit()