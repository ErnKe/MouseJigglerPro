# 🖱️ Mouse Jiggler Pro

**Windows için modern ve gelişmiş Mouse Jiggler uygulaması — Teams desteği ile!**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.8+-yellow.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

---

## 📖 Hakkında

Mouse Jiggler Pro, bilgisayarınızın uyku moduna geçmesini veya ekran koruyucunun aktif olmasını engellemek için farenizi otomatik olarak hareket ettiren modern bir Windows uygulamasıdır.

> **Not:** Teams tespiti ve multi-monitor özellikleri şu an sadece Windows'ta desteklenmektedir. Mac/Linux'ta temel mouse jiggler özelliği pyautogui ile çalışır.

**v2.0** ile birlikte **Microsoft Teams entegrasyonu** eklendi — Teams uygulamanızı otomatik tespit eder, doğru monitöre odaklanır ve aktif durumunuzu korur.

## ✨ Özellikler

| Özellik | Açıklama |
|---------|----------|
| 🎨 **Modern Arayüz** | CustomTkinter ile karanlık tema |
| 🔄 **3 Hareket Deseni** | Rastgele, Dairesel, Kare |
| 🟢 **Teams Modu** | Microsoft Teams'e özel hareket motoru |
| 🔍 **Teams Tespiti** | Masaüstü ve browser Teams otomatik algılama |
| 🖥️ **Multi-Monitor** | Çoklu monitör desteği, Teams otomatik takip |
| ⏱️ **Esnek Zamanlama** | Otomatik durdurma, gecikmeli başlatma, zamanlanmış çalışma |
| ⏸️ **Akıllı Duraklatma** | Kullanıcı mouse'u hareket ettirince otomatik duraklatma |
| 🔔 **Bildirimler** | Teams kapanma/açılma bildirimleri |
| 🗕 **Mini Mod** | Kompakt görünüm (normal + Teams modu desteği) |
| 📥 **System Tray** | Arka planda çalışma + Teams kontrolü |
| ⌨️ **Klavye Kısayolları** | F9 normal mod, F10 Teams modu |
| 💾 **Ayar Kaydetme** | Tüm ayarlar otomatik kaydedilir |

---

## 🚀 Kurulum

### Yöntem 1: Kolay Başlatma (Önerilen)

