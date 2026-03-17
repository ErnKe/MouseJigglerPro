"""
Mouse Jiggler Pro — Sabitler
Renk, font ve varsayilan ayar tanimlari
"""

import os

# ===== DOSYA YOLLARI =====
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".mouse_jiggler_settings.json")
LOG_DIR = os.path.join(os.path.expanduser("~"), ".mouse_jiggler_logs")
LOG_FILE = os.path.join(LOG_DIR, "mouse_jiggler.log")
LOCK_FILE = os.path.join(os.path.expanduser("~"), ".mouse_jiggler.lock")

# ===== RENK SABİTLERİ =====
COLORS = {
    # Ana tema renkleri
    "accent_green": "#4ecca3",
    "accent_green_hover": "#3db892",
    "accent_red": "#ff6b6b",
    "accent_red_hover": "#e55a5a",
    "accent_yellow": "#f9ca24",
    "accent_yellow_hover": "#d4a820",
    "teams_blue": "#0078d4",
    "teams_blue_hover": "#006abc",

    # Arka plan renkleri
    "bg_dark": "#1a1a2e",
    "bg_card": "#2a2a3e",
    "bg_button": "#333",
    "bg_button_hover": "#444",
    "bg_button_alt": "#555",

    # Metin renkleri
    "text_primary": "white",
    "text_secondary": "#888",
    "text_dark": "#1a1a2e",
    "text_tertiary": "#aaa",
    "text_dim": "#666",

    # Toast renkleri
    "toast_success_bg": "#2d6b4f",
    "toast_success_border": "#4ecca3",
    "toast_success_text": "#e0ffe0",
    "toast_warning_bg": "#6b5a2d",
    "toast_warning_border": "#f9ca24",
    "toast_warning_text": "#fff8e0",
    "toast_error_bg": "#6b2d2d",
    "toast_error_border": "#ff6b6b",
    "toast_error_text": "#ffe0e0",
    "toast_info_bg": "#2d4a6b",
    "toast_info_border": "#0078d4",
    "toast_info_text": "#e0f0ff",
}

# Font boyutlari
FONTS = {
    "title": 22,
    "subtitle": 20,
    "heading": 18,
    "section_heading": 17,
    "button": 16,
    "section": 15,
    "body": 14,
    "body_small": 13,
    "caption": 12,
    "tiny": 11,
}

# ===== VARSAYILAN AYARLAR =====
DEFAULT_SETTINGS = {
    "speed": 50,
    "distance": 15,
    "pattern": "Rastgele",
    "auto_stop_enabled": False,
    "auto_stop_minutes": 60,
    "delayed_start_enabled": False,
    "delayed_start_minutes": 5,
    "schedule_enabled": False,
    "schedule_start": "09:00",
    "schedule_end": "18:00",
    "pause_on_user_activity": True,
    "always_on_top": False,
    "teams_interval": "Sürekli",
    "teams_custom_interval_seconds": 30,
    "teams_movement_type": "Minimal",
    "teams_auto_pull": True,
    "teams_window_track": True,
    "teams_notify_on_close": True,
    "teams_auto_stop_enabled": False,
    "teams_auto_stop_minutes": 480,
    "teams_default_browser": "Otomatik",
}
