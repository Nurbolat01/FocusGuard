import socket
import threading
import time
from utils.sys_proxy import enable_system_proxy, disable_system_proxy

class LocalProxyServer:
    def __init__(self, host="127.0.0.1", port=8888, app_data=None, storage=None, on_tick_callback=None):
        self.host = host
        self.port = port
        self.app_data = app_data
        self.storage = storage
        self.on_tick_callback = on_tick_callback
        
        self.server_socket = None
        self.is_running = False
        self.last_active_domain = None
        self.last_activity_time = 0

    def start(self):
        """Запуск локального прокси-сервера"""
        self.is_running = True
        enable_system_proxy(self.host, self.port)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)

        # Фоновый поток приема соединений
        threading.Thread(target=self._accept_loop, daemon=True).start()
        # Фоновый поток таймера обратного отсчета
        threading.Thread(target=self._timer_loop, daemon=True).start()

    def stop(self):
        """Остановка прокси и разблокировка сети"""
        self.is_running = False
        disable_system_proxy()
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

    def _accept_loop(self):
        while self.is_running:
            try:
                client_sock, _ = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, client_sock):
        try:
            client_sock.settimeout(3.0)
            request = client_sock.recv(4096)
            if not request:
                client_sock.close()
                return

            first_line = request.split(b"\n")[0].decode("utf-8", errors="ignore")
            parts = first_line.split(" ")
            
            if len(parts) < 2:
                client_sock.close()
                return

            method, target = parts[0], parts[1]

            # Извлекаем домен
            domain = ""
            if target.startswith("http://") or target.startswith("https://"):
                domain = target.split("//")[1].split("/")[0].split(":")[0]
            elif ":" in target:
                domain = target.split(":")[0]
            else:
                domain = target.split("/")[0]

            domain = domain.lower()

            # Проверяем домен по нашему списку
            matched_site_key = self._find_matching_site(domain)

            if matched_site_key:
                site_info = self.app_data["sites"][matched_site_key]

                # Если лимит исчерпан или заблокирован сразу -> МГНОВЕННЫЙ БЛОК
                if site_info.get("blocked", False) or site_info.get("seconds_used", 0) >= site_info.get("limit_minutes", 0) * 60:
                    # Разрываем соединение мгновенно
                    client_sock.close()
                    return

                # Фиксируем активность пользователя на этом сайте
                self.last_active_domain = matched_site_key
                self.last_activity_time = time.time()

            # Пропускаем обычный HTTPS CONNECT
            if method == "CONNECT":
                host, port = target.split(":") if ":" in target else (target, 443)
                remote_sock = socket.create_connection((host, int(port)), timeout=3.0)
                client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                self._tunnel(client_sock, remote_sock)
            else:
                client_sock.close()

        except Exception:
            try:
                client_sock.close()
            except Exception:
                pass

    def _find_matching_site(self, domain):
        """Проверяет, входит ли запрашиваемый домен в наш отслеживаемый список"""
        if not self.app_data or "sites" not in self.app_data:
            return None

        for site_key in self.app_data["sites"].keys():
            clean_key = site_key.replace("www.", "").lower()
            if clean_key in domain:
                return site_key
        return None

    def _tunnel(self, client_sock, remote_sock):
        """Туннелирование трафика в двух направлениях"""
        def forward(src, dst):
            try:
                while self.is_running:
                    data = src.recv(8192)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    src.close()
                except Exception:
                    pass
                try:
                    dst.close()
                except Exception:
                    pass

        threading.Thread(target=forward, args=(client_sock, remote_sock), daemon=True).start()
        threading.Thread(target=forward, args=(remote_sock, client_sock), daemon=True).start()

    def _timer_loop(self):
        """Каждую секунду проверяет активные сайты и списывает секунды"""
        while self.is_running:
            time.sleep(1)

            # Если пользователь заходил на сайт в последние 5 секунд — считываем секундную активность
            if self.last_active_domain and (time.time() - self.last_activity_time <= 5):
                site_key = self.last_active_domain
                if site_key in self.app_data.get("sites", {}):
                    site_info = self.app_data["sites"][site_key]
                    limit_sec = site_info.get("limit_minutes", 0) * 60

                    if not site_info.get("blocked", False) and limit_sec > 0:
                        site_info["seconds_used"] += 1

                        if site_info["seconds_used"] >= limit_sec:
                            site_info["blocked"] = True

                        if self.storage:
                            self.storage.save_data(self.app_data)

                        if self.on_tick_callback:
                            self.on_tick_callback()