1. **Python 3.8+** yüklü olmalıdır ([Python İndir](https://www.python.org/downloads/))
   > Kurulum sırasında **"Add Python to PATH"** seçeneğini işaretleyin!
2. Projeyi indirin veya klonlayın:
   ```
   git clone https://github.com/ErnKe/MouseJigglerPro.git
   ```
3. `run.bat` dosyasına çift tıklayın — **Hepsi bu kadar!**
   > İlk çalıştırmada gerekli kütüphaneler otomatik yüklenir.

### Yöntem 2: Manuel Kurulum

```bash
pip install -r requirements.txt
python mouse_jiggler.py
```

---

## 📦 Gereksinimler

### Zorunlu
* **Python 3.8+**
* **customtkinter** — Modern UI framework

### Opsiyonel (Ekstra özellikler için)
* **psutil** — Teams process tespiti
* **pystray** + **Pillow** — System tray desteği
* **keyboard** — Klavye kısayolları (F9/F10)
* **pyautogui** — Teams sekme geçişi ve cross-platform mouse kontrolü

---

## 🎮 Kullanım

### Temel Kullanım
1. **BAŞLAT** butonuna tıklayın veya **F9** tuşuna basın
2. Mouse otomatik olarak hareket etmeye başlayacak
3. Durdurmak için **DURDUR** veya tekrar **F9**

### 🟢 Teams Modu

1. Ana ekrandaki **Teams Modu** butonuna tıklayın
2. Teams otomatik ve canlı olarak tespit edilir (3 saniyede bir taranır)
3. **TEAMS BAŞLAT** butonuna basın — türünü seçin:
   - **🌐 Browser Teams** — Chrome/Edge'deki Teams
   - **🖥️ Masaüstü Teams** — Windows Teams uygulaması
4. Seçiminize göre Teams otomatik açılır ve mouse hareketi başlar
5. Teams penceresi kapanırsa bildirim alırsınız
6. **F9** ile hızlıca başlatın (Teams sayfasındayken Teams modu, diğer sayfalarda normal mod)

**Teams Ayarları:**
- **Varsayılan Tarayıcı**: Otomatik, Chrome, Edge, Firefox, Brave veya Opera
- **Hareket Aralığı**: Sürekli, 10sn, 30sn, 1dk, 5dk, 10dk, 20dk, 30dk veya özel
- **Hareket Tipi**: Minimal (1-3px), Küçük (3-8px), Orta (8-15px)
- **Otomatik Çekme**: Mouse Teams dışına çıkarsa geri çeker
- **Pencere Takibi**: Teams pencere değişikliklerini izler
- **Bildirimler**: Teams kapanma/açılma bildirimleri

### Ayarlar (Normal Mod)
⚙️ **Ayarlar** butonuna tıklayarak özelleştirebilirsiniz:
- **Hız & Mesafe**: Hareket sıklığı ve mesafesi
- **Desen**: Rastgele, Dairesel veya Kare
- **Zamanlama**: Otomatik durdurma, gecikmeli başlatma, zamanlanmış çalışma
- **Akıllı Özellikler**: Kullanıcı algılama, her zaman üstte

### Mini Mod
🗕 **Mini** butonuyla kompakt moda geçin — normal ve Teams modu için çalışır.

### System Tray
📥 **Tepsi** butonuyla sistem tepsisine küçültün. Sağ tıklayarak:
- Göster
- Başlat/Durdur (Normal)
- Teams Başlat/Durdur
- Çıkış

---

## ⌨️ Klavye Kısayolları

| Kısayol | İşlev |
|---------|-------|
| **F9** | Akıllı Başlat / Durdur — normal sayfada normal mod, Teams sayfasında Teams modu |

---

## 📁 Dosya Yapısı

```
MouseJigglerPro/
├── mouse_jiggler.py      # Ana uygulama
├── requirements.txt      # Python bağımlılıkları
├── run.bat               # Başlatma scripti
├── README.md             # Bu dosya
├── LICENSE               # GPL-3.0 Lisansı
└── screenshots/          # Ekran görüntüleri
    ├── screenshot.png
    └── screenshot2.png
```

---

## 🔧 Ayar Dosyası

Ayarlarınız otomatik olarak şu konumda saklanır:
```
%USERPROFILE%\.mouse_jiggler_settings.json
```

---

## 🐛 Sorun Giderme

### "Python bulunamadı" hatası
- Python'un yüklü olduğundan emin olun
- Python'u PATH'e eklediğinizden emin olun

### Teams tespit edilemiyor (masaüstü)
- Teams'in açık olduğundan emin olun
- `pip install psutil` ile process tespitini aktifleştirin
- Uygulama içi "Yeniden Tara" butonunu deneyin

### Teams tespit edilemiyor (browser)
- Teams'in browser'da **açık bir sekmede** olduğundan emin olun
- Edge veya Chrome kullanıyorsanız Teams sekmesi arka planda olabilir — sorun değil, tespit edilir
- "Yeniden Tara" butonunu deneyin
- psutil yüklü ise tespit daha güvenilir olur: `pip install psutil`

### Teams farklı sekmede iken tespit edilemiyor
- "Yeniden Tara" butonuna tıklayın — browser otomatik öne getirilir
- Teams sekmesine geçin ve tekrar "Yeniden Tara" yapın
- psutil yüklüyse browser process'i otomatik tespit edilir

### Klavye kısayolları çalışmıyor
```
pip install keyboard
```

### Teams sekmesine otomatik geçiş çalışmıyor
```
pip install pyautogui
```
- pyautogui yüklüyse: Ctrl+L + URL yöntemiyle Teams sekmesi açılır
- pyautogui yüklü değilse: browser doğrudan çalıştırılarak Teams açılır
- Chrome veya Edge kullanmanız önerilir

### System tray çalışmıyor
```
pip install pystray pillow
```

---

## 📄 Lisans

Bu proje **GNU Genel Kamu Lisansı v3.0** altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

---

## 👨‍💻 Geliştirici

**Eren Kekiç**

---

**Made by Eren Kekiç**
