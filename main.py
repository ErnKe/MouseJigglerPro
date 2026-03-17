"""
Mouse Jiggler Pro — Baslatici
Made by Eren Kekic
"""

import sys
from constants import LOCK_FILE
from utils import logger, SingleInstanceLock


def main():
    """Ana baslatma fonksiyonu"""
    logger.info("=== Mouse Jiggler Pro baslatiliyor ===")

    # Tek instance kontrolu
    lock = SingleInstanceLock(LOCK_FILE)
    if not lock.acquire():
        logger.warning("Baska bir instance zaten calisiyor — cikiliyor")

        # Kullaniciya bilgi ver (GUI olmadan)
        try:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "Mouse Jiggler Pro zaten çalışıyor!\n\nGörev çubuğunda veya sistem tepsisinde arayın.",
                    "Mouse Jiggler Pro",
                    0x40  # MB_ICONINFORMATION
                )
        except Exception:
            pass

        sys.exit(1)

    try:
        from app import MouseJigglerPro
        app = MouseJigglerPro()
        app.run()
    except Exception as e:
        logger.critical(f"Uygulama coktu: {e}", exc_info=True)
        raise
    finally:
        lock.release()
        logger.info("=== Mouse Jiggler Pro kapatildi ===")


if __name__ == "__main__":
    main()
