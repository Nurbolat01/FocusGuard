import os
import winreg
import subprocess

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
REDIRECT_IP = "127.0.0.1"

# Известные DoH-серверы браузеров для принудительного отката на системный DNS
DOH_SERVERS = [
    "dns.google",
    "cloudflare-dns.com",
    "dns.quad9.net",
    "doh.cleanbrowsing.org",
    "common.dot.dns.yandex.net",
    "dns.adguard-dns.com"
]

class SiteBlocker:
    def __init__(self):
        self.hosts_path = HOSTS_PATH
        self.disable_browser_doh()  # Автоматически отключаем DoH в реестре при инициализации

    def disable_browser_doh(self):
        """Отключает DoH в Chrome, Edge и Brave через системную политику Windows"""
        policies = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Google\Chrome", "DnsOverHttpsMode", "off"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Edge", "DnsOverHttpsMode", "off"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\BraveSoftware\Brave", "DnsOverHttpsMode", "off")
        ]
        
        for root, path, key_name, value in policies:
            try:
                key = winreg.CreateKey(root, path)
                winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, value)
                winreg.CloseKey(key)
            except Exception as e:
                pass  # Требуются права админа

    def _flush_dns(self):
        """Сброс кэша DNS в Windows"""
        try:
            subprocess.run("ipconfig /flushdns", shell=True, capture_output=True, check=False)
        except Exception:
            pass

    def get_domain_variations(self, domain):
        """Возвращает варианты доменного имени"""
        domain = domain.lower().strip()
        for prefix in ["https://", "http://", "www."]:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        
        domain = domain.split('/')[0]

        variations = [domain]
        if not domain.startswith("www."):
            variations.append(f"www.{domain}")
        return variations

    def block_sites(self, domains_list):
        """Заблокировать список сайтов + DoH-серверы"""
        try:
            with open(self.hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            all_targets = set()
            
            # Добавляем целевые сайты
            for d in domains_list:
                for var in self.get_domain_variations(d):
                    all_targets.add(var)

            # Если есть хотя бы один сайт для блокировки — блокируем и DoH-серверы
            if domains_list:
                for doh in DOH_SERVERS:
                    all_targets.add(doh)

            # Очищаем старый блок Focus Guard
            new_lines = [line for line in lines if "# FG_BLOCK" not in line]

            # Записываем новые правила
            for target in all_targets:
                new_lines.append(f"{REDIRECT_IP} {target} # FG_BLOCK\n")

            with open(self.hosts_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            self._flush_dns()
            return True
        except PermissionError:
            print("ОШИБКА: Нужны права администратора!")
            return False
        except Exception as e:
            print(f"Ошибка блокировки: {e}")
            return False

    def unblock_all(self):
        """Снять все блокировки"""
        try:
            with open(self.hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            new_lines = [line for line in lines if "# FG_BLOCK" not in line]

            with open(self.hosts_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            self._flush_dns()
            return True
        except Exception as e:
            print(f"Ошибка разблокировки: {e}")
            return False