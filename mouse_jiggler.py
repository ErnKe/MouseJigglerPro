"""
Mouse Jiggler Pro - Modern ve Gelişmiş
Windows için tam özellikli uygulama
Made by Eren Kekiç
"""

import customtkinter as ctk
import random
import ctypes
import math
import threading
import sys
import json
import os
from datetime import datetime, time

# ===== DPI SCALING FIX =====
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# Opsiyonel kütüphaneler
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

# Windows API
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_cursor_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def set_cursor_pos(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)

# Tema ayarı
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Ayar dosyası yolu
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".mouse_jiggler_settings.json")

class MouseJigglerPro:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Mouse Jiggler Pro")
        
        # Sabit boyut - DPI scaling'e karşı
        self.root.geometry("380x350")
        self.root.minsize(380, 350)
        self.root.maxsize(380, 350)
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
        
        # Hareket deseni için
        self.angle = 0
        self.square_step = 0
        
        # Varsayılan ayarlar
        self.settings = {
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
            "always_on_top": False
        }
        
        # Ayarları yükle
        self.load_settings()
        
        # UI oluştur
        self.setup_main_page()
        self.setup_settings_page()
        self.setup_keyboard_shortcut()
        
        # Ana sayfayı göster
        self.show_main_page()
        
        # Zamanlanmış çalışma kontrolü
        self.check_schedule()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    # ==================== ANA SAYFA ====================
    def setup_main_page(self):
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        
        # ===== BAŞLIK =====
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(20, 0))
        
        title_label = ctk.CTkLabel(header_frame, text="🖱️  Mouse Jiggler Pro",
                                   font=ctk.CTkFont(size=22, weight="bold"))
        title_label.pack(side="left")
        
        self.status_label = ctk.CTkLabel(header_frame, text="●",
                                         font=ctk.CTkFont(size=20),
                                         text_color="#ff6b6b")
        self.status_label.pack(side="right")
        
        # ===== ANA BUTON =====
        self.btn = ctk.CTkButton(self.main_frame, text="▶   BAŞLAT",
                                 font=ctk.CTkFont(size=16, weight="bold"),
                                 height=50, corner_radius=12,
                                 fg_color="#4ecca3", hover_color="#3db892",
                                 text_color="#1a1a2e",
                                 command=self.toggle)
        self.btn.pack(fill="x", padx=25, pady=(20, 10))
        
        # ===== ÇALIŞMA SÜRESİ =====
        self.timer_label = ctk.CTkLabel(self.main_frame, text="Çalışma Süresi: 00:00:00",
                                        font=ctk.CTkFont(size=14),
                                        text_color="#888")
        self.timer_label.pack()
        
        # ===== DURUM BİLGİSİ =====
        self.status_info = ctk.CTkLabel(self.main_frame, text="",
                                        font=ctk.CTkFont(size=13),
                                        text_color="#f9ca24")
        self.status_info.pack(pady=(5, 0))
        
        # ===== KISA YOL BİLGİSİ =====
        shortcut_text = "F9: Başlat / Durdur" if KEYBOARD_AVAILABLE else ""
        shortcut_label = ctk.CTkLabel(self.main_frame, text=shortcut_text,
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      text_color="#4ecca3")
        shortcut_label.pack(pady=(8, 0))
        
        # ===== BUTONLAR =====
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(15, 0))
        
        # Ayarlar butonu
        self.settings_btn = ctk.CTkButton(btn_frame, text="⚙️  Ayarlar",
                                          font=ctk.CTkFont(size=13),
                                          width=100, height=36,
                                          corner_radius=10,
                                          fg_color="#333", hover_color="#444",
                                          command=self.show_settings_page)
        self.settings_btn.pack(side="left")
        
        # Mini mod butonu
        self.mini_btn = ctk.CTkButton(btn_frame, text="🗕  Mini",
                                      font=ctk.CTkFont(size=13),
                                      width=85, height=36,
                                      corner_radius=10,
                                      fg_color="#333", hover_color="#444",
                                      command=self.toggle_mini_mode)
        self.mini_btn.pack(side="left", padx=(12, 0))
        
        # Tray butonu
        if TRAY_AVAILABLE:
            self.tray_btn = ctk.CTkButton(btn_frame, text="📥  Tepsi",
                                          font=ctk.CTkFont(size=13),
                                          width=85, height=36,
                                          corner_radius=10,
                                          fg_color="#333", hover_color="#444",
                                          command=self.minimize_to_tray)
            self.tray_btn.pack(side="left", padx=(12, 0))
        
        # ===== KREDİ =====
        credit = ctk.CTkLabel(self.main_frame, text="Made by Eren Kekiç",
                              font=ctk.CTkFont(size=13, weight="bold"),
                              text_color="#ffffff")
        credit.pack(side="bottom", pady=(15, 20))
    
    # ==================== AYARLAR SAYFASI ====================
    def setup_settings_page(self):
        self.settings_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        
        # ===== ÜST BAR =====
        top_bar = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=25, pady=(15, 10))
        
        back_btn = ctk.CTkButton(top_bar, text="←  Geri",
                                 font=ctk.CTkFont(size=14, weight="bold"),
                                 width=90, height=35,
                                 corner_radius=10,
                                 fg_color="#333", hover_color="#444",
                                 command=self.show_main_page)
        back_btn.pack(side="left")
        
        title = ctk.CTkLabel(top_bar, text="⚙️  Ayarlar",
                            font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(side="left", padx=(15, 0))
        
        # ===== İÇERİK =====
        content = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=(5, 15))
        
        # ----- HAREKET AYARLARI -----
        self.create_section(content, "🎛️  Hareket Ayarları")
        
        # Hız
        speed_frame = ctk.CTkFrame(content, fg_color="transparent")
        speed_frame.pack(fill="x", pady=(8, 6))
        ctk.CTkLabel(speed_frame, text="Hız:", font=ctk.CTkFont(size=13), 
                    width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(speed_frame, text="Yavaş", font=ctk.CTkFont(size=11),
                    text_color="#888").pack(side="left")
        self.speed_slider = ctk.CTkSlider(speed_frame, from_=10, to=100, width=160,
                                          button_color="#4ecca3", button_hover_color="#3db892",
                                          progress_color="#4ecca3")
        self.speed_slider.set(self.settings["speed"])
        self.speed_slider.pack(side="left", padx=10)
        ctk.CTkLabel(speed_frame, text="Hızlı", font=ctk.CTkFont(size=11),
                    text_color="#888").pack(side="left")
        
        # Mesafe
        dist_frame = ctk.CTkFrame(content, fg_color="transparent")
        dist_frame.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(dist_frame, text="Mesafe:", font=ctk.CTkFont(size=13),
                    width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(dist_frame, text="Küçük", font=ctk.CTkFont(size=11),
                    text_color="#888").pack(side="left")
        self.distance_slider = ctk.CTkSlider(dist_frame, from_=5, to=50, width=160,
                                             button_color="#4ecca3", button_hover_color="#3db892",
                                             progress_color="#4ecca3")
        self.distance_slider.set(self.settings["distance"])
        self.distance_slider.pack(side="left", padx=10)
        ctk.CTkLabel(dist_frame, text="Büyük", font=ctk.CTkFont(size=11),
                    text_color="#888").pack(side="left")
        
        # Desen
        pattern_frame = ctk.CTkFrame(content, fg_color="transparent")
        pattern_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(pattern_frame, text="Desen:", font=ctk.CTkFont(size=13),
                    width=80, anchor="w").pack(side="left")
        self.pattern_var = ctk.StringVar(value=self.settings["pattern"])
        self.pattern_menu = ctk.CTkOptionMenu(pattern_frame, variable=self.pattern_var,
                                              values=["Rastgele", "Dairesel", "Kare"],
                                              width=150, height=30,
                                              font=ctk.CTkFont(size=12),
                                              fg_color="#333", button_color="#444",
                                              button_hover_color="#555")
        self.pattern_menu.pack(side="left")
        
        # ----- ZAMANLAMA -----
        self.create_section(content, "⏰  Zamanlama")
        
        # Otomatik durdurma
        auto_frame = ctk.CTkFrame(content, fg_color="transparent")
        auto_frame.pack(fill="x", pady=(8, 4))
        self.auto_stop_var = ctk.BooleanVar(value=self.settings["auto_stop_enabled"])
        ctk.CTkCheckBox(auto_frame, text="Otomatik durdur:",
                       variable=self.auto_stop_var,
                       font=ctk.CTkFont(size=13),
                       checkbox_width=22, checkbox_height=22,
                       fg_color="#4ecca3", hover_color="#3db892").pack(side="left")
        self.auto_stop_entry = ctk.CTkEntry(auto_frame, width=55, height=30,
                                            font=ctk.CTkFont(size=12))
        self.auto_stop_entry.insert(0, str(self.settings["auto_stop_minutes"]))
        self.auto_stop_entry.pack(side="left", padx=10)
        ctk.CTkLabel(auto_frame, text="dk sonra", font=ctk.CTkFont(size=12)).pack(side="left")
        
        # Gecikmeli başlatma
        delay_frame = ctk.CTkFrame(content, fg_color="transparent")
        delay_frame.pack(fill="x", pady=(4, 4))
        self.delayed_var = ctk.BooleanVar(value=self.settings["delayed_start_enabled"])
        ctk.CTkCheckBox(delay_frame, text="Gecikmeli başlat:",
                       variable=self.delayed_var,
                       font=ctk.CTkFont(size=13),
                       checkbox_width=22, checkbox_height=22,
                       fg_color="#4ecca3", hover_color="#3db892").pack(side="left")
        self.delayed_entry = ctk.CTkEntry(delay_frame, width=55, height=30,
                                          font=ctk.CTkFont(size=12))
        self.delayed_entry.insert(0, str(self.settings["delayed_start_minutes"]))
        self.delayed_entry.pack(side="left", padx=10)
        ctk.CTkLabel(delay_frame, text="dk sonra", font=ctk.CTkFont(size=12)).pack(side="left")
        
        # Zamanlanmış
        schedule_frame = ctk.CTkFrame(content, fg_color="transparent")
        schedule_frame.pack(fill="x", pady=(4, 5))
        self.schedule_var = ctk.BooleanVar(value=self.settings["schedule_enabled"])
        ctk.CTkCheckBox(schedule_frame, text="Zamanlanmış:",
                       variable=self.schedule_var,
                       font=ctk.CTkFont(size=13),
                       checkbox_width=22, checkbox_height=22,
                       fg_color="#4ecca3", hover_color="#3db892").pack(side="left")
        self.schedule_start = ctk.CTkEntry(schedule_frame, width=60, height=30,
                                           font=ctk.CTkFont(size=12))
        self.schedule_start.insert(0, self.settings["schedule_start"])
        self.schedule_start.pack(side="left", padx=(10, 5))
        ctk.CTkLabel(schedule_frame, text="-", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.schedule_end = ctk.CTkEntry(schedule_frame, width=60, height=30,
                                         font=ctk.CTkFont(size=12))
        self.schedule_end.insert(0, self.settings["schedule_end"])
        self.schedule_end.pack(side="left", padx=5)
        
        # ----- AKILLI ÖZELLİKLER -----
        self.create_section(content, "⚡  Akıllı Özellikler")
        
        self.pause_var = ctk.BooleanVar(value=self.settings["pause_on_user_activity"])
        ctk.CTkCheckBox(content, text="Kullanıcı mouse'u hareket ettirince duraklat",
                       variable=self.pause_var,
                       font=ctk.CTkFont(size=13),
                       checkbox_width=22, checkbox_height=22,
                       fg_color="#4ecca3", hover_color="#3db892").pack(anchor="w", pady=(8, 4))
        
        self.topmost_var = ctk.BooleanVar(value=self.settings["always_on_top"])
        ctk.CTkCheckBox(content, text="Her zaman üstte",
                       variable=self.topmost_var,
                       font=ctk.CTkFont(size=13),
                       checkbox_width=22, checkbox_height=22,
                       fg_color="#4ecca3", hover_color="#3db892").pack(anchor="w", pady=(0, 15))
    
    def create_section(self, parent, text):
        """Bölüm başlığı"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(12, 0))
        
        label = ctk.CTkLabel(frame, text=text,
                            font=ctk.CTkFont(size=15, weight="bold"),
                            text_color="#4ecca3")
        label.pack(side="left")
        
        separator = ctk.CTkFrame(frame, height=2, fg_color="#444")
        separator.pack(side="left", fill="x", expand=True, padx=(12, 0))
    
    # ==================== SAYFA GEÇİŞLERİ ====================
    def show_main_page(self):
        """Ana sayfayı göster"""
        # Önce ayarları kaydet
        if self.current_page == "settings":
            self.save_current_settings()
        
        self.settings_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.current_page = "main"
        
        # Pencere boyutunu ayarla
        self.root.geometry("380x350")
        self.root.minsize(380, 350)
        self.root.maxsize(380, 350)
    
    def show_settings_page(self):
        """Ayarlar sayfasını göster"""
        self.main_frame.pack_forget()
        self.settings_frame.pack(fill="both", expand=True)
        self.current_page = "settings"
        
        # Ayarlar için daha büyük pencere
        self.root.geometry("420x530")
        self.root.minsize(420, 530)
        self.root.maxsize(420, 530)
    
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
    
    def save_settings(self):
        """Ayarları dosyaya kaydet"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ayarlar kaydedilemedi: {e}")
    
    def load_settings(self):
        """Ayarları dosyadan yükle"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
        except Exception as e:
            print(f"Ayarlar yüklenemedi: {e}")
    
    # ==================== KLAVYE KISAYOLU ====================
    def setup_keyboard_shortcut(self):
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.add_hotkey('F9', self.toggle_from_hotkey)
            except Exception as e:
                print(f"Kısayol ayarlanamadı: {e}")
    
    def toggle_from_hotkey(self):
        self.root.after(0, self.toggle)
    
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
        self.btn.configure(text="⏳  İPTAL", fg_color="#f9ca24", hover_color="#d4a820")
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
        if self.delayed_start_job:
            self.root.after_cancel(self.delayed_start_job)
            self.delayed_start_job = None
        self.status_info.configure(text="")
        
        self.running = True
        self.paused_by_user = False
        self.elapsed_seconds = 0
        self.angle = 0
        self.square_step = 0
        self.last_mouse_pos = get_cursor_pos()
        
        self.btn.configure(text="⏹   DURDUR", fg_color="#ff6b6b", hover_color="#e55a5a")
        self.status_label.configure(text_color="#4ecca3")
        self.timer_label.configure(text="Çalışma Süresi: 00:00:00")
        
        if self.mini_mode and hasattr(self, 'mini_btn_main'):
            self.mini_btn_main.configure(text="⏹", fg_color="#ff6b6b", hover_color="#e55a5a")
            self.mini_status.configure(text_color="#4ecca3")
        
        if self.settings.get("auto_stop_enabled", False):
            stop_ms = self.settings.get("auto_stop_minutes", 60) * 60 * 1000
            self.auto_stop_job = self.root.after(stop_ms, self.stop)
        
        self.jiggle()
        self.update_timer()
        
        if self.settings.get("pause_on_user_activity", True):
            self.check_user_activity()
    
    def stop(self):
        self.running = False
        self.paused_by_user = False
        self.btn.configure(text="▶   BAŞLAT", fg_color="#4ecca3", hover_color="#3db892")
        self.status_label.configure(text_color="#ff6b6b")
        self.status_info.configure(text="")
        
        if self.mini_mode and hasattr(self, 'mini_btn_main'):
            self.mini_btn_main.configure(text="▶", fg_color="#4ecca3", hover_color="#3db892")
            self.mini_status.configure(text_color="#ff6b6b")
        
        for job in [self.job, self.timer_job, self.auto_stop_job, 
                    self.delayed_start_job, self.user_check_job]:
            if job:
                try:
                    self.root.after_cancel(job)
                except:
                    pass
        
        self.job = None
        self.timer_job = None
        self.auto_stop_job = None
        self.delayed_start_job = None
        self.user_check_job = None
    
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
            print(f"Hareket hatası: {e}")
        
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
                    self.status_label.configure(text_color="#f9ca24")
            else:
                if self.paused_by_user:
                    self.paused_by_user = False
                    self.status_info.configure(text="")
                    self.status_label.configure(text_color="#4ecca3")
        except:
            pass
        
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
                print(f"Zamanlama hatası: {e}")
        
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
            self.main_frame.pack_forget()
            self.root.geometry("180x60")
            self.root.minsize(180, 60)
            self.root.maxsize(180, 60)
            
            self.mini_frame = ctk.CTkFrame(self.root, fg_color="transparent")
            self.mini_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            self.mini_btn_main = ctk.CTkButton(self.mini_frame, 
                                               text="⏹" if self.running else "▶",
                                               width=50, height=38,
                                               corner_radius=10,
                                               font=ctk.CTkFont(size=16),
                                               fg_color="#ff6b6b" if self.running else "#4ecca3",
                                               hover_color="#e55a5a" if self.running else "#3db892",
                                               text_color="#1a1a2e",
                                               command=self.toggle)
            self.mini_btn_main.pack(side="left")
            
            self.mini_status = ctk.CTkLabel(self.mini_frame, text="●",
                                            font=ctk.CTkFont(size=16),
                                            text_color="#4ecca3" if self.running else "#ff6b6b")
            self.mini_status.pack(side="left", padx=10)
            
            mini_expand = ctk.CTkButton(self.mini_frame, text="⬜", 
                                        width=50, height=38,
                                        corner_radius=10,
                                        font=ctk.CTkFont(size=14),
                                        fg_color="#333", hover_color="#444",
                                        command=self.toggle_mini_mode)
            mini_expand.pack(side="right")
        else:
            self.mini_mode = False
            if hasattr(self, 'mini_frame'):
                self.mini_frame.destroy()
            self.root.geometry("380x350")
            self.root.minsize(380, 350)
            self.root.maxsize(380, 350)
            self.main_frame.pack(fill="both", expand=True)
    
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
            pystray.MenuItem("Çıkış", self.quit_from_tray)
        )
        
        self.tray_icon = pystray.Icon("mouse_jiggler", image, "Mouse Jiggler Pro", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.deiconify)
    
    def quit_from_tray(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.on_close)
    
    # ==================== KAPATMA ====================
    def on_close(self):
        if self.current_page == "settings":
            self.save_current_settings()
        self.save_settings()
        self.stop()
        
        if self.schedule_job:
            try:
                self.root.after_cancel(self.schedule_job)
            except:
                pass
        
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except:
                pass
        
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        self.root.attributes('-topmost', self.settings.get("always_on_top", False))
        self.root.mainloop()

if __name__ == "__main__":
    app = MouseJigglerPro()
    app.run()