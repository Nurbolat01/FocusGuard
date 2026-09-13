import os
import glob
import winreg

def get_steam_path():
    """Находит путь к установленной папке Steam через реестр Windows"""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        return path
    except Exception:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam")
            path, _ = winreg.QueryValueEx(key, "InstallPath")
            return path
        except Exception:
            return None

def parse_vdf_simple(file_path):
    """Парсер манифестов Steam vdf"""
    data = {}
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith('"name"'):
                    parts = line.split('"')
                    if len(parts) >= 4:
                        data["name"] = parts[3]
                elif line.startswith('"installdir"'):
                    parts = line.split('"')
                    if len(parts) >= 4:
                        data["installdir"] = parts[3]
    except Exception:
        pass
    return data

def get_installed_steam_games():
    """Сканирует библиотеки Steam и находит установленные игры"""
    steam_path = get_steam_path()
    if not steam_path:
        return []

    library_folders = [steam_path]
    vdf_library_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    
    if os.path.exists(vdf_library_path):
        try:
            with open(vdf_library_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if '"path"' in line:
                        parts = line.split('"')
                        if len(parts) >= 4:
                            folder = parts[3].replace("\\\\", "\\")
                            if os.path.exists(folder) and folder not in library_folders:
                                library_folders.append(folder)
        except Exception:
            pass

    games_found = []

    for lib in library_folders:
        steamapps = os.path.join(lib, "steamapps")
        if not os.path.exists(steamapps):
            continue

        manifests = glob.glob(os.path.join(steamapps, "appmanifest_*.acf"))
        for manifest in manifests:
            vdf_data = parse_vdf_simple(manifest)
            name = vdf_data.get("name")
            installdir = vdf_data.get("installdir")

            if name and installdir:
                game_dir = os.path.join(steamapps, "common", installdir)
                if os.path.exists(game_dir):
                    exe_files = []
                    for root, _, files in os.walk(game_dir):
                        for file in files:
                            if file.lower().endswith(".exe"):
                                if not any(x in file.lower() for x in ["unins", "setup", "crash", "helper", "unity"]):
                                    exe_files.append(file.lower())

                    if exe_files:
                        main_exe = sorted(exe_files, key=len)[0]
                        games_found.append({
                            "display_name": name,
                            "exe": main_exe
                        })

    return sorted(games_found, key=lambda x: x["display_name"])