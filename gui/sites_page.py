import customtkinter as ctk
from core.web_blocker import WebBlocker

class SitesPageFrame(ctk.CTkFrame):
    def __init__(self, parent, storage_manager, app_data):
        super().__init__(parent, fg_color="transparent")
        self.storage = storage_manager
        self.app_data = app_data
        self.web_blocker = WebBlocker()

        self.setup_ui()

    def setup_ui(self):
        lbl = ctk.CTkLabel(self, text="🌐 Контроль и блокировка сайтов", font=ctk.CTkFont(size=18, weight="bold"))
        lbl.pack(pady=(10, 5))

        # Панель добавления
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(padx=10, pady=10, fill="x")

        self.site_entry = ctk.CTkEntry(add_frame, placeholder_text="например: youtube.com", width=220)
        self.site_entry.grid(row=0, column=0, padx=10, pady=10)

        self.time_entry = ctk.CTkEntry(add_frame, placeholder_text="Мин. (0 = сразу)", width=100)
        self.time_entry.grid(row=0, column=1, padx=5, pady=10)

        add_btn = ctk.CTkButton(add_frame, text="Добавить", width=100, command=self.add_site)
        add_btn.grid(row=0, column=2, padx=10, pady=10)

        # Список заблокированных сайтов
        self.scroll_frame = ctk.CTkScrollableFrame(self, height=320)
        self.scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.update_list_ui()

    def add_site(self):
        site_raw = self.site_entry.get().strip()
        limit_str = self.time_entry.get().strip()

        if not site_raw:
            return

        domain = self.web_blocker._normalize_domain(site_raw)
        limit_minutes = int(limit_str) if limit_str.isdigit() else 0

        self.app_data["sites"][domain] = {
            "limit_minutes": limit_minutes,
            "seconds_used": 0,
            "blocked": limit_minutes == 0  # Если лимит 0 — блокируем сразу
        }

        self.storage.save_data(self.app_data)
        self.sync_hosts()
        
        self.site_entry.delete(0, "end")
        self.time_entry.delete(0, "end")
        self.update_list_ui()

    def remove_site(self, domain):
        if domain in self.app_data["sites"]:
            del self.app_data["sites"][domain]
            self.storage.save_data(self.app_data)
            self.sync_hosts()
            self.update_list_ui()

    def sync_hosts(self):
        """Собирает все сайты с флагом blocked=True и отправляет в hosts"""
        blocked_list = [
            domain for domain, info in self.app_data.get("sites", {}).items()
            if info.get("blocked", False)
        ]
        self.web_blocker.apply_blocklist(blocked_list)

    def update_list_ui(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        sites = self.app_data.get("sites", {})
        if not sites:
            empty_lbl = ctk.CTkLabel(self.scroll_frame, text="Список сайтов пуст.", text_color="gray")
            empty_lbl.pack(pady=20)
            return

        for domain, info in sites.items():
            card = ctk.CTkFrame(self.scroll_frame)
            card.pack(fill="x", pady=5, padx=5)

            is_blocked = info.get("blocked", False)
            status_text = "🚫 ЗАБЛОКИРОВАН" if is_blocked else f"Лимит: {info['limit_minutes']} мин."
            status_color = "#ff4757" if is_blocked else "#2ed573"

            lbl_domain = ctk.CTkLabel(card, text=domain, font=ctk.CTkFont(weight="bold"), anchor="w")
            lbl_domain.pack(side="left", padx=10, pady=10)

            lbl_status = ctk.CTkLabel(card, text=status_text, text_color=status_color, font=ctk.CTkFont(weight="bold"))
            lbl_status.pack(side="left", padx=15, pady=10)

            del_btn = ctk.CTkButton(
                card, text="❌", width=30, fg_color="#ff4757", hover_color="#ff6b81",
                command=lambda d=domain: self.remove_site(d)
            )
            del_btn.pack(side="right", padx=10, pady=10)