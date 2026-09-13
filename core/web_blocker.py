import os
import platform

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts" if platform.system() == "Windows" else "/etc/hosts"
REDIRECT_IP = "127.0.0.1"
MARKER_START = "# --- FOCUS GUARD BLOCK START ---"
MARKER_END = "# --- FOCUS GUARD BLOCK END ---"

class WebBlocker:
    def __init__(self, hosts_path=HOSTS_PATH):
        self.hosts_path = hosts_path

    def _normalize_domain(self, site_input):
        """Очищает вводимый URL до чистого домена (например, https://youtube.com/watch -> youtube.com)"""
        site = site_input.strip().lower()
        site = site.replace("https://", "").replace("http://", "").replace("www.", "")
        site = site.split("/")[0]
        return site

    def apply_blocklist(self, blocked_sites):
        """
        Применяет список заблокированных сайтов к файлу hosts.
        blocked_sites: список доменов ['youtube.com', 'vk.com', 'twitch.tv']
        """
        try:
            if not os.path.exists(self.hosts_path):
                return False, "Файл hosts не найден."

            # Читаем текущий hosts
            with open(self.hosts_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Удаляем прошлый блок Focus Guard
            new_lines = []
            in_block = False
            for line in lines:
                if MARKER_START in line:
                    in_block = True
                    continue
                if MARKER_END in line:
                    in_block = False
                    continue
                if not in_block:
                    new_lines.append(line)

            # Если есть сайты для блокировки — добавляем новую секцию
            if blocked_sites:
                if new_lines and not new_lines[-1].endswith("\n"):
                    new_lines.append("\n")
                
                new_lines.append(f"{MARKER_START}\n")
                for site in blocked_sites:
                    domain = self._normalize_domain(site)
                    if domain:
                        new_lines.append(f"{REDIRECT_IP} {domain}\n")
                        new_lines.append(f"{REDIRECT_IP} www.{domain}\n")
                new_lines.append(f"{MARKER_END}\n")

            # Записываем изменения
            with open(self.hosts_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            # Сбрасываем DNS-кэш Windows, чтобы блокировка сработала мгновенно
            if platform.system() == "Windows":
                os.system("ipconfig /flushdns >nul 2>&1")

            return True, "Успешно обновлено."
        except PermissionError:
            return False, "Нет прав администратора для записи в файл hosts."
        except Exception as e:
            return False, f"Ошибка записи: {e}"

    def clear_all_blocks(self):
        """Полностью снимает все блокировки сайтов"""
        return self.apply_blocklist([])