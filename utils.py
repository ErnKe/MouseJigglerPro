"""
Mouse Jiggler Pro — Yardimci Araclar
Platform tespiti, Windows API, cursor fonksiyonlari
"""

import logging
import logging.handlers
import os

from constants import LOG_DIR, LOG_FILE

# ===== LOGGING YAPILANDIRMASI =====
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("MouseJigglerPro")
logger.setLevel(logging.DEBUG)

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8'
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(module)-20s | %(funcName)-30s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.WARNING)
_console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(_console_handler)

logger.info("Mouse Jiggler Pro baslatiliyor...")

import platform
import ctypes

# ===== PLATFORM TESPİTİ =====
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# ===== DPI SCALING FIX =====
if IS_WINDOWS:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception as e:
        logger.debug(f"Per-monitor DPI ayari hatasi, fallback deneniyor: {e}")
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e2:
            logger.debug(f"DPI awareness fallback hatasi: {e2}")

# ===== OPSİYONEL KÜTÜPHANELER =====
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    logger.debug("pystray/PIL bulunamadi — system tray devre disi")
    TRAY_AVAILABLE = False
    pystray = None
    Image = None
    ImageDraw = None

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    logger.debug("keyboard bulunamadi — klavye kisayollari devre disi")
    KEYBOARD_AVAILABLE = False
    keyboard = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.debug("psutil bulunamadi — process tespiti devre disi")
    PSUTIL_AVAILABLE = False
    psutil = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Kose guvenligini kapat (mouse jiggler icin gerekli)
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    logger.debug("pyautogui bulunamadi — cross-platform mouse devre disi")
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None

# ===== WINDOWS API TANIMLARI =====
if IS_WINDOWS:
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    def get_cursor_pos():
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def set_cursor_pos(x, y):
        ctypes.windll.user32.SetCursorPos(x, y)

    # Teams Window Detection
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    GetWindowTextW = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    # Multi-Monitor API
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                    ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

    MonitorFromWindow = ctypes.windll.user32.MonitorFromWindow
    GetMonitorInfoW = ctypes.windll.user32.GetMonitorInfoW
    EnumDisplayMonitors = ctypes.windll.user32.EnumDisplayMonitors
    GetWindowRect = ctypes.windll.user32.GetWindowRect
    SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
    ShowWindow = ctypes.windll.user32.ShowWindow

    MONITOR_DEFAULTTONEAREST = 2
    SW_RESTORE = 9
    SW_SHOW = 5
    SW_MINIMIZE = 6

else:
    # Mac/Linux — pyautogui fallback
    try:
        import pyautogui
        def get_cursor_pos():
            pos = pyautogui.position()
            return pos.x, pos.y

        def set_cursor_pos(x, y):
            pyautogui.moveTo(x, y)
    except ImportError:
        logger.debug("pyautogui bulunamadi (non-Windows) — dummy cursor fonksiyonlari")
        def get_cursor_pos():
            return 0, 0

        def set_cursor_pos(x, y):
            pass

    # Dummy Windows API tanimlari — TeamsDetector IS_WINDOWS kontrolu yapacak
    POINT = None
    RECT = None
    MONITORINFO = None
    EnumWindows = None
    EnumWindowsProc = None
    GetWindowTextW = None
    GetWindowTextLengthW = None
    IsWindowVisible = None
    MonitorFromWindow = None
    GetMonitorInfoW = None
    EnumDisplayMonitors = None
    GetWindowRect = None
    SetForegroundWindow = None
    ShowWindow = None
    MONITOR_DEFAULTTONEAREST = 2
    SW_RESTORE = 9
    SW_SHOW = 5
    SW_MINIMIZE = 6


# ===== TEK INSTANCE KİLİDİ =====
class SingleInstanceLock:
    """Lockfile ile tek instance garantisi — Windows + cross-platform"""

    def __init__(self, lock_path):
        self.lock_path = lock_path
        self.lock_file = None
        self.locked = False

    def acquire(self):
        """Kilidi al — basariliysa True, baska instance varsa False"""
        try:
            if IS_WINDOWS:
                import msvcrt
                self.lock_file = open(self.lock_path, 'w')
                msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                self.lock_file.write(str(os.getpid()))
                self.lock_file.flush()
                self.locked = True
                logger.debug("Instance kilidi alindi")
                return True
            else:
                import fcntl
                self.lock_file = open(self.lock_path, 'w')
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.lock_file.write(str(os.getpid()))
                self.lock_file.flush()
                self.locked = True
                logger.debug("Instance kilidi alindi")
                return True
        except (IOError, OSError, ImportError) as e:
            logger.warning(f"Baska bir instance zaten calisiyor: {e}")
            if self.lock_file:
                try:
                    self.lock_file.close()
                except Exception:
                    pass
                self.lock_file = None
            return False

    def release(self):
        """Kilidi serbest birak"""
        if self.lock_file:
            try:
                if IS_WINDOWS:
                    import msvcrt
                    try:
                        msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                else:
                    import fcntl
                    try:
                        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass

                self.lock_file.close()
                self.lock_file = None
                self.locked = False
                logger.debug("Instance kilidi serbest birakildi")
            except Exception as e:
                logger.debug(f"Kilit serbest birakma hatasi: {e}")

        # Lock dosyasini sil
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception:
            pass

    def __del__(self):
        self.release()
