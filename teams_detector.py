"""
Mouse Jiggler Pro — Teams Tespit Sistemi
Microsoft Teams otomatik algilama, pencere yonetimi, browser kontrolu
"""

import ctypes
import os
import subprocess
import threading

from utils import (
    IS_WINDOWS,
    PSUTIL_AVAILABLE, PYAUTOGUI_AVAILABLE,
    psutil, pyautogui,
    get_cursor_pos, set_cursor_pos,
    EnumWindows, EnumWindowsProc, GetWindowTextW, GetWindowTextLengthW, IsWindowVisible,
    POINT, RECT, MONITORINFO,
    MonitorFromWindow, GetMonitorInfoW, EnumDisplayMonitors, GetWindowRect,
    SetForegroundWindow, ShowWindow,
    MONITOR_DEFAULTTONEAREST, SW_RESTORE, SW_SHOW, SW_MINIMIZE,
    logger,
)


class TeamsDetector:
    """Microsoft Teams process ve pencere tespit sınıfı."""

    # Masaüstü Teams process isimleri
    DESKTOP_TEAMS_NAMES = {"ms-teams.exe", "teams.exe", "msteams.exe"}

    # Browser process isimleri ve görüntü adları
    BROWSER_MAP = {
        "chrome.exe": "Chrome",
        "msedge.exe": "Edge",
        "firefox.exe": "Firefox",
    }

    # Teams URL pattern'leri
    TEAMS_URLS = ("teams.microsoft.com", "teams.live.com", "teams.cloud.microsoft")

    def __init__(self):
        # Cache sistemi
        self._cache = {
            "status": None,
            "timestamp": 0,
            "ttl": 10,           # saniye
            "updating": False
        }

    def _run_silent_command(self, command):
        """CMD penceresi açmadan subprocess çalıştır (sadece Windows)"""
        if not IS_WINDOWS:
            return b""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        return subprocess.check_output(
            command,
            startupinfo=startupinfo,
            creationflags=creationflags,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )

    def detect_teams_process(self):
        """Teams process tespiti — pencere başlığı, process ismi, browser penceresi."""
        result = {
            "found": False,
            "type": None,
            "process_name": None,
            "pid": None,
            "browser_name": None,
        }

        # Yöntem 1: Pencere başlığı ile tespit (en güvenilir)
        window_result = self._detect_teams_by_window_title()
        if window_result["found"]:
            return window_result

        # Yöntem 2: Process ismi ile tespit (masaüstü)
        desktop_result = self._detect_desktop_teams()
        if desktop_result["found"]:
            return desktop_result

        # Yöntem 3: Browser pencere başlıklarında Teams arama
        browser_result = self._detect_browser_teams()
        if browser_result["found"]:
            return browser_result

        # Yöntem 4: Browser process var mı? (Teams sekmesi aktif değil olabilir)
        browser_proc_result = self._detect_browser_with_teams()
        if browser_proc_result["found"]:
            return browser_proc_result

        return result

    def _detect_teams_by_window_title(self):
        """Tüm pencerelerin başlıklarında Teams ara — minimize dahil"""
        result = {"found": False, "type": None, "process_name": None, "pid": None, "browser_name": None}

        if not IS_WINDOWS:
            return result

        teams_keywords = [
            "Microsoft Teams",
            "Teams - ",
            "| Microsoft Teams",
            "teams.microsoft.com",
            "teams.cloud.microsoft",
            "teams.live.com",
        ]

        found_windows = []

        def enum_callback(hwnd, lParam):
            # IsWindowVisible KONTROLÜ KALDIRILDI — minimize dahil TÜM pencereler taranır
            try:
                length = GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value

                    for keyword in teams_keywords:
                        if keyword.lower() in title.lower():
                            is_visible = bool(IsWindowVisible(hwnd))
                            found_windows.append({
                                "hwnd": hwnd,
                                "title": title,
                                "visible": is_visible,
                            })
                            break
            except Exception as e:
                logger.info(f"Pencere title okuma hatasi: {e}")
            return True

        try:
            enum_proc = EnumWindowsProc(enum_callback)
            EnumWindows(enum_proc, 0)
        except Exception as e:
            logger.warning(f"EnumWindows hatasi: {e}")

        if found_windows:
            # Öncelik: visible pencereler önce, sonra invisible
            found_windows.sort(key=lambda w: (not w["visible"],))
            window = found_windows[0]
            title = window["title"].lower()

            # Tür belirleme: browser mı masaüstü mü?
            browser_urls = ["teams.microsoft.com", "teams.cloud.microsoft", "teams.live.com"]
            is_browser = any(url in title for url in browser_urls)

            if is_browser:
                result["type"] = "browser"
                result["browser_name"] = self._detect_browser_from_title(window["title"])
            else:
                result["type"] = "desktop"

            result["found"] = True
            result["process_name"] = window["title"][:80]

        return result

    def _detect_desktop_teams(self):
        """Masaüstü Teams uygulamasını process olarak tespit et"""
        result = {"found": False, "type": "desktop", "process_name": None, "pid": None, "browser_name": None}

        teams_process_names = ["ms-teams.exe", "Teams.exe", "msteams.exe", "MSTeams.exe"]

        if PSUTIL_AVAILABLE:
            try:
                for proc in psutil.process_iter(["name", "pid", "status"]):
                    try:
                        pname = proc.info["name"]
                        if pname and pname.lower() in [t.lower() for t in teams_process_names]:
                            result["found"] = True
                            result["process_name"] = pname
                            result["pid"] = proc.info["pid"]
                            return result
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception as e:
                logger.info(f"Desktop Teams tarama hatasi: {e}")
        else:
            # tasklist fallback — CMD açmadan
            for pname in teams_process_names:
                try:
                    output = self._run_silent_command(
                        ["tasklist", "/FI", f"IMAGENAME eq {pname}", "/FO", "CSV", "/NH"]
                    )
                    decoded = output.decode("utf-8", errors="ignore").strip()
                    if pname.lower() in decoded.lower() and "bilgi yok" not in decoded.lower() and "no tasks" not in decoded.lower():
                        result["found"] = True
                        result["process_name"] = pname
                        try:
                            parts = decoded.split(",")
                            if len(parts) >= 2:
                                result["pid"] = int(parts[1].strip('"'))
                        except Exception as e:
                            logger.info(f"PID parse hatasi: {e}")
                        return result
                except Exception as e:
                    logger.info(f"Tasklist tarama hatasi: {e}")
                    continue

        return result

    def _detect_browser_teams(self):
        """Browser'da açık Teams'i pencere başlığından tespit et — minimize dahil"""
        result = {"found": False, "type": "browser", "process_name": None, "pid": None, "browser_name": None}

        if not IS_WINDOWS:
            return result

        browser_teams_patterns = [
            "teams.microsoft.com",
            "teams.cloud.microsoft",
            "teams.live.com",
            "Teams - Microsoft Edge",
            "Teams - Google Chrome",
            "Teams - Mozilla Firefox",
            "Microsoft Teams - ",
        ]

        found_windows = []

        def enum_callback(hwnd, lParam):
            # IsWindowVisible KONTROLÜ KALDIRILDI — minimize dahil
            try:
                length = GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    for pattern in browser_teams_patterns:
                        if pattern.lower() in title.lower():
                            is_visible = bool(IsWindowVisible(hwnd))
                            found_windows.append({
                                "hwnd": hwnd,
                                "title": title,
                                "visible": is_visible,
                            })
                            break
            except Exception as e:
                logger.info(f"Browser pencere okuma hatasi: {e}")
            return True

        try:
            enum_proc = EnumWindowsProc(enum_callback)
            EnumWindows(enum_proc, 0)
        except Exception as e:
            logger.warning(f"EnumWindows hatasi (browser): {e}")

        if found_windows:
            # Visible pencereler öncelikli
            found_windows.sort(key=lambda w: (not w["visible"],))
            title = found_windows[0]["title"]
            result["found"] = True
            result["process_name"] = title[:50]
            result["browser_name"] = self._detect_browser_from_title(title)

        return result

    def _detect_browser_from_title(self, title):
        """Pencere başlığından browser ismini belirle"""
        title_lower = title.lower()
        if "edge" in title_lower:
            return "Edge"
        elif "chrome" in title_lower:
            return "Chrome"
        elif "firefox" in title_lower:
            return "Firefox"
        elif "opera" in title_lower:
            return "Opera"
        elif "brave" in title_lower:
            return "Brave"
        return "Browser"

    def _detect_browser_with_teams(self):
        """Browser process'i tespit et — Teams sekmesi aktif olmasa bile"""
        result = {
            "found": False,
            "type": "browser",
            "process_name": None,
            "pid": None,
            "browser_name": None,
            "needs_tab_switch": False,
            "browser_hwnd": None,
        }

        if not IS_WINDOWS:
            return result

        browser_executables = {
            "chrome.exe": "Chrome",
            "msedge.exe": "Edge",
            "firefox.exe": "Firefox",
            "opera.exe": "Opera",
            "brave.exe": "Brave",
        }

        found_browsers = []

        if PSUTIL_AVAILABLE:
            try:
                for proc in psutil.process_iter(["name", "pid", "cmdline"]):
                    try:
                        pname = proc.info["name"]
                        if pname and pname.lower() in browser_executables:
                            cmdline = proc.info.get("cmdline") or []
                            cmdline_str = " ".join(cmdline).lower()
                            # Command line'da Teams URL var mı?
                            has_teams_url = any(
                                url in cmdline_str
                                for url in ["teams.microsoft.com", "teams.cloud.microsoft", "teams.live.com"]
                            )
                            found_browsers.append({
                                "name": pname,
                                "pid": proc.info["pid"],
                                "browser_name": browser_executables.get(pname.lower(), "Browser"),
                                "has_teams_in_cmdline": has_teams_url,
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception as e:
                logger.info(f"Browser Teams tarama hatasi: {e}")
        else:
            # tasklist fallback
            for exe, name in browser_executables.items():
                try:
                    output = self._run_silent_command(
                        ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"]
                    )
                    decoded = output.decode("utf-8", errors="ignore").strip()
                    if exe.lower() in decoded.lower() and "bilgi yok" not in decoded.lower() and "no tasks" not in decoded.lower():
                        found_browsers.append({
                            "name": exe,
                            "pid": None,
                            "browser_name": name,
                            "has_teams_in_cmdline": False,
                        })
                except Exception as e:
                    logger.info(f"Tasklist browser tarama hatasi: {e}")
                    continue

        if found_browsers:
            # Teams URL'si cmdline'da olan browser'a öncelik ver
            teams_browsers = [b for b in found_browsers if b.get("has_teams_in_cmdline")]
            best = teams_browsers[0] if teams_browsers else found_browsers[0]

            # Browser'ın window handle'ını bul
            browser_hwnd = self._find_browser_window(best["browser_name"])

            result["found"] = True
            result["process_name"] = best["name"]
            result["pid"] = best["pid"]
            result["browser_name"] = best["browser_name"]
            result["needs_tab_switch"] = True  # Teams sekmesi aktif değil
            result["browser_hwnd"] = browser_hwnd

        return result

    def _find_browser_window(self, browser_name):
        """Belirtilen browser'ın ana pencere handle'ını bul"""
        if not IS_WINDOWS:
            return None

        browser_titles = {
            "Chrome": "Google Chrome",
            "Edge": "Microsoft Edge",
            "Firefox": "Mozilla Firefox",
            "Opera": "Opera",
            "Brave": "Brave",
        }

        search_title = browser_titles.get(browser_name, browser_name)
        found_hwnd = None

        def enum_callback(hwnd, lParam):
            nonlocal found_hwnd
            try:
                length = GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if search_title.lower() in title.lower():
                        found_hwnd = hwnd
                        return False  # İlk eşleşmede dur
            except Exception as e:
                logger.info(f"Browser pencere arama hatasi: {e}")
            return True

        try:
            enum_proc = EnumWindowsProc(enum_callback)
            EnumWindows(enum_proc, 0)
        except Exception as e:
            logger.warning(f"EnumWindows hatasi (browser window): {e}")

        return found_hwnd

    def bring_teams_to_front(self):
        """Teams penceresini veya Teams açık olan browser'ı öne getir"""
        if not IS_WINDOWS:
            return {"success": False, "action": "not_windows"}

        # 1. Önce Teams window'u dene
        window_info = self.detect_teams_window()
        if window_info.get("found") and window_info.get("hwnd"):
            hwnd = window_info["hwnd"]
            try:
                ShowWindow(hwnd, SW_RESTORE)
                SetForegroundWindow(hwnd)
                return {"success": True, "action": "teams_focused"}
            except Exception as e:
                logger.warning(f"Teams pencere one getirme hatasi: {e}")

        # 2. Teams bulunamadıysa browser'ı öne getir
        browser_info = self._detect_browser_with_teams()
        if browser_info.get("found") and browser_info.get("browser_hwnd"):
            hwnd = browser_info["browser_hwnd"]
            try:
                ShowWindow(hwnd, SW_RESTORE)
                SetForegroundWindow(hwnd)
                return {
                    "success": True,
                    "action": "browser_focused",
                    "browser_name": browser_info.get("browser_name"),
                    "needs_tab_switch": True,
                }
            except Exception as e:
                logger.warning(f"Browser pencere one getirme hatasi: {e}")

        # 3. Desktop Teams process var ama pencere bulunamıyor
        desktop_info = self._detect_desktop_teams()
        if desktop_info.get("found"):
            return {"success": False, "action": "teams_in_tray", "message": "Teams sistem tepsisinde olabilir"}

        return {"success": False, "action": "not_found", "message": "Teams bulunamadı"}

    def detect_teams_window(self):
        """Teams penceresini bul (minimize dahil)."""
        result = {
            "found": False,
            "hwnd": None,
            "title": None,
        }

        if not IS_WINDOWS:
            return result

        teams_patterns = [
            "Microsoft Teams",
            "Teams - ",
            "| Microsoft Teams",
            "teams.microsoft.com",
            "teams.cloud.microsoft",
            "teams.live.com",
        ]

        found_windows = []

        def enum_callback(hwnd, lParam):
            # IsWindowVisible KONTROLÜ YOK — minimize dahil tüm pencereler
            try:
                length = GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    for pattern in teams_patterns:
                        if pattern.lower() in title.lower():
                            is_visible = bool(IsWindowVisible(hwnd))
                            found_windows.append({
                                "hwnd": hwnd,
                                "title": title,
                                "visible": is_visible,
                            })
                            break
            except Exception as e:
                logger.info(f"Pencere numaralandirma hatasi: {e}")
            return True

        try:
            enum_proc = EnumWindowsProc(enum_callback)
            EnumWindows(enum_proc, 0)
        except Exception as e:
            logger.warning(f"EnumWindows hatasi (detect): {e}")

        if found_windows:
            # Visible olanları öncelikle al
            found_windows.sort(key=lambda w: (not w["visible"],))
            # "Microsoft Teams" başlığı öncelikli
            best = found_windows[0]
            for w in found_windows:
                if "microsoft teams" in w["title"].lower():
                    best = w
                    break

            result["found"] = True
            result["hwnd"] = best["hwnd"]
            result["title"] = best["title"]

        return result

    def get_teams_status(self):
        """Birleşik Teams durum bilgisi."""
        process_info = self.detect_teams_process()
        window_info = self.detect_teams_window()

        detected = process_info.get("found", False) or window_info.get("found", False)

        # Tür belirleme — process'ten veya window'dan
        teams_type = process_info.get("type")
        if not teams_type and window_info.get("found"):
            # Pencere başlığından tür tahmin et
            title = (window_info.get("title") or "").lower()
            if any(url in title for url in ["teams.microsoft.com", "teams.cloud.microsoft", "teams.live.com"]):
                teams_type = "browser"
            elif "microsoft teams" in title:
                teams_type = "desktop"
            else:
                teams_type = "desktop"  # Varsayılan

        status = {
            "detected": detected,
            "type": teams_type or "desktop",
            "process_name": process_info.get("process_name"),
            "pid": process_info.get("pid"),
            "browser_name": process_info.get("browser_name"),
            "window_found": window_info.get("found", False),
            "hwnd": window_info.get("hwnd"),
            "window_title": window_info.get("title"),
            "monitor_count": len(self.get_all_monitors()) or 1,
            "teams_monitor": self.get_teams_monitor(),
            "teams_rect": self.get_teams_window_rect(),
            "needs_tab_switch": process_info.get("needs_tab_switch", False),
        }
        logger.debug(f"Teams status: detected={status['detected']}, type={status['type']}, window={status['window_found']}")
        return status

    def get_all_monitors(self):
        """Sistemdeki tüm bağlı monitörleri tespit et."""
        monitors = []

        try:
            def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                """Her monitör için çağrılan callback."""
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                    monitor_data = {
                        "handle": hMonitor,
                        "left": info.rcMonitor.left,
                        "top": info.rcMonitor.top,
                        "right": info.rcMonitor.right,
                        "bottom": info.rcMonitor.bottom,
                        "width": info.rcMonitor.right - info.rcMonitor.left,
                        "height": info.rcMonitor.bottom - info.rcMonitor.top,
                        "is_primary": bool(info.dwFlags & 1),
                        "work_area": {
                            "left": info.rcWork.left,
                            "top": info.rcWork.top,
                            "right": info.rcWork.right,
                            "bottom": info.rcWork.bottom,
                        },
                    }
                    monitors.append(monitor_data)
                return 1  # TRUE — devam et (int döndür)

            # EnumDisplayMonitors callback typedef — 64-bit uyumlu
            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_int,                    # return type
                ctypes.POINTER(ctypes.c_int),    # hMonitor
                ctypes.POINTER(ctypes.c_int),    # hdcMonitor
                ctypes.POINTER(RECT),            # lprcMonitor
                ctypes.c_longlong,               # dwData (LPARAM — 64-bit)
            )
            enum_proc = MONITORENUMPROC(callback)
            EnumDisplayMonitors(None, None, enum_proc, 0)
        except Exception as e:
            logger.warning(f"Monitor bilgisi hatasi: {e}")

        return monitors

    def get_teams_window_rect(self):
        """Teams penceresinin ekrandaki pozisyon ve boyutunu al."""
        result = {
            "found": False,
            "hwnd": None,
            "left": 0, "top": 0, "right": 0, "bottom": 0,
            "width": 0, "height": 0,
            "center_x": 0, "center_y": 0,
        }

        try:
            window_info = self.detect_teams_window()
            if not window_info["found"]:
                return result

            hwnd = window_info["hwnd"]
            rect = RECT()
            if GetWindowRect(hwnd, ctypes.byref(rect)):
                result["found"] = True
                result["hwnd"] = hwnd
                result["left"] = rect.left
                result["top"] = rect.top
                result["right"] = rect.right
                result["bottom"] = rect.bottom
                result["width"] = rect.right - rect.left
                result["height"] = rect.bottom - rect.top
                result["center_x"] = rect.left + (rect.right - rect.left) // 2
                result["center_y"] = rect.top + (rect.bottom - rect.top) // 2
        except Exception as e:
            logger.warning(f"Teams pencere boyutu hatasi: {e}")

        return result

    def get_teams_monitor(self):
        """Teams penceresinin bulunduğu monitörü tespit et."""
        result = {
            "found": False,
            "monitor_handle": None,
            "monitor_bounds": None,
            "is_primary": False,
            "monitor_index": -1,
        }

        try:
            window_rect = self.get_teams_window_rect()
            if not window_rect["found"]:
                return result

            hwnd = window_rect["hwnd"]
            # Teams penceresine en yakın monitörü bul
            hMonitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
            if not hMonitor:
                return result

            # Monitör bilgilerini al
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if not GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                return result

            result["found"] = True
            result["monitor_handle"] = hMonitor
            result["monitor_bounds"] = {
                "left": info.rcMonitor.left,
                "top": info.rcMonitor.top,
                "right": info.rcMonitor.right,
                "bottom": info.rcMonitor.bottom,
            }
            result["is_primary"] = bool(info.dwFlags & 1)

            # Monitör index'ini bul
            all_monitors = self.get_all_monitors()
            for i, mon in enumerate(all_monitors):
                if (mon["left"] == info.rcMonitor.left and
                        mon["top"] == info.rcMonitor.top and
                        mon["right"] == info.rcMonitor.right and
                        mon["bottom"] == info.rcMonitor.bottom):
                    result["monitor_index"] = i
                    break

        except Exception as e:
            logger.warning(f"Teams monitor tespiti hatasi: {e}")

        return result

    def move_cursor_to_teams(self):
        """Mouse imlecini Teams penceresinin merkezine taşı."""
        try:
            rect = self.get_teams_window_rect()
            if not rect["found"]:
                return False

            set_cursor_pos(rect["center_x"], rect["center_y"])
            return True
        except Exception as e:
            logger.warning(f"Cursor Teams'e tasima hatasi: {e}")
            return False

    def is_cursor_on_teams_monitor(self):
        """Mouse imleci Teams'in bulunduğu monitörde mi kontrol et."""
        try:
            teams_monitor = self.get_teams_monitor()
            if not teams_monitor["found"] or not teams_monitor["monitor_bounds"]:
                return False

            cursor_x, cursor_y = get_cursor_pos()
            bounds = teams_monitor["monitor_bounds"]

            return (bounds["left"] <= cursor_x < bounds["right"] and
                    bounds["top"] <= cursor_y < bounds["bottom"])
        except Exception as e:
            logger.warning(f"Cursor monitor kontrolu hatasi: {e}")
            return False

    def get_teams_status_cached(self, force_refresh=False):
        """Cache'li Teams durum sorgusu — ASLA bloklamaz"""
        import time as _time
        now = _time.time()
        cache = self._cache

        # Force refresh — arka planda güncelle, mevcut cache'i döndür
        if force_refresh:
            self.refresh_cache_async()
            if cache["status"] is not None:
                return cache["status"]
            return self._empty_status()

        # Cache geçerli mi?
        if (cache["status"] is not None
                and (now - cache["timestamp"]) < cache["ttl"]):
            return cache["status"]

        # Cache geçersiz — arka planda güncelle, mevcut olanı döndür
        self.refresh_cache_async()

        if cache["status"] is not None:
            return cache["status"]  # Eski ama mevcut

        # Hiç cache yok — boş status döndür, arka plan dolduracak
        return self._empty_status()

    def _empty_status(self):
        """Boş status dict — cache henüz dolmamışken kullanılır"""
        return {
            "detected": False,
            "type": None,
            "process_name": None,
            "pid": None,
            "browser_name": None,
            "window_found": False,
            "hwnd": None,
            "window_title": None,
            "needs_tab_switch": False,
            "monitor_count": 1,
            "teams_monitor": {"found": False},
            "teams_rect": {"found": False},
        }

    def refresh_cache_async(self, callback=None):
        """Cache'i arka plan thread'inde güncelle"""
        import time as _time

        if self._cache["updating"]:
            return  # Zaten güncelleniyor

        def worker():
            self._cache["updating"] = True
            try:
                status = self.get_teams_status()
                self._cache["status"] = status
                self._cache["timestamp"] = _time.time()
            except Exception as e:
                logger.info(f"Cache yenileme hatasi: {e}")
            finally:
                self._cache["updating"] = False

            if callback:
                try:
                    callback(self._cache["status"])
                except Exception as e:
                    logger.debug(f"Cache callback hatasi: {e}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _paste_text(self, text):
        """Metni clipboard'a kopyala ve Ctrl+V ile yapıştır — klavye layout sorunsuz"""
        if not PYAUTOGUI_AVAILABLE:
            return False

        import time as _time

        try:
            if IS_WINDOWS:
                # Windows clipboard API ile kopyala
                CF_UNICODETEXT = 13
                kernel32 = ctypes.windll.kernel32
                user32 = ctypes.windll.user32

                user32.OpenClipboard(0)
                user32.EmptyClipboard()

                hMem = kernel32.GlobalAlloc(0x0042, (len(text) + 1) * 2)  # GMEM_MOVEABLE | GMEM_ZEROINIT
                pMem = kernel32.GlobalLock(hMem)
                ctypes.cdll.msvcrt.wcscpy_s(ctypes.c_wchar_p(pMem), len(text) + 1, text)
                kernel32.GlobalUnlock(hMem)
                user32.SetClipboardData(CF_UNICODETEXT, hMem)
                user32.CloseClipboard()
            else:
                # Mac/Linux — pyperclip fallback
                try:
                    import pyperclip
                    pyperclip.copy(text)
                except ImportError:
                    pyautogui.write(text, interval=0.02)
                    return True

            _time.sleep(0.1)

            # Ctrl+V ile yapıştır
            pyautogui.hotkey('ctrl', 'v')
            _time.sleep(0.1)

            return True
        except Exception as e:
            logger.debug(f"Clipboard yapistirma hatasi: {e}")
            try:
                pyautogui.write(text, interval=0.02)
                return True
            except Exception as e2:
                logger.debug(f"PyAutoGUI write fallback hatasi: {e2}")
                return False

    def _focus_teams_via_pyautogui(self):
        """PyAutoGUI ile browser'da Teams sekmesine geç"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "method": "pyautogui_not_available"}

        import time as _time

        # Browser bul
        browser_info = self._detect_browser_with_teams()
        browser_hwnd = None
        browser_name = ""

        if browser_info.get("found"):
            browser_name = browser_info.get("browser_name", "")
            browser_hwnd = browser_info.get("browser_hwnd") or self._find_browser_window(browser_name)

        if not browser_hwnd:
            # Desktop Teams dene
            window_info = self.detect_teams_window()
            if window_info.get("hwnd"):
                try:
                    ShowWindow(window_info["hwnd"], SW_RESTORE)
                    SetForegroundWindow(window_info["hwnd"])
                    return {"success": True, "method": "desktop_focus"}
                except Exception as e:
                    logger.warning(f"Desktop Teams focus hatasi: {e}")
            return {"success": False, "method": "no_browser_hwnd"}

        try:
            # Browser'ı öne getir
            ShowWindow(browser_hwnd, SW_RESTORE)
            _time.sleep(0.4)
            SetForegroundWindow(browser_hwnd)
            _time.sleep(0.5)

            # Ctrl+L → adres çubuğuna odaklan
            pyautogui.hotkey('ctrl', 'l')
            _time.sleep(0.3)

            # Mevcut içeriği seç
            pyautogui.hotkey('ctrl', 'a')
            _time.sleep(0.1)

            # URL'yi clipboard üzerinden yapıştır (Türkçe Q klavye sorunsuz)
            self._paste_text("https://teams.microsoft.com")
            _time.sleep(0.2)

            # Enter bas
            pyautogui.press('enter')

            return {"success": True, "method": "pyautogui_address_bar", "browser": browser_name}
        except Exception as e:
            logger.debug(f"PyAutoGUI focus hatasi: {e}")
            return {"success": False, "method": "pyautogui_failed"}

    def _find_browser_executable(self, browser_name=None):
        """Browser executable path'ini bul"""
        if not IS_WINDOWS:
            return None

        known_paths = {
            "Chrome": [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            ],
            "Edge": [
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            ],
            "Firefox": [
                os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
            ],
            "Brave": [
                os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ],
            "Opera": [
                os.path.expandvars(r"%LocalAppData%\Programs\Opera\opera.exe"),
            ]
        }

        # Belirli browser istendiyse — bilinen path'lerden ara
        if browser_name and browser_name in known_paths:
            for path in known_paths[browser_name]:
                if os.path.isfile(path):
                    return path

        # Registry'den dene
        registry_keys = {
            "Chrome": r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
            "Edge": r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
            "Firefox": r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe",
        }

        if browser_name and browser_name in registry_keys:
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_keys[browser_name])
                path, _ = winreg.QueryValueEx(key, "")
                winreg.CloseKey(key)
                if os.path.isfile(path):
                    return path
            except Exception as e:
                logger.debug(f"Registry browser arama hatasi: {e}")

        # browser_name belirtilmemişse — tüm browser'ları dene
        if not browser_name:
            for name in ["Chrome", "Edge", "Firefox", "Brave", "Opera"]:
                path = self._find_browser_executable(name)
                if path:
                    return path

        return None

    def resolve_browser(self, preference="Otomatik"):
        """Kullanıcı tercihine göre başlatılacak browser'ı belirle"""
        if preference != "Otomatik":
            exe_path = self._find_browser_executable(preference)
            if exe_path:
                return {"browser_name": preference, "exe_path": exe_path, "found": True}
            else:
                return {"browser_name": preference, "exe_path": None, "found": False}

        # Otomatik — Teams açık olan browser → sıralı deneme
        cached = self.get_teams_status_cached()
        if cached and cached.get("type") == "browser" and cached.get("browser_name"):
            bname = cached["browser_name"]
            exe_path = self._find_browser_executable(bname)
            if exe_path:
                return {"browser_name": bname, "exe_path": exe_path, "found": True}

        for name in ["Chrome", "Edge", "Firefox", "Brave", "Opera"]:
            exe_path = self._find_browser_executable(name)
            if exe_path:
                return {"browser_name": name, "exe_path": exe_path, "found": True}

        return {"browser_name": None, "exe_path": None, "found": False}

    def open_teams_in_specific_browser(self, browser_name=None):
        """Belirtilen browser'da Teams URL'sini aç — os.startfile KULLANMAZ"""
        exe_path = self._find_browser_executable(browser_name)

        if exe_path:
            try:
                subprocess.Popen(
                    [exe_path, "https://teams.microsoft.com"],
                    creationflags=0x08000000 if IS_WINDOWS else 0
                )
                return {"success": True, "method": "direct_exe", "browser": browser_name, "path": exe_path}
            except Exception as e:
                logger.debug(f"Browser baslatma hatasi (exe): {e}")

        # Exe bulunamadıysa — komut adı ile dene
        if IS_WINDOWS and browser_name:
            browser_commands = {
                "Chrome": "chrome", "Edge": "msedge", "Firefox": "firefox",
                "Brave": "brave", "Opera": "opera"
            }
            cmd = browser_commands.get(browser_name)
            if cmd:
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0
                    subprocess.Popen(
                        [cmd, "https://teams.microsoft.com"],
                        startupinfo=startupinfo,
                        creationflags=0x08000000
                    )
                    return {"success": True, "method": "command", "browser": browser_name}
                except Exception as e:
                    logger.debug(f"Browser baslatma hatasi (cmd): {e}")

        # Son çare — pyautogui yöntemi
        if PYAUTOGUI_AVAILABLE:
            result = self._focus_teams_via_pyautogui()
            if result.get("success"):
                return result

        return {"success": False, "method": "all_failed"}

    def focus_teams_tab(self, browser_name=None):
        """Browser'da Teams sekmesine geç veya aç"""
        if not IS_WINDOWS:
            return {"success": False, "method": "not_windows"}

        import time as _time

        # 1. Mevcut Teams penceresini bul ve öne getir
        window_info = self.detect_teams_window()
        if window_info.get("found") and window_info.get("hwnd"):
            try:
                ShowWindow(window_info["hwnd"], SW_RESTORE)
                _time.sleep(0.3)
                SetForegroundWindow(window_info["hwnd"])
                return {"success": True, "method": "existing_window"}
            except Exception as e:
                logger.warning(f"Teams sekme focus hatasi: {e}")

        # 2. Mevcut browser'ı öne getir + pyautogui ile Ctrl+L + URL
        if PYAUTOGUI_AVAILABLE:
            browser_hwnd = None
            if browser_name:
                browser_hwnd = self._find_browser_window(browser_name)
            else:
                cached = self.get_teams_status_cached()
                bname = (cached or {}).get("browser_name", "")
                if bname:
                    browser_hwnd = self._find_browser_window(bname)
                    browser_name = bname

            if browser_hwnd:
                try:
                    ShowWindow(browser_hwnd, SW_RESTORE)
                    _time.sleep(0.4)
                    SetForegroundWindow(browser_hwnd)
                    _time.sleep(0.5)
                    pyautogui.hotkey('ctrl', 'l')
                    _time.sleep(0.3)
                    pyautogui.hotkey('ctrl', 'a')
                    _time.sleep(0.1)
                    self._paste_text("https://teams.microsoft.com")
                    _time.sleep(0.2)
                    pyautogui.press('enter')
                    return {"success": True, "method": "pyautogui_address_bar", "browser": browser_name}
                except Exception as e:
                    logger.debug(f"PyAutoGUI tab focus hatasi: {e}")

        # 3. Browser executable ile doğrudan aç (SON ve EN GÜVENİLİR)
        result = self.open_teams_in_specific_browser(browser_name)
        if result.get("success"):
            return result

        return {"success": False, "method": "all_failed"}
