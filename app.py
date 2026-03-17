"""
Mouse Jiggler Pro — Ana Uygulama
Modern ve gelismis Mouse Jiggler + Teams entegrasyonu
Made by Eren Kekic
"""

import customtkinter as ctk
import random
import math
import threading
import sys
import json
import os
import subprocess
from datetime import datetime, time

from constants import COLORS, FONTS, DEFAULT_SETTINGS, SETTINGS_FILE
from utils import (
    IS_WINDOWS,
    TRAY_AVAILABLE, KEYBOARD_AVAILABLE, PYAUTOGUI_AVAILABLE, PSUTIL_AVAILABLE,
    pystray, Image, ImageDraw, keyboard, pyautogui,
    get_cursor_pos, set_cursor_pos,
    ShowWindow, SetForegroundWindow, SW_RESTORE,
    logger,
)
from teams_detector import TeamsDetector

# Tema ayari
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class MouseJigglerPro:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Mouse Jiggler Pro")

        # Sabit boyut - DPI scaling'e karşı
        self.root.geometry("380x400")
        self.root.minsize(380, 400)
        self.root.maxsize(380, 400)
        self.root.resizable(False, False)

        # Durum değişkenleri
        self.running = False
        self.paused_by_user = False
        self.job = None
        self.timer_job = None
        self.auto_stop_job = None
        self.delayed_start_job = None
        self.schedule_job = None
        self.user_check_job = None
        self.elapsed_seconds = 0
        self.tray_icon = None
        self.last_mouse_pos = (0, 0)
        self.mini_mode = False
        self.current_page = "main"  # main veya settings

        # Teams modu durum değişkenleri
        self.teams_running = False
        self.teams_job = None
        self.teams_timer_job = None
        self.teams_auto_stop_job = None
        self.teams_monitor_job = None
        self.teams_elapsed_seconds = 0
        self.teams_process_job = None
        self.teams_delayed_job = None
        self.teams_retry_job = None
        self.teams_move_count = 0
        self.teams_live_scan_job = None
        self._selected_teams_type = None
        self.selection_overlay = None

        # Hareket deseni için
        self.angle = 0
        self.square_step = 0

        # Varsayılan ayarlar
        self.settings = dict(DEFAULT_SETTINGS)

        # Ayarları yükle
        self.load_settings()

        # Teams tespit
        self.teams_detector = TeamsDetector()
        self.teams_status = self.teams_detector.get_teams_status_cached()

        # UI oluştur
        self.setup_main_page()
        self.setup_settings_page()
        self.setup_teams_page()
        self.setup_teams_settings_page()
        self.setup_keyboard_shortcut()
        self._setup_toast()

        # Ana sayfayı göster
        self.show_main_page()

        # Zamanlanmış çalışma kontrolü
        self.check_schedule()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Teams açılış kontrolü
        self.root.after(500, self.check_teams_on_startup)
        logger.info("Uygulama basariyla baslatildi")

    def _cancel_job(self, job_attr_name):
        """root.after job'ını güvenli şekilde iptal et"""
        job = getattr(self, job_attr_name, None)
        if job:
            try:
                self.root.after_cancel(job)
            except Exception as e:
                logger.debug(f"Job iptal hatasi: {e}")
            setattr(self, job_attr_name, None)

    # ==================== ANA SAYFA ====================
    def setup_main_page(self):
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")

        # ===== BAŞLIK =====
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 0))

        title_label = ctk.CTkLabel(header_frame, text="🖱️  Mouse Jiggler Pro",
                                   font=ctk.CTkFont(size=FONTS["title"], weight="bold"))
        title_label.pack(side="left")

        self.status_label = ctk.CTkLabel(header_frame, text="●",
                                         font=ctk.CTkFont(size=FONTS["subtitle"]),
                                         text_color=COLORS["accent_red"])
        self.status_label.pack(side="right")

        # ===== ANA BUTON =====
        self.btn = ctk.CTkButton(self.main_frame, text="▶   BAŞLAT",
                                 font=ctk.CTkFont(size=FONTS["button"], weight="bold"),
                                 height=50, corner_radius=12,
                                 fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"],
                                 text_color=COLORS["text_dark"],
                                 command=self.toggle)
        self.btn.pack(fill="x", padx=25, pady=(20, 10))

        # ===== ÇALIŞMA SÜRESİ =====
        self.timer_label = ctk.CTkLabel(self.main_frame, text="Çalışma Süresi: 00:00:00",
                                        font=ctk.CTkFont(size=FONTS["body"]),
                                        text_color=COLORS["text_secondary"])
        self.timer_label.pack()

        # ===== DURUM BİLGİSİ =====
        self.status_info = ctk.CTkLabel(self.main_frame, text="",
                                        font=ctk.CTkFont(size=FONTS["body_small"]),
                                        text_color=COLORS["accent_yellow"])
        self.status_info.pack(pady=(5, 0))

        # ===== KISA YOL BİLGİSİ =====
        shortcut_text = "F9: Başlat / Durdur" if KEYBOARD_AVAILABLE else ""
        shortcut_label = ctk.CTkLabel(self.main_frame, text=shortcut_text,
                                      font=ctk.CTkFont(size=FONTS["body_small"], weight="bold"),
                                      text_color=COLORS["accent_green"])
        shortcut_label.pack(pady=(8, 0))

        # ===== BUTONLAR =====
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(15, 0))

        # Ayarlar butonu
        self.settings_btn = ctk.CTkButton(btn_frame, text="⚙️  Ayarlar",
                                          font=ctk.CTkFont(size=FONTS["body_small"]),
                                          width=100, height=36,
                                          corner_radius=10,
                                          fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                                          command=self.show_settings_page)
        self.settings_btn.pack(side="left")

        # Mini mod butonu
        self.mini_btn = ctk.CTkButton(btn_frame, text="🗕  Mini",
                                      font=ctk.CTkFont(size=FONTS["body_small"]),
                                      width=85, height=36,
                                      corner_radius=10,
                                      fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                                      command=self.toggle_mini_mode)
        self.mini_btn.pack(side="left", padx=(12, 0))

        # Tray butonu
        if TRAY_AVAILABLE:
            self.tray_btn = ctk.CTkButton(btn_frame, text="📥  Tepsi",
                                          font=ctk.CTkFont(size=FONTS["body_small"]),
                                          width=85, height=36,
                                          corner_radius=10,
                                          fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                                          command=self.minimize_to_tray)
            self.tray_btn.pack(side="left", padx=(12, 0))

        # Teams Modu butonu — ayrı satır
        teams_btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        teams_btn_frame.pack(fill="x", padx=25, pady=(8, 0))

        self.teams_mode_btn = ctk.CTkButton(teams_btn_frame, text="🟢  Teams Modu",
                                             font=ctk.CTkFont(size=FONTS["body_small"], weight="bold"),
                                             height=36, corner_radius=10,
                                             fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"],
                                             command=self.show_teams_page)
        self.teams_mode_btn.pack(fill="x")

        # ===== KREDİ =====
        credit = ctk.CTkLabel(self.main_frame, text="Made by Eren Kekiç",
                              font=ctk.CTkFont(size=FONTS["body_small"], weight="bold"),
                              text_color=COLORS["text_primary"])
        credit.pack(side="bottom", pady=(15, 20))

    # ==================== AYARLAR SAYFASI ====================
    def setup_settings_page(self):
        self.settings_frame = ctk.CTkFrame(self.root, fg_color="transparent")

        # ===== ÜST BAR =====
        top_bar = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 10))

        back_btn = ctk.CTkButton(top_bar, text="←  Geri",
                                 font=ctk.CTkFont(size=FONTS["body"], weight="bold"),
                                 width=90, height=35,
                                 corner_radius=10,
                                 fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                                 command=self.show_main_page)
        back_btn.pack(side="left")

        title = ctk.CTkLabel(top_bar, text="⚙️  Ayarlar",
                            font=ctk.CTkFont(size=FONTS["subtitle"], weight="bold"))
        title.pack(side="left", padx=(15, 0))

        # ===== İÇERİK =====
        content = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=(5, 15))

        # ----- HAREKET AYARLARI -----
        self.create_section(content, "🎛️  Hareket Ayarları")

        # Hız
        speed_frame = ctk.CTkFrame(content, fg_color="transparent")
        speed_frame.pack(fill="x", pady=(8, 6))
        ctk.CTkLabel(speed_frame, text="Hız:", font=ctk.CTkFont(size=FONTS["body_small"]),
                    width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(speed_frame, text="Yavaş", font=ctk.CTkFont(size=FONTS["tiny"]),
                    text_color=COLORS["text_secondary"]).pack(side="left")
        self.speed_slider = ctk.CTkSlider(speed_frame, from_=10, to=100, width=160,
                                          button_color=COLORS["accent_green"], button_hover_color=COLORS["accent_green_hover"],
                                          progress_color=COLORS["accent_green"])
        self.speed_slider.set(self.settings["speed"])
        self.speed_slider.pack(side="left", padx=10)
        ctk.CTkLabel(speed_frame, text="Hızlı", font=ctk.CTkFont(size=FONTS["tiny"]),
                    text_color=COLORS["text_secondary"]).pack(side="left")

        # Mesafe
        dist_frame = ctk.CTkFrame(content, fg_color="transparent")
        dist_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(dist_frame, text="Mesafe:", font=ctk.CTkFont(size=FONTS["body_small"]),
                    width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(dist_frame, text="Küçük", font=ctk.CTkFont(size=FONTS["tiny"]),
                    text_color=COLORS["text_secondary"]).pack(side="left")
        self.distance_slider = ctk.CTkSlider(dist_frame, from_=5, to=50, width=160,
                                             button_color=COLORS["accent_green"], button_hover_color=COLORS["accent_green_hover"],
                                             progress_color=COLORS["accent_green"])
        self.distance_slider.set(self.settings["distance"])
        self.distance_slider.pack(side="left", padx=10)
        ctk.CTkLabel(dist_frame, text="Büyük", font=ctk.CTkFont(size=FONTS["tiny"]),
                    text_color=COLORS["text_secondary"]).pack(side="left")

        # Desen
        pattern_frame = ctk.CTkFrame(content, fg_color="transparent")
        pattern_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(pattern_frame, text="Desen:", font=ctk.CTkFont(size=FONTS["body_small"]),
                    width=80, anchor="w").pack(side="left")
        self.pattern_var = ctk.StringVar(value=self.settings["pattern"])
        self.pattern_menu = ctk.CTkOptionMenu(pattern_frame, variable=self.pattern_var,
                                              values=["Rastgele", "Dairesel", "Kare"],
                                              width=150, height=30,
                                              font=ctk.CTkFont(size=FONTS["caption"]),
                                              fg_color=COLORS["bg_button"], button_color=COLORS["bg_button_hover"],
                                              button_hover_color=COLORS["bg_button_alt"])
        self.pattern_menu.pack(side="left")

        # ----- ZAMANLAMA -----
        self.create_section(content, "⏰  Zamanlama")

        # Otomatik durdurma
        auto_frame = ctk.CTkFrame(content, fg_color="transparent")
        auto_frame.pack(fill="x", pady=(8, 4))
        self.auto_stop_var = ctk.BooleanVar(value=self.settings["auto_stop_enabled"])
        ctk.CTkCheckBox(auto_frame, text="Otomatik durdur:",
                       variable=self.auto_stop_var,
                       font=ctk.CTkFont(size=FONTS["body_small"]),
                       checkbox_width=22, checkbox_height=22,
                       fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"]).pack(side="left")
        self.auto_stop_entry = ctk.CTkEntry(auto_frame, width=55, height=30,
                                            font=ctk.CTkFont(size=FONTS["caption"]))
        self.auto_stop_entry.insert(0, str(self.settings["auto_stop_minutes"]))
        self.auto_stop_entry.pack(side="left", padx=10)
        ctk.CTkLabel(auto_frame, text="dk sonra", font=ctk.CTkFont(size=FONTS["caption"])).pack(side="left")

        # Gecikmeli başlatma
        delay_frame = ctk.CTkFrame(content, fg_color="transparent")
        delay_frame.pack(fill="x", pady=(4, 4))
        self.delayed_var = ctk.BooleanVar(value=self.settings["delayed_start_enabled"])
        ctk.CTkCheckBox(delay_frame, text="Gecikmeli başlat:",
                       variable=self.delayed_var,
                       font=ctk.CTkFont(size=FONTS["body_small"]),
                       checkbox_width=22, checkbox_height=22,
                       fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"]).pack(side="left")
        self.delayed_entry = ctk.CTkEntry(delay_frame, width=55, height=30,
                                          font=ctk.CTkFont(size=FONTS["caption"]))
        self.delayed_entry.insert(0, str(self.settings["delayed_start_minutes"]))
        self.delayed_entry.pack(side="left", padx=10)
        ctk.CTkLabel(delay_frame, text="dk sonra", font=ctk.CTkFont(size=FONTS["caption"])).pack(side="left")

        # Zamanlanmış
        schedule_frame = ctk.CTkFrame(content, fg_color="transparent")
        schedule_frame.pack(fill="x", pady=(4, 5))
        self.schedule_var = ctk.BooleanVar(value=self.settings["schedule_enabled"])
        ctk.CTkCheckBox(schedule_frame, text="Zamanlanmış:",
                       variable=self.schedule_var,
                       font=ctk.CTkFont(size=FONTS["body_small"]),
                       checkbox_width=22, checkbox_height=22,
                       fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"]).pack(side="left")
        self.schedule_start = ctk.CTkEntry(schedule_frame, width=60, height=30,
                                           font=ctk.CTkFont(size=FONTS["caption"]))
        self.schedule_start.insert(0, self.settings["schedule_start"])
        self.schedule_start.pack(side="left", padx=(10, 5))
        ctk.CTkLabel(schedule_frame, text="-", font=ctk.CTkFont(size=FONTS["body"], weight="bold")).pack(side="left")
        self.schedule_end = ctk.CTkEntry(schedule_frame, width=60, height=30,
                                         font=ctk.CTkFont(size=FONTS["caption"]))
        self.schedule_end.insert(0, self.settings["schedule_end"])
        self.schedule_end.pack(side="left", padx=5)

        # ----- AKILLI ÖZELLİKLER -----
        self.create_section(content, "⚡  Akıllı Özellikler")

        self.pause_var = ctk.BooleanVar(value=self.settings["pause_on_user_activity"])
        ctk.CTkCheckBox(content, text="Kullanıcı mouse'u hareket ettirince duraklat",
                       variable=self.pause_var,
                       font=ctk.CTkFont(size=FONTS["body_small"]),
                       checkbox_width=22, checkbox_height=22,
                       fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"]).pack(anchor="w", pady=(8, 4))

        self.topmost_var = ctk.BooleanVar(value=self.settings["always_on_top"])
        ctk.CTkCheckBox(content, text="Her zaman üstte",
                       variable=self.topmost_var,
                       font=ctk.CTkFont(size=FONTS["body_small"]),
                       checkbox_width=22, checkbox_height=22,
                       fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"]).pack(anchor="w", pady=(0, 15))

    # ==================== TEAMS SAYFASI ====================
    def setup_teams_page(self):
        """Teams modu sayfası"""
        self.teams_frame = ctk.CTkFrame(self.root, fg_color="transparent")

        # ===== ÜST BAR =====
        top_bar = ctk.CTkFrame(self.teams_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(15, 5))

        back_btn = ctk.CTkButton(top_bar, text="←  Geri",
                                  font=ctk.CTkFont(size=FONTS["body_small"]),
                                  width=80, height=32, corner_radius=8,
                                  fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                                  command=self.show_main_page)
        back_btn.pack(side="left")

        title = ctk.CTkLabel(top_bar, text="🟢  Teams Modu",
                              font=ctk.CTkFont(size=FONTS["section_heading"], weight="bold"),
                              text_color=COLORS["teams_blue"])
        title.pack(side="left", padx=(12, 0))

        # Durum göstergesi (sağda)
        self.teams_status_indicator = ctk.CTkLabel(
            top_bar, text="●",
            font=ctk.CTkFont(size=FONTS["heading"]),
            text_color=COLORS["accent_green"] if self.teams_status.get("detected") else COLORS["accent_yellow"])
        self.teams_status_indicator.pack(side="right")

        # ===== TEAMS DURUM KARTI =====
        card = ctk.CTkFrame(self.teams_frame, fg_color=COLORS["bg_card"], corner_radius=12)
        card.pack(fill="x", padx=20, pady=(10, 0))

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=15, pady=12)

        # Teams tipi
        teams_type_text = "✅ " + self.teams_status.get("type", "Bilinmiyor").title() if self.teams_status.get("detected") else "❌ Teams bulunamadı"
        self.teams_type_label = ctk.CTkLabel(card_inner, text=teams_type_text,
                                              font=ctk.CTkFont(size=FONTS["body"], weight="bold"),
                                              text_color="white")
        self.teams_type_label.pack(anchor="w")

        # Monitör bilgisi
        monitor_info = self.teams_status.get("teams_monitor", {})
        monitor_text = f"Monitör #{monitor_info.get('monitor_index', '?')}" if monitor_info.get("found") else "Monitör bilgisi yok"
        self.teams_monitor_label = ctk.CTkLabel(card_inner, text=monitor_text,
                                                 font=ctk.CTkFont(size=FONTS["caption"]),
                                                 text_color=COLORS["text_tertiary"])
        self.teams_monitor_label.pack(side="left", anchor="w")

        # Pencere durumu
        window_text = "Pencere bulundu ✓" if self.teams_status.get("window_found") else "Pencere bulunamadı ✗"
        window_color = COLORS["accent_green"] if self.teams_status.get("window_found") else COLORS["accent_red"]
        self.teams_window_label = ctk.CTkLabel(card_inner, text=window_text,
                                                font=ctk.CTkFont(size=FONTS["caption"]),
                                                text_color=window_color)
        self.teams_window_label.pack(side="right", anchor="e")

        # Canlı izleme göstergesi
        self.live_scan_indicator = ctk.CTkLabel(card, text="● Canlı izleniyor",
                                                 font=ctk.CTkFont(size=FONTS["tiny"]),
                                                 text_color=COLORS["accent_green"])
        self.live_scan_indicator.pack(pady=(0, 10))

        # ===== TEAMS BAŞLAT BUTONU =====
        self.teams_start_btn = ctk.CTkButton(
            self.teams_frame, text="🟢  TEAMS BAŞLAT",
            font=ctk.CTkFont(size=FONTS["button"], weight="bold"),
            height=50, corner_radius=12,
            fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"],
            text_color="white",
            command=self.toggle_teams_mode)
        self.teams_start_btn.pack(fill="x", padx=20, pady=(15, 0))

        # F9 kısayol bilgisi
        if KEYBOARD_AVAILABLE:
            shortcut_label = ctk.CTkLabel(
                self.teams_frame, text="F9: Başlat / Durdur",
                font=ctk.CTkFont(size=FONTS["caption"]),
                text_color=COLORS["accent_green"])
            shortcut_label.pack(pady=(4, 0))

        # Çalışma süresi
        self.teams_timer_label = ctk.CTkLabel(
            self.teams_frame, text="Çalışma Süresi: 00:00:00",
            font=ctk.CTkFont(size=FONTS["body_small"]),
            text_color=COLORS["text_tertiary"])
        self.teams_timer_label.pack(pady=(8, 0))

        # Durum bilgisi
        self.teams_status_info = ctk.CTkLabel(
            self.teams_frame, text="",
            font=ctk.CTkFont(size=FONTS["body_small"]),
            text_color=COLORS["accent_yellow"])
        self.teams_status_info.pack(pady=(4, 0))

        # Teams Ayarları butonu
        settings_btn = ctk.CTkButton(
            self.teams_frame, text="⚙️  Teams Ayarları",
            font=ctk.CTkFont(size=FONTS["body_small"]),
            height=36, corner_radius=10,
            fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
            command=self.show_teams_settings_page)
        settings_btn.pack(fill="x", padx=20, pady=(12, 0))

        # Alt uyarı
        warning = ctk.CTkLabel(
            self.teams_frame, text="⚠️ Mouse Teams penceresinde kalacaktır",
            font=ctk.CTkFont(size=FONTS["tiny"]),
            text_color=COLORS["text_dim"])
        warning.pack(side="bottom", pady=(0, 12))

    # ==================== TEAMS AYARLARI SAYFASI ====================
    def setup_teams_settings_page(self):
        """Teams ayarları sayfası"""
        self.teams_settings_frame = ctk.CTkFrame(self.root, fg_color="transparent")

        # ===== ÜST BAR =====
        top_bar = ctk.CTkFrame(self.teams_settings_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(15, 5))

        back_btn = ctk.CTkButton(top_bar, text="←  Geri",
                                  font=ctk.CTkFont(size=FONTS["body_small"]),
                                  width=80, height=32, corner_radius=8,
                                  fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                                  command=self.show_teams_page)
        back_btn.pack(side="left")

        title = ctk.CTkLabel(top_bar, text="⚙️  Teams Ayarları",
                              font=ctk.CTkFont(size=FONTS["section_heading"], weight="bold"),
                              text_color=COLORS["teams_blue"])
        title.pack(side="left", padx=(12, 0))

        # İçerik alanı — scroll destekli
        content = ctk.CTkScrollableFrame(self.teams_settings_frame, fg_color="transparent",
                                          scrollbar_button_color=COLORS["bg_button_hover"], scrollbar_button_hover_color=COLORS["bg_button_alt"])
        content.pack(fill="both", expand=True, padx=20, pady=(5, 10))

        # ===== VARSAYILAN TARAYICI =====
        self.create_section(content, "🌐  Varsayılan Tarayıcı")

        browser_frame = ctk.CTkFrame(content, fg_color="transparent")
        browser_frame.pack(fill="x", pady=(8, 6))

        ctk.CTkLabel(browser_frame, text="Tarayıcı:", font=ctk.CTkFont(size=FONTS["body_small"]),
                     width=80, anchor="w").pack(side="left")

        self.teams_browser_var = ctk.StringVar(value=self.settings.get("teams_default_browser", "Otomatik"))
        self.teams_browser_menu = ctk.CTkOptionMenu(
            browser_frame,
            variable=self.teams_browser_var,
            values=["Otomatik", "Chrome", "Edge", "Firefox", "Brave", "Opera"],
            width=160, height=30,
            font=ctk.CTkFont(size=FONTS["caption"]),
            fg_color=COLORS["bg_button"], button_color=COLORS["bg_button_hover"],
            button_hover_color=COLORS["bg_button_alt"]
        )
        self.teams_browser_menu.pack(side="left", padx=(10, 0))

        # ===== HAREKET ARALIĞI =====
        self.create_section(content, "⏱️  Hareket Aralığı")

        interval_frame = ctk.CTkFrame(content, fg_color="transparent")
        interval_frame.pack(fill="x", pady=(8, 0))

        self.teams_interval_var = ctk.StringVar(value=self.settings.get("teams_interval", "Sürekli"))
        interval_options = ["Sürekli", "10 Saniye", "30 Saniye", "1 Dakika",
                           "5 Dakika", "10 Dakika", "20 Dakika", "30 Dakika", "Özel"]
        self.teams_interval_menu = ctk.CTkOptionMenu(
            interval_frame, variable=self.teams_interval_var,
            values=interval_options,
            font=ctk.CTkFont(size=FONTS["body_small"]),
            width=180, height=32,
            fg_color=COLORS["bg_button"], button_color=COLORS["bg_button_hover"],
            command=self._on_teams_interval_change)
        self.teams_interval_menu.pack(side="left")

        self.teams_custom_interval_entry = ctk.CTkEntry(
            interval_frame, placeholder_text="Saniye cinsinden girin",
            font=ctk.CTkFont(size=FONTS["caption"]),
            width=140, height=32,
            state="disabled")
        self.teams_custom_interval_entry.pack(side="left", padx=(10, 0))

        # Özel değer yüklü ise entry'ye yaz
        if self.settings.get("teams_interval") == "Özel":
            self.teams_custom_interval_entry.configure(state="normal")
            self.teams_custom_interval_entry.insert(0, str(self.settings.get("teams_custom_interval_seconds", 30)))

        # ===== HAREKET TİPİ =====
        self.create_section(content, "🎯  Hareket Tipi")

        self.teams_movement_var = ctk.StringVar(value=self.settings.get("teams_movement_type", "Minimal"))
        movement_options = ["Minimal", "Küçük", "Orta"]
        self.teams_movement_menu = ctk.CTkOptionMenu(
            content, variable=self.teams_movement_var,
            values=movement_options,
            font=ctk.CTkFont(size=FONTS["body_small"]),
            width=180, height=32,
            fg_color=COLORS["bg_button"], button_color=COLORS["bg_button_hover"])
        self.teams_movement_menu.pack(anchor="w", pady=(8, 0))

        # Açıklama
        movement_desc = ctk.CTkLabel(content, text="Minimal: 1-3px  |  Küçük: 3-8px  |  Orta: 8-15px",
                                      font=ctk.CTkFont(size=FONTS["tiny"]),
                                      text_color=COLORS["text_dim"])
        movement_desc.pack(anchor="w", pady=(4, 0))

        # ===== AKILLI ÖZELLİKLER =====
        self.create_section(content, "⚡  Akıllı Özellikler")

        self.teams_auto_pull_var = ctk.BooleanVar(value=self.settings.get("teams_auto_pull", True))
        ctk.CTkCheckBox(content, text="Mouse'u otomatik Teams ekranına çek",
                        variable=self.teams_auto_pull_var,
                        font=ctk.CTkFont(size=FONTS["body_small"]),
                        checkbox_width=22, checkbox_height=22,
                        fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"]).pack(anchor="w", pady=(8, 4))

        self.teams_window_track_var = ctk.BooleanVar(value=self.settings.get("teams_window_track", True))
        ctk.CTkCheckBox(content, text="Teams pencere değişikliklerini takip et",
                        variable=self.teams_window_track_var,
                        font=ctk.CTkFont(size=FONTS["body_small"]),
                        checkbox_width=22, checkbox_height=22,
                        fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"]).pack(anchor="w", pady=(0, 4))

        self.teams_notify_var = ctk.BooleanVar(value=self.settings.get("teams_notify_on_close", True))
        ctk.CTkCheckBox(content, text="Teams kapanırsa bildirim ver",
                        variable=self.teams_notify_var,
                        font=ctk.CTkFont(size=FONTS["body_small"]),
                        checkbox_width=22, checkbox_height=22,
                        fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"]).pack(anchor="w", pady=(0, 4))

        # ===== OTOMATİK DURDURMA =====
        self.create_section(content, "⏰  Otomatik Durdurma")

        auto_stop_frame = ctk.CTkFrame(content, fg_color="transparent")
        auto_stop_frame.pack(fill="x", pady=(8, 0))

        self.teams_auto_stop_var = ctk.BooleanVar(value=self.settings.get("teams_auto_stop_enabled", False))
        ctk.CTkCheckBox(auto_stop_frame, text="",
                        variable=self.teams_auto_stop_var,
                        font=ctk.CTkFont(size=FONTS["body_small"]),
                        checkbox_width=22, checkbox_height=22,
                        width=30,
                        fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"]).pack(side="left")

        self.teams_auto_stop_entry = ctk.CTkEntry(
            auto_stop_frame,
            font=ctk.CTkFont(size=FONTS["body_small"]),
            width=55, height=30)
        self.teams_auto_stop_entry.pack(side="left", padx=(4, 0))
        self.teams_auto_stop_entry.insert(0, str(self.settings.get("teams_auto_stop_minutes", 480)))

        ctk.CTkLabel(auto_stop_frame, text="dakika sonra durdur",
                     font=ctk.CTkFont(size=FONTS["body_small"]),
                     text_color=COLORS["text_tertiary"]).pack(side="left", padx=(8, 0))

    def _on_teams_interval_change(self, value):
        """Teams hareket aralığı değiştiğinde özel entry'yi aç/kapat"""
        if value == "Özel":
            self.teams_custom_interval_entry.configure(state="normal")
        else:
            self.teams_custom_interval_entry.configure(state="disabled")

    def create_section(self, parent, text):
        """Bölüm başlığı"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(12, 0))

        label = ctk.CTkLabel(frame, text=text,
                            font=ctk.CTkFont(size=FONTS["section"], weight="bold"),
                            text_color=COLORS["accent_green"])
        label.pack(side="left")

        separator = ctk.CTkFrame(frame, height=2, fg_color=COLORS["bg_button_hover"])
        separator.pack(side="left", fill="x", expand=True, padx=(12, 0))

    # ==================== SAYFA GEÇİŞLERİ ====================
    def show_main_page(self):
        """Ana sayfayı göster"""
        # Önce ayarları kaydet
        if self.current_page == "settings":
            self.save_current_settings()
        if self.current_page == "teams_settings":
            self.save_teams_settings()

        self.settings_frame.pack_forget()
        if hasattr(self, 'teams_frame'):
            self.teams_frame.pack_forget()
        if hasattr(self, 'teams_settings_frame'):
            self.teams_settings_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.current_page = "main"

        # Pencere boyutunu ayarla
        self.root.geometry("380x400")
        self.root.minsize(380, 400)
        self.root.maxsize(380, 400)
        self._stop_teams_live_scan()

    def show_settings_page(self):
        """Ayarlar sayfasını göster"""
        self.main_frame.pack_forget()
        if hasattr(self, 'teams_frame'):
            self.teams_frame.pack_forget()
        if hasattr(self, 'teams_settings_frame'):
            self.teams_settings_frame.pack_forget()
        self.settings_frame.pack(fill="both", expand=True)
        self.current_page = "settings"

        # Ayarlar için daha büyük pencere
        self.root.geometry("420x530")
        self.root.minsize(420, 530)
        self.root.maxsize(420, 530)
        self._stop_teams_live_scan()

    def show_teams_page(self):
        """Teams sayfasını göster"""
        if self.current_page == "settings":
            self.save_current_settings()
        if self.current_page == "teams_settings":
            self.save_teams_settings()

        self.main_frame.pack_forget()
        self.settings_frame.pack_forget()
        if hasattr(self, 'teams_settings_frame'):
            self.teams_settings_frame.pack_forget()
        self.teams_frame.pack(fill="both", expand=True)
        self.current_page = "teams"

        self.root.geometry("400x420")
        self.root.minsize(400, 420)
        self.root.maxsize(400, 420)

        # Cache'den anında göster
        cached_status = self.teams_detector.get_teams_status_cached()
        if cached_status:
            self.teams_status = cached_status
            self._update_teams_card()

        # Canlı izlemeyi başlat (3sn'de bir arka planda tarar)
        self._start_teams_live_scan()

    def show_teams_settings_page(self):
        """Teams ayarları sayfasını göster"""
        self.teams_frame.pack_forget()
        self.teams_settings_frame.pack(fill="both", expand=True)
        self.current_page = "teams_settings"

        self.root.geometry("420x500")
        self.root.minsize(420, 500)
        self.root.maxsize(420, 500)

    # ==================== TOAST BİLDİRİM SİSTEMİ ====================
    def _setup_toast(self):
        """Sağ üstten çıkan küçük toast baloncuğu"""
        self.toast_frame = ctk.CTkFrame(self.root, corner_radius=12, fg_color=COLORS["bg_card"],
                                         border_width=1, border_color=COLORS["bg_button_hover"])
        self.toast_label = ctk.CTkLabel(self.toast_frame, text="",
                                         font=ctk.CTkFont(size=FONTS["caption"]),
                                         text_color="white", wraplength=200,
                                         justify="left")
        self.toast_label.pack(padx=12, pady=8)
        self.toast_visible = False
        self.toast_hide_job = None

    def show_toast(self, message, toast_type="info"):
        """Sağ üst köşede küçük baloncuk bildirimi"""
        colors = {
            "success": {"bg": COLORS["toast_success_bg"], "border": COLORS["toast_success_border"], "text": COLORS["toast_success_text"]},
            "warning": {"bg": COLORS["toast_warning_bg"], "border": COLORS["toast_warning_border"], "text": COLORS["toast_warning_text"]},
            "error":   {"bg": COLORS["toast_error_bg"], "border": COLORS["toast_error_border"], "text": COLORS["toast_error_text"]},
            "info":    {"bg": COLORS["toast_info_bg"], "border": COLORS["toast_info_border"], "text": COLORS["toast_info_text"]},
        }
        style = colors.get(toast_type, colors["info"])

        self.toast_frame.configure(fg_color=style["bg"], border_color=style["border"])
        self.toast_label.configure(text=message, text_color=style["text"])

        # Önceki hide job'ı iptal et
        self._cancel_job("toast_hide_job")

        # Sağ üstte küçük baloncuk — relwidth YOK (auto-size)
        self.toast_frame.place(relx=0.97, rely=0.04, anchor="ne")
        self.toast_frame.lift()
        self.toast_visible = True

        # 4 saniye sonra gizle
        self.toast_hide_job = self.root.after(4000, self._hide_toast)

    def _hide_toast(self):
        """Toast'ı gizle"""
        if self.toast_visible:
            self.toast_frame.place_forget()
            self.toast_visible = False
            self.toast_hide_job = None

    # ==================== TEAMS AÇILIŞ KONTROLÜ ====================
    def check_teams_on_startup(self):
        """Açılışta Teams durumunu sessizce cache'e al"""
        self.teams_detector.refresh_cache_async(
            callback=lambda status: self.root.after(0, lambda: self._on_startup_cache_ready(status))
        )

    def _on_startup_cache_ready(self, status):
        """Startup cache hazır — sadece kaydet, toast yok"""
        if status:
            self.teams_status = status

    # ==================== CANLI İZLEME ====================
    def _start_teams_live_scan(self):
        """Teams canlı izleme başlat — 3sn'de bir arka planda tarar"""
        self._do_teams_live_scan()

    def _do_teams_live_scan(self):
        """Periyodik Teams tarama döngüsü"""
        # Sadece teams sayfasındayken çalış
        if self.current_page not in ("teams", "teams_settings"):
            self.teams_live_scan_job = None
            return

        if hasattr(self, 'live_scan_indicator'):
            self.live_scan_indicator.configure(text="◌ Taranıyor...")

        # Arka planda tara
        self.teams_detector.refresh_cache_async(
            callback=lambda status: self.root.after(0, lambda: self._on_live_scan_result(status))
        )

        # 3 saniye sonra tekrar
        self.teams_live_scan_job = self.root.after(3000, self._do_teams_live_scan)

    def _on_live_scan_result(self, status):
        """Canlı tarama sonucu — kartı sessizce güncelle, durum değişirse toast"""
        if status is None:
            if hasattr(self, 'live_scan_indicator'):
                self.live_scan_indicator.configure(text="● Canlı izleniyor")
            return

        old_detected = self.teams_status.get("detected", False) if self.teams_status else False
        old_window = self.teams_status.get("window_found", False) if self.teams_status else False

        self.teams_status = status

        # Sadece teams sayfasındayken güncelle
        if self.current_page in ("teams", "teams_settings"):
            self._update_teams_card()

            # Durum değişikliği varsa toast göster
            new_detected = status.get("detected", False)
            new_window = status.get("window_found", False)

            if not old_detected and new_detected:
                browser_name = status.get("browser_name", "")
                type_text = f"Browser ({browser_name})" if browser_name else "Masaüstü"
                self.show_toast(f"Teams tespit edildi — {type_text}", "success")
            elif old_window and not new_window:
                self.show_toast("Teams penceresi kayboldu", "warning")
            elif not old_window and new_window:
                self.show_toast("Teams penceresi bulundu", "success")

        if hasattr(self, 'live_scan_indicator'):
            self.live_scan_indicator.configure(text="● Canlı izleniyor")

    def _stop_teams_live_scan(self):
        """Teams canlı izlemeyi durdur"""
        self._cancel_job("teams_live_scan_job")

    # ==================== TEAMS MOD FONKSİYONLARI ====================
    def toggle_teams_mode(self):
        """Teams modunu başlat/durdur"""
        if self.teams_running:
            self.stop_teams_mode()
        else:
            if self.current_page in ("teams", "teams_settings"):
                self._show_teams_selection()
            else:
                # Tray, mini mod → otomatik seç
                self._auto_start_teams()

    def start_teams_mode(self):
        """Eski uyumluluk — otomatik başlat"""
        self._auto_start_teams()

    def _auto_start_teams(self):
        """Otomatik Teams başlat — tray, mini mod için"""
        # Teams sayfasına geç
        if self.current_page not in ("teams", "teams_settings"):
            self.show_teams_page()

        # Önce son kullanılan türü dene
        if hasattr(self, '_selected_teams_type') and self._selected_teams_type:
            self._start_teams_with_type(self._selected_teams_type)
            return

        # Cache'den tür belirle — self.teams_status zaten canlı izleme ile güncelleniyor
        status = self.teams_status
        if status:
            teams_type = status.get("type", "")
            if teams_type in ("browser", "desktop"):
                self._start_teams_with_type(teams_type)
                return

        # Hiçbir bilgi yok — varsayılan browser ile başlat
        self._start_teams_with_type("browser")

    def _show_teams_selection(self):
        """Teams türü seçim ekranı — cache'den anında, gecikme YOK"""
        self.selection_overlay = ctk.CTkFrame(self.root, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.selection_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.selection_overlay.lift()

        inner = ctk.CTkFrame(self.selection_overlay, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text="Teams Türünü Seçin",
                     font=ctk.CTkFont(size=FONTS["heading"], weight="bold"),
                     text_color="white").pack(pady=(0, 20))

        # === CACHE'DEN OKU — SENKRON TESPİT YOK ===
        status = self.teams_status or {}
        detected_type = status.get("type", "")
        browser_name = status.get("browser_name", "")
        detected = status.get("detected", False)
        needs_tab = status.get("needs_tab_switch", False)

        # Browser durumu
        browser_available = detected and detected_type == "browser"
        if not browser_available and detected and needs_tab:
            browser_available = True

        # Varsayılan tarayıcı ayarına göre label belirle
        default_browser = self.settings.get("teams_default_browser", "Otomatik")
        if default_browser != "Otomatik":
            browser_label = f"🌐  {default_browser} ile Teams"
        elif browser_name:
            browser_label = f"🌐  Browser ({browser_name})"
        else:
            browser_label = "🌐  Browser Teams"
        browser_sublabel = "Tespit edildi ✓" if browser_available else "Tıklayın — açılacak"

        browser_frame = ctk.CTkFrame(inner, fg_color=COLORS["bg_card"], corner_radius=12)
        browser_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(browser_frame, text=browser_label,
                       font=ctk.CTkFont(size=FONTS["section"], weight="bold"),
                       height=55, corner_radius=12,
                       fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"],
                       text_color="white",
                       command=lambda: self._start_teams_with_type("browser")).pack(fill="x", padx=10, pady=(10, 2))
        ctk.CTkLabel(browser_frame, text=browser_sublabel,
                      font=ctk.CTkFont(size=FONTS["tiny"]),
                      text_color=COLORS["accent_green"] if browser_available else COLORS["text_secondary"]).pack(pady=(0, 8))

        # Masaüstü durumu
        desktop_available = detected and detected_type == "desktop"
        desktop_sublabel = "Tespit edildi ✓" if desktop_available else "Tıklayın — açılacak"

        desktop_frame = ctk.CTkFrame(inner, fg_color=COLORS["bg_card"], corner_radius=12)
        desktop_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(desktop_frame, text="🖥️  Masaüstü Uygulaması",
                       font=ctk.CTkFont(size=FONTS["section"], weight="bold"),
                       height=55, corner_radius=12,
                       fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"],
                       text_color=COLORS["text_dark"],
                       command=lambda: self._start_teams_with_type("desktop")).pack(fill="x", padx=10, pady=(10, 2))
        ctk.CTkLabel(desktop_frame, text=desktop_sublabel,
                      font=ctk.CTkFont(size=FONTS["tiny"]),
                      text_color=COLORS["accent_green"] if desktop_available else COLORS["text_secondary"]).pack(pady=(0, 8))

        ctk.CTkButton(inner, text="İptal",
                       font=ctk.CTkFont(size=FONTS["body_small"]),
                       width=100, height=35, corner_radius=10,
                       fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                       command=self._hide_teams_selection).pack(pady=(10, 0))

    def _hide_teams_selection(self):
        """Seçim overlay'ini kapat"""
        if hasattr(self, 'selection_overlay') and self.selection_overlay:
            self.selection_overlay.place_forget()
            self.selection_overlay.destroy()
            self.selection_overlay = None

    def _start_teams_with_type(self, teams_type):
        """Kullanıcının seçtiği Teams türüne göre başlat"""
        self._hide_teams_selection()
        if self.running:
            self.stop()
        self.teams_running = True
        self.teams_elapsed_seconds = 0
        self.teams_move_count = 0
        self._selected_teams_type = teams_type
        logger.info(f"Teams modu baslatildi — tur: {teams_type}")

        # UI anında güncelle
        self.teams_start_btn.configure(text="⏹  TEAMS DURDUR",
                                        fg_color=COLORS["accent_red"], hover_color=COLORS["accent_red_hover"])
        self.teams_status_info.configure(text="🔄 Teams açılıyor...")

        # Timer ve jiggle'ı HEMEN başlat
        self.update_teams_timer()
        self.teams_jiggle()
        self.track_teams_window()
        self.monitor_teams_process()

        # Otomatik durdurma
        if self.settings.get("teams_auto_stop_enabled", False):
            try:
                stop_minutes = int(self.settings.get("teams_auto_stop_minutes", 480))
                self.teams_auto_stop_job = self.root.after(stop_minutes * 60 * 1000, self.stop_teams_mode)
            except Exception as e:
                logger.debug(f"Teams auto-stop parse hatasi: {e}")

        # Teams'i arka planda öne getir ve odakla
        self._focus_selected_teams_async(teams_type)

    def _focus_selected_teams_async(self, teams_type):
        """Seçilen Teams türünü arka planda odakla"""
        def worker():
            import time as _time

            if teams_type == "browser":
                # Varsayılan tarayıcı ayarından browser belirle
                preference = self.settings.get("teams_default_browser", "Otomatik")
                browser_info = self.teams_detector.resolve_browser(preference)
                browser_name = browser_info.get("browser_name")
                exe_path = browser_info.get("exe_path")

                if not browser_info.get("found") and preference != "Otomatik":
                    # Kullanıcının seçtiği browser yok — otomatik fallback
                    self.root.after(0, lambda: self.show_toast(
                        f"⚠️ {preference} bulunamadı — otomatik seçiliyor", "warning"))
                    fallback = self.teams_detector.resolve_browser("Otomatik")
                    browser_name = fallback.get("browser_name")
                    exe_path = fallback.get("exe_path")

                if not exe_path:
                    self.root.after(0, lambda: self.show_toast(
                        "❌ Hiçbir browser bulunamadı", "error"))
                    self.root.after(0, lambda: self._on_focus_complete(None, "browser"))
                    return

                # Teams'i browser'da aç
                result = self.teams_detector.focus_teams_tab(browser_name=browser_name)

                if result.get("success"):
                    _time.sleep(2.5)
                    self.teams_detector.refresh_cache_async(
                        callback=lambda s: self.root.after(0, lambda: self._on_focus_complete(s, "browser"))
                    )
                else:
                    # Doğrudan exe ile aç
                    try:
                        subprocess.Popen(
                            [exe_path, "https://teams.microsoft.com"],
                            creationflags=0x08000000 if IS_WINDOWS else 0
                        )
                        _time.sleep(3)
                        self.teams_detector.refresh_cache_async(
                            callback=lambda s: self.root.after(0, lambda: self._on_focus_complete(s, "browser"))
                        )
                    except Exception as e:
                        logger.warning(f"Browser focus hatasi: {e}")
                        self.root.after(0, lambda: self._on_focus_complete(None, "browser"))

            elif teams_type == "desktop":
                window_info = self.teams_detector.detect_teams_window()

                if window_info.get("hwnd"):
                    try:
                        ShowWindow(window_info["hwnd"], SW_RESTORE)
                        _time.sleep(0.3)
                        SetForegroundWindow(window_info["hwnd"])
                        _time.sleep(1)
                    except Exception as e:
                        logger.warning(f"Desktop Teams focus hatasi: {e}")
                else:
                    # Process var ama pencere yok — Teams protocol ile başlat
                    try:
                        if IS_WINDOWS:
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            startupinfo.wShowWindow = 0
                            subprocess.Popen(
                                ["cmd", "/c", "start", "", "msteams:"],
                                creationflags=0x08000000,
                                startupinfo=startupinfo
                            )
                            _time.sleep(3)
                    except Exception as e:
                        logger.debug(f"msteams: protokol baslatma hatasi: {e}")

                self.teams_detector.refresh_cache_async(
                    callback=lambda s: self.root.after(0, lambda: self._on_focus_complete(s, "desktop"))
                )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _on_focus_complete(self, status, teams_type):
        """Focus sonucu — tüm senaryolar"""
        if not self.teams_running:
            return

        if status:
            self.teams_status = status
            if self.current_page in ("teams", "teams_settings"):
                self._update_teams_card()

        window_found = (status or {}).get("window_found", False)
        detected = (status or {}).get("detected", False)

        if window_found:
            type_text = "Browser" if teams_type == "browser" else "Masaüstü"
            if self.current_page in ("teams", "teams_settings"):
                self.show_toast(f"✅ {type_text} Teams aktif", "success")
            if self.settings.get("teams_auto_pull", True):
                rect = (status or {}).get("teams_rect", {})
                if rect.get("found"):
                    self.teams_detector.move_cursor_to_teams()
        elif detected:
            if self.current_page in ("teams", "teams_settings"):
                self.show_toast("ℹ️ Teams yükleniyor...", "info")
            self.root.after(5000, lambda: self._delayed_recheck(teams_type))
        else:
            if self.current_page in ("teams", "teams_settings"):
                self.show_toast("⚠️ Teams bulunamadı — fallback modda", "warning")

        self.teams_status_info.configure(text=f"🔄 Aktif — {self.teams_move_count} hareket")

    def _delayed_recheck(self, teams_type):
        """5sn sonra tekrar kontrol"""
        if not self.teams_running:
            return
        self.teams_detector.refresh_cache_async(
            callback=lambda s: self.root.after(0, lambda: self._on_recheck_result(s, teams_type))
        )

    def _on_recheck_result(self, status, teams_type):
        """Gecikmeli kontrol sonucu"""
        if not self.teams_running or not status:
            return
        self.teams_status = status
        if self.current_page in ("teams", "teams_settings"):
            self._update_teams_card()
            if status.get("window_found"):
                self.show_toast("✅ Teams penceresi bulundu!", "success")
                if self.settings.get("teams_auto_pull", True):
                    rect = status.get("teams_rect", {})
                    if rect.get("found"):
                        self.teams_detector.move_cursor_to_teams()

    def stop_teams_mode(self):
        """Teams modunu durdur"""
        self.teams_running = False
        logger.info("Teams modu durduruldu")

        # Buton güncelle
        self.teams_start_btn.configure(text="🟢  TEAMS BAŞLAT",
                                        fg_color=COLORS["teams_blue"], hover_color=COLORS["teams_blue_hover"])
        self.teams_timer_label.configure(text="Çalışma Süresi: 00:00:00")
        self.teams_status_info.configure(text="")

        # Tüm teams job'larını iptal et
        for job_name in ["teams_job", "teams_timer_job", "teams_auto_stop_job",
                         "teams_monitor_job", "teams_process_job", "teams_delayed_job", "teams_retry_job"]:
            self._cancel_job(job_name)

        # Temizlik
        self._selected_teams_type = None
        if hasattr(self, 'selection_overlay') and self.selection_overlay:
            self._hide_teams_selection()

    def teams_jiggle(self):
        """Teams penceresinde mouse hareket ettir"""
        if not self.teams_running:
            return

        try:
            window_info = self.teams_detector.get_teams_window_rect()

            # Hareket tipi belirle
            movement = self.settings.get("teams_movement_type", "Minimal")
            if movement == "Minimal":
                max_dist = 3
            elif movement == "Küçük":
                max_dist = 8
            else:  # Orta
                max_dist = 15

            current_x, current_y = get_cursor_pos()

            if window_info.get("found"):
                # Teams penceresi bulundu — sınırlar içinde hareket et
                rect = window_info
                margin = 50

                # Mouse Teams dışındaysa çek
                if self.settings.get("teams_auto_pull", True):
                    if not (rect["left"] + margin <= current_x <= rect["right"] - margin and
                            rect["top"] + margin <= current_y <= rect["bottom"] - margin):
                        set_cursor_pos(rect["center_x"], rect["center_y"])
                        current_x, current_y = rect["center_x"], rect["center_y"]

                dx = random.randint(-max_dist, max_dist)
                dy = random.randint(-max_dist, max_dist)
                new_x = max(rect["left"] + margin, min(rect["right"] - margin, current_x + dx))
                new_y = max(rect["top"] + margin, min(rect["bottom"] - margin, current_y + dy))
                set_cursor_pos(new_x, new_y)
            else:
                # Teams penceresi bulunamadı — mevcut konumda küçük hareket yap (FALLBACK)
                dx = random.randint(-max_dist, max_dist)
                dy = random.randint(-max_dist, max_dist)
                set_cursor_pos(current_x + dx, current_y + dy)

            # Hareket sayacını artır
            self.teams_move_count += 1
            if self.teams_running:
                self.teams_status_info.configure(
                    text=f"🔄 Aktif — {self.teams_move_count} hareket")

        except Exception as e:
            logger.error(f"Teams cursor hareket hatasi: {e}")

        # Sonraki hareketi zamanla
        try:
            interval = self.settings.get("teams_interval", "Sürekli")
            if interval == "Sürekli":
                delay_ms = 1000 + random.randint(-200, 200)
            elif interval == "Özel":
                custom_sec = self.settings.get("teams_custom_interval_seconds", 30)
                delay_ms = max(1000, custom_sec * 1000)
            else:
                delay_ms = self._parse_interval(interval)
            self.teams_job = self.root.after(delay_ms, self.teams_jiggle)
        except Exception as e:
            logger.debug(f"Teams interval parse hatasi: {e}")
            self.teams_job = self.root.after(1000, self.teams_jiggle)

    def _parse_interval(self, interval_str):
        """Interval string'ini milisaniyeye çevir"""
        mapping = {
            "10 Saniye": 10000,
            "30 Saniye": 30000,
            "1 Dakika": 60000,
            "5 Dakika": 300000,
            "10 Dakika": 600000,
            "20 Dakika": 1200000,
            "30 Dakika": 1800000,
        }
        return mapping.get(interval_str, 1000)

    def track_teams_window(self):
        """Teams penceresini periyodik olarak takip et"""
        if not self.teams_running:
            return

        if not self.settings.get("teams_window_track", True):
            self.teams_monitor_job = self.root.after(5000, self.track_teams_window)
            return

        try:
            window_info = self.teams_detector.get_teams_window_rect()
            if not window_info.get("found"):
                self.teams_status_info.configure(text="⚠️ Teams penceresi kayboldu!")
                # 5 saniye sonra tekrar kontrol et
                self.teams_monitor_job = self.root.after(5000, self.track_teams_window)
                return

            # Pencere bulundu, uyarı varsa temizle
            current_text = self.teams_status_info.cget("text")
            if "kayboldu" in current_text:
                self.teams_status_info.configure(text="🔄 Teams modu aktif")

        except Exception as e:
            logger.warning(f"Teams pencere takip hatasi: {e}")

        self.teams_monitor_job = self.root.after(3000, self.track_teams_window)

    def update_teams_timer(self):
        """Teams modu çalışma süresini güncelle"""
        if not self.teams_running:
            return
        self.teams_elapsed_seconds += 1
        hrs = self.teams_elapsed_seconds // 3600
        mins = (self.teams_elapsed_seconds % 3600) // 60
        secs = self.teams_elapsed_seconds % 60
        self.teams_timer_label.configure(text=f"Çalışma Süresi: {hrs:02d}:{mins:02d}:{secs:02d}")
        self.teams_timer_job = self.root.after(1000, self.update_teams_timer)

    def monitor_teams_process(self):
        """Teams process'ini periyodik olarak kontrol et"""
        if not self.teams_running:
            return

        try:
            status = self.teams_detector.detect_teams_process()

            if not status.get("found", False):
                # Teams kapanmış
                if self.settings.get("teams_notify_on_close", True):
                    self.show_teams_notification(
                        "Teams Kapandı",
                        "⚠️ Microsoft Teams kapandı!\nTeams modu duraklatıldı.",
                        "warning"
                    )
                self.teams_status_info.configure(text="⚠️ Teams kapandı — bekleniyor...")
                self.teams_process_job = self.root.after(10000, self.monitor_teams_process)
                return

            # Teams tekrar açılmış mı kontrol et
            current_text = self.teams_status_info.cget("text")
            if "Teams kapandı" in current_text:
                self.teams_status_info.configure(text="✅ Teams tekrar algılandı!")
                self.show_teams_notification(
                    "Teams Algılandı",
                    "✅ Microsoft Teams tekrar açıldı!\nTeams modu devam ediyor.",
                    "info"
                )
                self.teams_status = self.teams_detector.get_teams_status_cached(force_refresh=True)

        except Exception as e:
            logger.info(f"Teams process izleme hatasi: {e}")

        self.teams_process_job = self.root.after(15000, self.monitor_teams_process)

    def show_teams_notification(self, title, message, notification_type="info"):
        """Toast bildirimi göster — sadece Teams sayfalarında"""
        if self.current_page not in ("teams", "teams_settings"):
            return
        if notification_type == "warning":
            self.show_toast(message, "warning")
        elif notification_type == "error":
            self.show_toast(message, "error")
        else:
            self.show_toast(message, "success")

    def _update_teams_card(self):
        """Teams durum kartındaki 4 label'ı self.teams_status'a göre güncelle"""
        status = self.teams_status
        detected = status.get("detected", False)
        needs_tab = status.get("needs_tab_switch", False)

        # 1. Tip label
        if detected:
            teams_type = status.get("type", "")
            browser_name = status.get("browser_name", "")
            if teams_type == "browser" and browser_name:
                type_text = f"Browser ({browser_name})"
            elif teams_type == "desktop":
                type_text = "Masaüstü Uygulaması"
            else:
                type_text = teams_type.title() if teams_type else "Tespit Edildi"
            self.teams_type_label.configure(text=f"✅ {type_text}")
        else:
            self.teams_type_label.configure(text="❌ Teams bulunamadı")

        # 2. Durum indikatörü rengi
        if detected and not needs_tab:
            self.teams_status_indicator.configure(text_color=COLORS["accent_green"])
        elif detected and needs_tab:
            self.teams_status_indicator.configure(text_color=COLORS["teams_blue"])
        else:
            self.teams_status_indicator.configure(text_color=COLORS["accent_yellow"])

        # 3. Pencere durumu — 3 durum
        if status.get("window_found"):
            self.teams_window_label.configure(text="Pencere bulundu ✓", text_color=COLORS["accent_green"])
        elif detected and needs_tab:
            self.teams_window_label.configure(text="Sekme aktif değil ⟳", text_color=COLORS["teams_blue"])
        else:
            self.teams_window_label.configure(text="Pencere bulunamadı ✗", text_color=COLORS["accent_red"])

        # 4. Monitör bilgisi
        monitor_info = status.get("teams_monitor", {})
        if monitor_info.get("found"):
            self.teams_monitor_label.configure(
                text=f"Monitör #{monitor_info.get('monitor_index', '?')}")
        else:
            self.teams_monitor_label.configure(text="Monitör bilgisi yok")

    def save_current_settings(self):
        """Mevcut ayarları kaydet"""
        try:
            self.settings["speed"] = int(self.speed_slider.get())
            self.settings["distance"] = int(self.distance_slider.get())
            self.settings["pattern"] = self.pattern_var.get()
            self.settings["auto_stop_enabled"] = self.auto_stop_var.get()
            self.settings["auto_stop_minutes"] = int(self.auto_stop_entry.get() or 60)
            self.settings["delayed_start_enabled"] = self.delayed_var.get()
            self.settings["delayed_start_minutes"] = int(self.delayed_entry.get() or 5)
            self.settings["schedule_enabled"] = self.schedule_var.get()
            self.settings["schedule_start"] = self.schedule_start.get() or "09:00"
            self.settings["schedule_end"] = self.schedule_end.get() or "18:00"
            self.settings["pause_on_user_activity"] = self.pause_var.get()
            self.settings["always_on_top"] = self.topmost_var.get()

            self.root.attributes('-topmost', self.settings["always_on_top"])
            self.save_settings()
        except ValueError:
            pass

    def save_teams_settings(self):
        """Teams ayarlarını kaydet"""
        try:
            self.settings["teams_interval"] = self.teams_interval_var.get()
            # Özel aralık değeri
            if self.teams_interval_var.get() == "Özel":
                custom_val = self.teams_custom_interval_entry.get()
                self.settings["teams_custom_interval_seconds"] = int(custom_val) if custom_val else 30
            self.settings["teams_movement_type"] = self.teams_movement_var.get()
            self.settings["teams_auto_pull"] = self.teams_auto_pull_var.get()
            self.settings["teams_window_track"] = self.teams_window_track_var.get()
            self.settings["teams_notify_on_close"] = self.teams_notify_var.get()
            self.settings["teams_auto_stop_enabled"] = self.teams_auto_stop_var.get()
            self.settings["teams_auto_stop_minutes"] = int(self.teams_auto_stop_entry.get() or 480)
            self.settings["teams_default_browser"] = self.teams_browser_var.get()
            self.save_settings()
        except ValueError:
            pass

    def save_settings(self):
        """Ayarları dosyaya kaydet"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.debug("Ayarlar kaydedildi")
        except Exception as e:
            logger.error(f"Ayarlar kaydedilemedi: {e}")

    def load_settings(self):
        """Ayarları dosyadan yükle"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
                logger.debug("Ayarlar yuklendi")
        except Exception as e:
            logger.error(f"Ayarlar yüklenemedi: {e}")

    # ==================== KLAVYE KISAYOLU ====================
    def setup_keyboard_shortcut(self):
        """Klavye kısayolu — sadece F9"""
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.add_hotkey('F9', self.toggle_from_hotkey, suppress=False)
            except Exception as e:
                logger.debug(f"Keyboard kisayol hatasi: {e}")
                try:
                    self.root.bind('<F9>', lambda e: self._smart_f9_toggle())
                except Exception as e2:
                    logger.debug(f"Tkinter F9 bind hatasi: {e2}")
        else:
            try:
                self.root.bind('<F9>', lambda e: self._smart_f9_toggle())
            except Exception as e:
                logger.debug(f"F9 kisayol bind hatasi: {e}")

    def toggle_from_hotkey(self):
        """F9 — Akıllı toggle: duruma göre normal veya Teams"""
        self.root.after(0, self._smart_f9_toggle)

    def _smart_f9_toggle(self):
        """F9 akıllı davranış — tek tuşla her şeyi yönet"""
        # 1. Herhangi bir mod aktifse → DURDUR
        if self.teams_running:
            self.stop_teams_mode()
            return
        if self.running:
            self.stop()
            return
        # 2. Hiçbir mod aktif değil → sayfaya göre BAŞLAT
        if self.current_page in ("teams", "teams_settings"):
            self._show_teams_selection()
        else:
            self.start()

    # ==================== BAŞLAT / DURDUR ====================
    def toggle(self):
        if self.running:
            self.stop()
        else:
            if self.settings.get("delayed_start_enabled", False):
                self.start_delayed()
            else:
                self.start()

    def start_delayed(self):
        delay_minutes = self.settings.get("delayed_start_minutes", 5)
        self.delayed_seconds_remaining = delay_minutes * 60
        self.btn.configure(text="⏳  İPTAL", fg_color=COLORS["accent_yellow"], hover_color=COLORS["accent_yellow_hover"])
        self.update_countdown()

    def update_countdown(self):
        if self.delayed_seconds_remaining > 0:
            mins = self.delayed_seconds_remaining // 60
            secs = self.delayed_seconds_remaining % 60
            self.status_info.configure(text=f"⏳ Başlamaya {mins:02d}:{secs:02d}")
            self.delayed_seconds_remaining -= 1
            self.delayed_start_job = self.root.after(1000, self.update_countdown)
        else:
            self.status_info.configure(text="")
            self.start()

    def start(self):
        # Teams moduyla çakışma kontrolü
        if self.teams_running:
            self.stop_teams_mode()

        self._cancel_job("delayed_start_job")
        self.status_info.configure(text="")

        self.running = True
        self.paused_by_user = False
        self.elapsed_seconds = 0
        self.angle = 0
        self.square_step = 0
        self.last_mouse_pos = get_cursor_pos()

        self.btn.configure(text="⏹   DURDUR", fg_color=COLORS["accent_red"], hover_color=COLORS["accent_red_hover"])
        self.status_label.configure(text_color=COLORS["accent_green"])
        self.timer_label.configure(text="Çalışma Süresi: 00:00:00")

        if self.mini_mode and hasattr(self, 'mini_btn_main'):
            self.mini_btn_main.configure(text="⏹", fg_color=COLORS["accent_red"], hover_color=COLORS["accent_red_hover"])
            self.mini_status.configure(text_color=COLORS["accent_green"])

        if self.settings.get("auto_stop_enabled", False):
            stop_ms = self.settings.get("auto_stop_minutes", 60) * 60 * 1000
            self.auto_stop_job = self.root.after(stop_ms, self.stop)

        self.jiggle()
        self.update_timer()
        logger.info("Normal mod baslatildi")

        if self.settings.get("pause_on_user_activity", True):
            self.check_user_activity()

    def stop(self):
        self.running = False
        self.paused_by_user = False
        self.btn.configure(text="▶   BAŞLAT", fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"])
        self.status_label.configure(text_color=COLORS["accent_red"])
        self.status_info.configure(text="")

        if self.mini_mode and hasattr(self, 'mini_btn_main'):
            self.mini_btn_main.configure(text="▶", fg_color=COLORS["accent_green"], hover_color=COLORS["accent_green_hover"])
            self.mini_status.configure(text_color=COLORS["accent_red"])

        for job_name in ["job", "timer_job", "auto_stop_job", "delayed_start_job", "user_check_job"]:
            self._cancel_job(job_name)
        logger.info("Normal mod durduruldu")

    def jiggle(self):
        if not self.running or self.paused_by_user:
            if self.running:
                self.job = self.root.after(500, self.jiggle)
            return

        try:
            x, y = get_cursor_pos()
            distance = self.settings.get("distance", 15)
            pattern = self.settings.get("pattern", "Rastgele")

            if pattern == "Rastgele":
                dx = random.randint(-distance, distance)
                dy = random.randint(-distance, distance)
            elif pattern == "Dairesel":
                self.angle += 15
                if self.angle >= 360:
                    self.angle = 0
                rad = math.radians(self.angle)
                dx = int(math.cos(rad) * distance)
                dy = int(math.sin(rad) * distance)
            elif pattern == "Kare":
                self.square_step += 1
                side = (self.square_step // (distance * 2)) % 4
                if side == 0:
                    dx, dy = 2, 0
                elif side == 1:
                    dx, dy = 0, 2
                elif side == 2:
                    dx, dy = -2, 0
                else:
                    dx, dy = 0, -2

            set_cursor_pos(x + dx, y + dy)
            self.last_mouse_pos = get_cursor_pos()
        except Exception as e:
            logger.error(f"Hareket hatasi: {e}")

        speed = self.settings.get("speed", 50)
        base_delay = 1500 - (speed * 12)
        delay = max(200, base_delay + random.randint(-100, 100))

        self.job = self.root.after(delay, self.jiggle)

    def check_user_activity(self):
        if not self.running:
            return

        if not self.settings.get("pause_on_user_activity", True):
            self.user_check_job = self.root.after(500, self.check_user_activity)
            return

        try:
            current_pos = get_cursor_pos()
            last_pos = self.last_mouse_pos

            dx = abs(current_pos[0] - last_pos[0])
            dy = abs(current_pos[1] - last_pos[1])
            distance = self.settings.get("distance", 15)

            if dx > distance + 10 or dy > distance + 10:
                if not self.paused_by_user:
                    self.paused_by_user = True
                    self.status_info.configure(text="⏸️ Kullanıcı hareketi algılandı")
                    self.status_label.configure(text_color=COLORS["accent_yellow"])
            else:
                if self.paused_by_user:
                    self.paused_by_user = False
                    self.status_info.configure(text="")
                    self.status_label.configure(text_color=COLORS["accent_green"])
        except Exception as e:
            logger.debug(f"Kullanici aktivite kontrolu hatasi: {e}")

        self.user_check_job = self.root.after(500, self.check_user_activity)

    def check_schedule(self):
        if self.settings.get("schedule_enabled", False):
            try:
                now = datetime.now().time()
                start_parts = self.settings.get("schedule_start", "09:00").split(":")
                end_parts = self.settings.get("schedule_end", "18:00").split(":")

                start_time = time(int(start_parts[0]), int(start_parts[1]))
                end_time = time(int(end_parts[0]), int(end_parts[1]))

                in_schedule = start_time <= now <= end_time

                if in_schedule and not self.running:
                    self.start()
                    self.status_info.configure(text="📅 Zamanlanmış başlatma")
                elif not in_schedule and self.running:
                    self.stop()
                    self.status_info.configure(text="📅 Zamanlanmış durdurma")
            except Exception as e:
                logger.error(f"Zamanlama hatasi: {e}")

        self.schedule_job = self.root.after(60000, self.check_schedule)

    def update_timer(self):
        if not self.running:
            return
        self.elapsed_seconds += 1
        hrs = self.elapsed_seconds // 3600
        mins = (self.elapsed_seconds % 3600) // 60
        secs = self.elapsed_seconds % 60
        self.timer_label.configure(text=f"Çalışma Süresi: {hrs:02d}:{mins:02d}:{secs:02d}")
        self.timer_job = self.root.after(1000, self.update_timer)

    # ==================== MİNİ MOD ====================
    def toggle_mini_mode(self):
        if not self.mini_mode:
            self.mini_mode = True
            # Mevcut sayfayı gizle — hangi sayfa aktifse onu kapat
            if self.current_page == "main":
                self.main_frame.pack_forget()
            elif self.current_page == "settings":
                self.settings_frame.pack_forget()
            elif self.current_page == "teams":
                self.teams_frame.pack_forget()
            elif self.current_page == "teams_settings":
                self.teams_settings_frame.pack_forget()
            self.root.geometry("200x60")
            self.root.minsize(200, 60)
            self.root.maxsize(200, 60)

            self.mini_frame = ctk.CTkFrame(self.root, fg_color="transparent")
            self.mini_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Teams veya normal mod kontrolü
            if self.teams_running:
                self.mini_btn_main = ctk.CTkButton(self.mini_frame,
                                                   text="⏹",
                                                   width=50, height=38,
                                                   corner_radius=10,
                                                   font=ctk.CTkFont(size=FONTS["button"]),
                                                   fg_color=COLORS["accent_red"],
                                                   hover_color=COLORS["accent_red_hover"],
                                                   text_color=COLORS["text_dark"],
                                                   command=self.toggle_teams_mode)
                mini_status_color = COLORS["teams_blue"]
            else:
                self.mini_btn_main = ctk.CTkButton(self.mini_frame,
                                                   text="⏹" if self.running else "▶",
                                                   width=50, height=38,
                                                   corner_radius=10,
                                                   font=ctk.CTkFont(size=FONTS["button"]),
                                                   fg_color=COLORS["accent_red"] if self.running else COLORS["accent_green"],
                                                   hover_color=COLORS["accent_red_hover"] if self.running else COLORS["accent_green_hover"],
                                                   text_color=COLORS["text_dark"],
                                                   command=self.toggle)
                mini_status_color = COLORS["accent_green"] if self.running else COLORS["accent_red"]
            self.mini_btn_main.pack(side="left")

            self.mini_status = ctk.CTkLabel(self.mini_frame, text="●",
                                            font=ctk.CTkFont(size=FONTS["button"]),
                                            text_color=mini_status_color)
            self.mini_status.pack(side="left", padx=10)

            mini_expand = ctk.CTkButton(self.mini_frame, text="⬜",
                                        width=50, height=38,
                                        corner_radius=10,
                                        font=ctk.CTkFont(size=FONTS["body"]),
                                        fg_color=COLORS["bg_button"], hover_color=COLORS["bg_button_hover"],
                                        command=self.toggle_mini_mode)
            mini_expand.pack(side="right")
        else:
            self.mini_mode = False
            if hasattr(self, 'mini_frame'):
                self.mini_frame.destroy()
            self.root.geometry("380x400")
            self.root.minsize(380, 400)
            self.root.maxsize(380, 400)
            self.main_frame.pack(fill="both", expand=True)
            self.current_page = "main"

    # ==================== SYSTEM TRAY ====================
    def minimize_to_tray(self):
        if not TRAY_AVAILABLE:
            return

        self.root.withdraw()

        size = 64
        image = Image.new('RGB', (size, size), color='#1a1a2e')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 8, 48, 56], fill='#4ecca3', outline='#eee', width=2)
        draw.line([32, 8, 32, 28], fill='#eee', width=2)

        menu = pystray.Menu(
            pystray.MenuItem("Göster", self.show_from_tray),
            pystray.MenuItem("Başlat/Durdur", self.toggle_from_hotkey),
            pystray.MenuItem("Teams Başlat/Durdur", self.toggle_teams_from_tray),
            pystray.MenuItem("Çıkış", self.quit_from_tray)
        )

        self.tray_icon = pystray.Icon("mouse_jiggler", image, "Mouse Jiggler Pro", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.deiconify)

    def toggle_teams_from_tray(self, icon=None, item=None):
        """Tray'den Teams toggle — seçim ekranı olmadan direkt"""
        self.root.after(0, self._tray_teams_toggle)

    def _tray_teams_toggle(self):
        """Tray'den Teams toggle"""
        if self.teams_running:
            self.stop_teams_mode()
        else:
            self._auto_start_teams()

    def quit_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.on_close)

    # ==================== KAPATMA ====================
    def on_close(self):
        if self.current_page == "settings":
            self.save_current_settings()
        elif self.current_page == "teams_settings":
            self.save_teams_settings()
        self.save_settings()
        self.stop()

        # Canlı izlemeyi durdur
        self._stop_teams_live_scan()

        # Teams modunu durdur
        if self.teams_running:
            self.stop_teams_mode()

        # Kalan job'ları temizle
        for job_name in ["schedule_job", "toast_hide_job"]:
            self._cancel_job(job_name)

        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except Exception as e:
                logger.debug(f"Keyboard unhook hatasi: {e}")

        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception as e:
                logger.debug(f"Tray icon durdurma hatasi: {e}")

        logger.info("Uygulama kapatiliyor...")
        self.root.destroy()
        sys.exit(0)

    def run(self):
        self.root.attributes('-topmost', self.settings.get("always_on_top", False))
        self.root.mainloop()
