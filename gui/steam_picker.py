import customtkinter as ctk
from utils.steam_parser import get_installed_steam_games

class SteamPickerWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Выбор игры из Steam")
        self.geometry("400x500")
        self.resizable(False, False)
        self.callback = callback

        self.grab_set()

        lbl = ctk.CTkLabel(self, text="Выберите установленную игру:", font=ctk.CTkFont(size=16, weight="bold"))
        lbl.pack(pady=10)

        self.scroll = ctk.CTkScrollableFrame(self, height=380)
        self.scroll.pack(padx=10, pady=5, fill="both", expand=True)

        self.load_games()

    def load_games(self):
        games = get_installed_steam_games()
        if not games:
            lbl_empty = ctk.CTkLabel(self, text="Игры Steam не найдены.", text_color="gray")
            lbl_empty.pack(pady=20)
            return

        for game in games:
            btn = ctk.CTkButton(
                self.scroll, 
                text=f"🎮 {game['display_name']}\n({game['exe']})", 
                anchor="w",
                fg_color="#2f3640",
                hover_color="#353b48",
                command=lambda g=game: self.select_game(g)
            )
            btn.pack(fill="x", pady=4, padx=5)

    def select_game(self, game):
        self.callback(game['display_name'], game['exe'])
        self.destroy()