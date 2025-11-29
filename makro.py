import time
import threading
import random
import os
import json
import tkinter as tk
from tkinter import messagebox, ttk as standard_ttk 
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Listener as KeyboardListener, Key, KeyCode
import sys


try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
except ImportError:
    print("ttkbootstrap kuruluyor...")
    try:
        os.system("pip install ttkbootstrap")
        import ttkbootstrap as ttk
        from ttkbootstrap.constants import *
    except ImportError:
        print("Hata: ttkbootstrap kurulamadı. Lütfen manuel olarak 'pip install ttkbootstrap' komutunu çalıştırın.")
        sys.exit(1)


DEFAULT_CPS = 50.0 
TEMEL_GECIKME = 1.0 / DEFAULT_CPS 
PRESS_RELEASE_GECIKME = 0.0001
TUS_DOSYA = "byforgeon_macro_config.json"
DEFAULT_RANDOMNESS_RATIO = 0.10 
MAX_CPS = 70.0
MIN_CPS = 1.0 
MAX_JITTER_PERCENT = 30.0


RENK_ARKA_PLAN = "#1c1c1c"
RENK_VURGU = "#00cc00"
RENK_HATA = "#ff4444"
RENK_BILGI = "#aaaaaa"

DEFAULT_TUS_ATAMALARI = {
    "sol_tik": "1",
    "sag_tik": "2",
    "cikis": "f10"
}
print("\n[BYFORGEON] Sistem Başlatılıyor...")

def load_tuslar():
    if os.path.exists(TUS_DOSYA):
        try:
            with open(TUS_DOSYA, "r") as f:
                data = json.load(f)
                for key, default_val in DEFAULT_TUS_ATAMALARI.items():
                    if key not in data:
                        data[key] = default_val
                return data
        except (json.JSONDecodeError, IOError):
            print("[UYARI] Konfigürasyon dosyası bozuk. Varsayılanlar kullanılıyor.")
            return DEFAULT_TUS_ATAMALARI.copy()
    print("[BILGI] Mevcut konfigürasyon bulunamadı. Yeni dosya oluşturuluyor.")
    return DEFAULT_TUS_ATAMALARI.copy()

def save_tuslar(tuslar):
    with open(TUS_DOSYA, "w") as f:
        json.dump(tuslar, f)
    print(f"[KONFIG] Kısayol tuşları {TUS_DOSYA} dosyasına kaydedildi.")

TUS_ATAMALARI = load_tuslar()

def key_from_string(s):
    s = s.lower()
    if len(s) == 1 and s.isalnum():
        return KeyCode.from_char(s)
    try:
        return getattr(Key, s)
    except AttributeError:
        return None

def cps_to_rpm(cps):
    return round(cps * 60, 0)

def delay_to_cps(delay):
    return 1.0 / delay if delay > 0 else 0.0

# AutoClicker
class AutoClicker(threading.Thread):
    def __init__(self, isim, tus, initial_delay, gui_callback=None):
        super().__init__(daemon=True)
        self.temel_gecikme = initial_delay
        self.press_release_gecikme = PRESS_RELEASE_GECIKME
        self.rastgelelik_orani = DEFAULT_RANDOMNESS_RATIO
        self.tus = tus
        self.isim = isim
        self.calisiyor = False
        self.mouse = MouseController()
        self._stop_event = threading.Event()
        self.gui_callback = gui_callback

    def toggle(self):
        self.calisiyor = not self.calisiyor
        if self.gui_callback:
            self.gui_callback(self.isim, self.calisiyor)
            
    def set_delay(self, delay):
        self.temel_gecikme = delay

    def set_randomness(self, oran):
        self.rastgelelik_orani = oran

    def run(self):
        while not self._stop_event.is_set():
            if self.calisiyor:
                try:
                    self.mouse.press(self.tus)
                    time.sleep(self.press_release_gecikme)
                    self.mouse.release(self.tus)
                    
                    sapma = self.temel_gecikme * self.rastgelelik_orani
                    min_delay = self.temel_gecikme - sapma
                    max_delay = self.temel_gecikme + sapma
                    rastgele_gecikme = random.uniform(max(0, min_delay), max_delay)
                    
                    self._stop_event.wait(max(0, rastgele_gecikme))
                except Exception as e:
                    print(f"[HATA] {self.isim} makro döngüsü hatası: {e}")
                    self.calisiyor = False 
                    if self.gui_callback:
                        self.gui_callback(self.isim, self.calisiyor)
                        self.gui_callback("HATA_KRITIK", f"{self.isim} durduruldu: {str(e)}")
                
            else:
                self._stop_event.wait(0.01)

    def stop(self):
        self.calisiyor = False
        self._stop_event.set()

#  MacroManager 
class MacroManager:
    def __init__(self, gui_callback=None):
        self.initial_delay = TEMEL_GECIKME
        self.sol = AutoClicker("LMB (Sol Tık)", Button.left, self.initial_delay, gui_callback)
        self.sag = AutoClicker("RMB (Sağ Tık)", Button.right, self.initial_delay, gui_callback)
        self.threads = [self.sol, self.sag]
        self.gui_callback = gui_callback

    def start_all(self):
        for t in self.threads:
            t.start()
        print("[BASLAT] Tüm makro iş parçacıkları başlatıldı.")

    def stop_all(self):
        for t in self.threads:
            t.stop()
        print("[DURDUR] Tüm makro iş parçacıkları sonlandırıldı.")

    def toggle_sol(self):
        self.sol.toggle()
        print(f"[EYLEM] LMB Makro Durumu: {'AÇIK' if self.sol.calisiyor else 'KAPALI'}.")

    def toggle_sag(self):
        self.sag.toggle()
        print(f"[EYLEM] RMB Makro Durumu: {'AÇIK' if self.sag.calisiyor else 'KAPALI'}.")

    def set_cps(self, yeni_cps):
        delay = 1.0 / yeni_cps
        for t in self.threads:
            t.set_delay(delay)
        print(f"[AYAR] CPS {yeni_cps:.1f} ({cps_to_rpm(yeni_cps):.0f} RPM) olarak ayarlandı.")
            
    def set_randomness_ratio(self, oran):
        for t in self.threads:
            t.set_randomness(oran)
        print(f"[AYAR] Titreşim Oranı {oran*100:.1f}% olarak ayarlandı.")

    def on_press(self, key):
        key_sol = key_from_string(TUS_ATAMALARI["sol_tik"])
        key_sag = key_from_string(TUS_ATAMALARI["sag_tik"])
        key_cikis = key_from_string(TUS_ATAMALARI["cikis"])
        
        if key == key_sol:
            self.toggle_sol()
        elif key == key_sag:
            self.toggle_sag()
        elif key == key_cikis:
            print("[SONLANDIR] Çıkış kısayolu algılandı. Sistem kapatılıyor.")
            return False 

# GUI 
class MacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BYFORGEON | GELİŞMİŞ MAKRO KONTROL PANELİ (v3.1)")
        self.root.geometry("600x530") 
        self.root.resizable(False, False)
        
        # Tema ve Stil Ayarları (Siyah ve Yeşil)
        self.style = ttk.Style(theme="darkly") 
        self.ozel_stil_yapilandir()
        
        self.frame = ttk.Frame(root, padding=10)
        self.frame.pack(fill=BOTH, expand=True)

        self.manager = MacroManager(self.update_gui)
        self.listening_for_key = None 
        
        self._setup_header()
        self._setup_notebook()
        self._setup_control_tab() # log_text burada oluşturulur
        self._setup_settings_tab()
        self._setup_keybinds_tab()
        self._setup_footer()

        self.manager.start_all()
        self.write_log("BYFORGEON Sistem Kontrolörü Çevrimiçi. Komut Bekleniyor.", tag="init")
        threading.Thread(target=self.klavye_dinle, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.kapat)
        print("[HAZIR] GUI yüklendi ve sistem çevrimiçi.")

    def ozel_stil_yapilandir(self):
        
        self.style.configure("TFrame", background=RENK_ARKA_PLAN)
        self.style.configure("TLabel", background=RENK_ARKA_PLAN, foreground=RENK_VURGU, font=("Consolas", 10))
        
       
        self.style.configure("TNotebook", background=RENK_ARKA_PLAN, borderwidth=0)
        self.style.map("TNotebook.Tab", background=[("selected", RENK_VURGU), ("!selected", "#333333")],
                                       foreground=[("selected", "black"), ("!selected", RENK_BILGI)])
                                       
       
        self.style.configure("Ozel.Yesil.TButton", background=RENK_VURGU, foreground="black", font=("Consolas", 10, "bold"), borderwidth=0)
        self.style.map("Ozel.Yesil.TButton", background=[("active", "#00ff00")])
        
      
        self.style.configure("Tehlike.TButton", background=RENK_HATA, foreground="white", font=("Consolas", 10, "bold"), borderwidth=0)
        self.style.map("Tehlike.TButton", background=[("active", "#ff6666")])
        
      
        self.style.configure("TEntry", fieldbackground="#333333", foreground=RENK_VURGU, insertcolor=RENK_VURGU, borderwidth=1, relief="solid")
        self.style.configure("TSpinbox", fieldbackground="#333333", foreground=RENK_VURGU, insertcolor=RENK_VURGU, borderwidth=1, relief="solid")
        self.style.configure("TScale", background=RENK_ARKA_PLAN, troughcolor="#333333", borderwidth=0)

    def _setup_header(self):
        header_frame = ttk.Frame(self.frame, padding=10, style='TFrame')
        header_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(header_frame, text="BYFORGEON CYBER SYSTEMS", font=("Arial", 16, "bold"), foreground=RENK_VURGU, background=RENK_ARKA_PLAN).pack(side=LEFT)
        ttk.Label(header_frame, text="SADE & GÜVENLİ", font=("Arial", 10), foreground=RENK_BILGI, background=RENK_ARKA_PLAN).pack(side=RIGHT, padx=10)

    def _setup_notebook(self):
        self.notebook = standard_ttk.Notebook(self.frame)
        self.notebook.pack(pady=5, padx=5, fill=BOTH, expand=True)

        self.control_frame = ttk.Frame(self.notebook, padding=15)
        self.settings_frame = ttk.Frame(self.notebook, padding=15)
        self.keybinds_frame = ttk.Frame(self.notebook, padding=15)

        self.notebook.add(self.control_frame, text="1. KONTROL / DURUM", padding=10)
        self.notebook.add(self.settings_frame, text="2. PERFORMANS AYARI", padding=10)
        self.notebook.add(self.keybinds_frame, text="3. KISAYOL TUŞLARI", padding=10)

   
    def _setup_control_tab(self):
        
        ttk.Label(self.control_frame, text="MAKRO SİSTEM DURUMU", font=("Consolas", 14, "bold"), foreground=RENK_VURGU).pack(pady=(0, 15))
        
        # Sistem Konsolu
        ttk.Label(self.control_frame, text="[SİSTEM KONSOL ÇIKTISI]", font=("Consolas", 10, "bold"), foreground=RENK_VURGU).pack(pady=(5, 5), anchor="w")
        self.log_text = tk.Text(self.control_frame, height=7, state=tk.DISABLED, wrap=tk.WORD, bg="#000000", fg=RENK_VURGU, font=("Consolas", 9), relief=tk.FLAT, insertbackground=RENK_VURGU)
        self.log_text.pack(fill=X, padx=10)
        
        # Durum Çerçevesi
        status_container = ttk.Frame(self.control_frame, padding=15, relief=SOLID, borderwidth=1, style='TFrame')
        status_container.pack(fill=X, pady=15)

        # Sol Tık
        ttk.Label(status_container, text="SOL TIK (LMB):", font=("Consolas", 12)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.status_sol_led = ttk.Label(status_container, text="KAPALI", font=("Consolas", 12, "bold"), foreground=RENK_HATA, background=RENK_ARKA_PLAN)
        self.status_sol_led.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(status_container, text=f"AÇ/KAPA [{TUS_ATAMALARI['sol_tik'].upper()}]", style="Ozel.Yesil.TButton", command=self.manager.toggle_sol).grid(row=0, column=2, sticky="e", padx=10, pady=5)

        # Sağ Tık
        ttk.Label(status_container, text="SAĞ TIK (RMB):", font=("Consolas", 12)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.status_sag_led = ttk.Label(status_container, text="KAPALI", font=("Consolas", 12, "bold"), foreground=RENK_HATA, background=RENK_ARKA_PLAN)
        self.status_sag_led.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(status_container, text=f"AÇ/KAPA [{TUS_ATAMALARI['sag_tik'].upper()}]", style="Ozel.Yesil.TButton", command=self.manager.toggle_sag).grid(row=1, column=2, sticky="e", padx=10, pady=5)
        
        status_container.grid_columnconfigure(0, weight=1)

        # Warm-up
        ttk.Label(self.control_frame, text="SİSTEM BAŞLANGIÇ İŞLEMİ:", font=("Consolas", 10, "bold"), foreground=RENK_BILGI).pack(pady=(15, 5), anchor="w")
        self.progress_bar = ttk.Progressbar(self.control_frame, orient=HORIZONTAL, length=400, mode='determinate', bootstyle="success")
        self.progress_bar.pack(fill=X, padx=10)
        self.simulate_warmup()

    def simulate_warmup(self):
        self.progress_bar['value'] = 0
        self.root.update_idletasks()
        for i in range(1, 101, 5):
            self.progress_bar['value'] = i
            self.root.update_idletasks()
            time.sleep(0.02)
        self.write_log("Sistem ön yüklemesi tamamlandı. Tüm modüller hazır.", tag="info")

    # AYARLAR
    def _setup_settings_tab(self):
        
        ttk.Label(self.settings_frame, text="PERFORMANS PARAMETRELERİ", font=("Consolas", 14, "bold"), foreground=RENK_VURGU).pack(pady=(0, 20))
        
        # RPM 
        ttk.Label(self.settings_frame, text="1. DAKİKADAKİ ATIM ORANI (RPM) [Tık/Dak]", font=("Consolas", 11)).pack(pady=(5, 5), anchor="w")
        
        rpm_control_frame = ttk.Frame(self.settings_frame)
        rpm_control_frame.pack(fill=X, pady=5)
        
        initial_cps = delay_to_cps(TEMEL_GECIKME)
        
        self.cps_slider = ttk.Scale(rpm_control_frame, from_=MIN_CPS, to=MAX_CPS, orient="horizontal", command=self.update_cps_from_slider, bootstyle="info")
        self.cps_slider.set(initial_cps)
        self.cps_slider.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        self.cps_entry = ttk.Spinbox(rpm_control_frame, from_=MIN_CPS, to=MAX_CPS, increment=1.0, width=5, justify='center', command=self.update_cps_from_entry, font=("Consolas", 11, "bold"))
        self.cps_entry.set(f"{initial_cps:.1f}")
        self.cps_entry.pack(side=RIGHT, padx=(0, 5))
        
        self.cps_label = ttk.Label(rpm_control_frame, text=f"{cps_to_rpm(initial_cps):.0f} RPM ({initial_cps:.1f} CPS)", width=20, anchor="e", font=("Consolas", 11, "bold"))
        self.cps_label.pack(side=RIGHT)
        
        # Jitter
        ttk.Separator(self.settings_frame, orient=HORIZONTAL, style="TVSeparator").pack(fill=X, pady=20)
        ttk.Label(self.settings_frame, text="2. TİTREŞİM ORANI (JITTER) [Rastgelelik %]", font=("Consolas", 11)).pack(pady=(5, 5), anchor="w")
        
        jitter_control_frame = ttk.Frame(self.settings_frame)
        jitter_control_frame.pack(fill=X, pady=5)
        initial_rand_percent = DEFAULT_RANDOMNESS_RATIO * 100
        
        self.rand_slider = ttk.Scale(jitter_control_frame, from_=0, to=MAX_JITTER_PERCENT, orient="horizontal", command=self.update_randomness_from_slider, bootstyle="warning")
        self.rand_slider.set(initial_rand_percent)
        self.rand_slider.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        self.rand_entry = ttk.Spinbox(jitter_control_frame, from_=0, to=MAX_JITTER_PERCENT, increment=1.0, width=5, justify='center', command=self.update_randomness_from_entry, font=("Consolas", 11, "bold"))
        self.rand_entry.set(f"{initial_rand_percent:.0f}")
        self.rand_entry.pack(side=RIGHT, padx=(0, 5))
        
        self.rand_label = ttk.Label(jitter_control_frame, text=f"Titreşim: %{initial_rand_percent:.0f}", width=15, anchor="e", font=("Consolas", 11, "bold"))
        self.rand_label.pack(side=RIGHT)

    # TUŞ ATAMALARI
    def _setup_keybinds_tab(self):
        ttk.Label(self.keybinds_frame, text="KISAYOL TUŞU KONFİGÜRASYONU", font=("Consolas", 14, "bold"), foreground=RENK_VURGU).pack(pady=(0, 20))
        
        key_frame = ttk.Frame(self.keybinds_frame, padding=10, relief=SOLID, borderwidth=1)
        key_frame.pack(pady=10)
        
        fields = [
            ("LMB Toggle (Sol Tık):", "sol_tik"),
            ("RMB Toggle (Sağ Tık):", "sag_tik"),
            ("Sistem Kapatma (Çıkış):", "cikis")
        ]
        
        self.entry_fields = {}
        for i, (label_text, key_name) in enumerate(fields):
            ttk.Label(key_frame, text=label_text, anchor="w", width=25, font=("Consolas", 10)).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            
            entry = ttk.Entry(key_frame, width=8, justify='center', font=("Consolas", 10), state="readonly")
            entry.insert(0, TUS_ATAMALARI[key_name].upper())
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entry_fields[key_name] = entry
            
            listen_button = ttk.Button(key_frame, text="DİNLE", style="Ozel.Yesil.TButton", command=lambda kn=key_name, ent=entry: self.start_key_listener(kn, ent))
            listen_button.grid(row=i, column=2, padx=5, pady=5)
            self.entry_fields[f"{key_name}_button"] = listen_button 
            
            self.entry_fields[f"{key_name}_status"] = ttk.Label(key_frame, text=f"Aktif: {TUS_ATAMALARI[key_name].upper()}", font=("Consolas", 9, "bold"), foreground=RENK_VURGU)
            self.entry_fields[f"{key_name}_status"].grid(row=i, column=3, padx=10, pady=5, sticky="w")
        
        ttk.Button(self.keybinds_frame, text="KONFİGÜRASYONU KAYDET VE UYGULA", style="Ozel.Yesil.TButton", command=self.kaydet_tuslar_to_file).pack(pady=(20, 5))
        
    # -ALT BÖLÜM -
    def _setup_footer(self):
        footer_frame = ttk.Frame(self.frame, padding=(0, 5))
        footer_frame.pack(side=BOTTOM, fill=X, pady=(10, 0))
        
        ttk.Label(footer_frame, text="Byforgeon Ekibi Tarafından Geliştirilmiştir | v3.1", font=("Consolas", 9, "italic"), foreground=RENK_VURGU, background=RENK_ARKA_PLAN).pack(side=LEFT)
        self.cikis_button = ttk.Button(footer_frame, text=f"SİSTEMİ KAPAT [{TUS_ATAMALARI['cikis'].upper()}]", style="Tehlike.TButton", command=self.kapat)
        self.cikis_button.pack(side=RIGHT)

    
    def update_cps_from_slider(self, value):
        try:
            yeni_cps = float(value)
            self.cps_entry.set(f"{yeni_cps:.1f}")
            self.manager.set_cps(yeni_cps)
            self.cps_label.config(text=f"{cps_to_rpm(yeni_cps):.0f} RPM ({yeni_cps:.1f} CPS)")
        except ValueError:
            pass
            
    def update_cps_from_entry(self):
        try:
            yeni_cps = float(self.cps_entry.get())
            if MIN_CPS <= yeni_cps <= MAX_CPS:
                self.cps_slider.set(yeni_cps)
                self.manager.set_cps(yeni_cps)
                self.cps_label.config(text=f"{cps_to_rpm(yeni_cps):.0f} RPM ({yeni_cps:.1f} CPS)")
                self.write_log(f"RPM/CPS değeri manuel olarak {yeni_cps:.1f} CPS'e ayarlandı.")
            else:
                self.write_log(f"Geçersiz CPS değeri: {yeni_cps}. Aralık {MIN_CPS}-{MAX_CPS} olmalı.", tag="error")
                self.cps_entry.set(f"{delay_to_cps(self.manager.sol.temel_gecikme):.1f}") 
        except ValueError:
            self.write_log("CPS için geçersiz giriş. Lütfen bir sayı girin.", tag="error")
            self.cps_entry.set(f"{delay_to_cps(self.manager.sol.temel_gecikme):.1f}")
            
    def update_randomness_from_slider(self, value):
        try:
            yeni_oran_yuzde = float(value)
            self.rand_entry.set(f"{yeni_oran_yuzde:.0f}")
            yeni_oran = yeni_oran_yuzde / 100
            self.manager.set_randomness_ratio(yeni_oran)
            self.rand_label.config(text=f"Titreşim: %{yeni_oran_yuzde:.0f}")
        except ValueError:
            pass
            
    def update_randomness_from_entry(self):
        try:
            yeni_oran_yuzde = float(self.rand_entry.get())
            if 0 <= yeni_oran_yuzde <= MAX_JITTER_PERCENT:
                self.rand_slider.set(yeni_oran_yuzde)
                yeni_oran = yeni_oran_yuzde / 100
                self.manager.set_randomness_ratio(yeni_oran)
                self.rand_label.config(text=f"Titreşim: %{yeni_oran_yuzde:.0f}")
                self.write_log(f"Titreşim manuel olarak %{yeni_oran_yuzde:.0f}'e ayarlandı.")
            else:
                self.write_log(f"Geçersiz Titreşim değeri: {yeni_oran_yuzde}. Aralık 0-{MAX_JITTER_PERCENT} olmalı.", tag="error")
                self.rand_entry.set(f"{self.manager.sol.rastgelelik_orani * 100:.0f}") 
        except ValueError:
            self.write_log("Titreşim için geçersiz giriş. Lütfen bir sayı girin.", tag="error")
            self.rand_entry.set(f"{self.manager.sol.rastgelelik_orani * 100:.0f}")

    def update_gui(self, isim, durum_veya_hata):
        
        def _update():
            if isim == "LMB (Sol Tık)":
                status_text = "AKTİF" if durum_veya_hata else "KAPALI"
                color = RENK_VURGU if durum_veya_hata else RENK_HATA
                self.status_sol_led.config(text=status_text, foreground=color)
                self.write_log(f"Sol Tık Makro Durumu: {status_text}", tag="info" if durum_veya_hata else "warn")
            elif isim == "RMB (Sağ Tık)":
                status_text = "AKTİF" if durum_veya_hata else "KAPALI"
                color = RENK_VURGU if durum_veya_hata else RENK_HATA
                self.status_sag_led.config(text=status_text, foreground=color)
                self.write_log(f"Sağ Tık Makro Durumu: {status_text}", tag="info" if durum_veya_hata else "warn")
            elif isim == "HATA_KRITIK":
                self.write_log(f"[KRİTİK HATA] {durum_veya_hata}", tag="error")
        
        if self.root.winfo_exists():
            self.root.after(0, _update)

    def write_log(self, message, tag=None):
        """Sistem loguna mesaj yazar ve renklendirir."""
        self.log_text.config(state=tk.NORMAL)
        current_time = time.strftime('%H:%M:%S')
        full_message = f"[{current_time}] {message}\n"
        
        self.log_text.insert(tk.END, full_message)
        
        if tag == "error":
             self.log_text.tag_config('error', foreground=RENK_HATA)
             self.log_text.tag_add('error', "end-2l", "end-1c")
        elif tag == "warn":
             self.log_text.tag_config('warn', foreground="#FFFF00") # Sarı
             self.log_text.tag_add('warn', "end-2l", "end-1c")
        elif tag == "info" or tag == "init":
             self.log_text.tag_config('info', foreground=RENK_VURGU)
             self.log_text.tag_add('info', "end-2l", "end-1c")
             
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    #  Tuş Yakalama 
    def start_key_listener(self, key_name, entry_widget):
        if self.listening_for_key:
            self.write_log("Zaten tuş dinleniyor. Lütfen mevcut atamayı bitirmek için bir tuşa basın.", tag="warn")
            return
        
        self.write_log(f"'{key_name.upper()}' için yeni kısayol tuşu bekleniyor...", tag="info")
        self.listening_for_key = {"key_name": key_name, "entry": entry_widget}
        
        for k_name, btn in self.entry_fields.items():
            if "_button" in k_name:
                btn.config(state=tk.DISABLED)
                
       
        entry_widget.config(state=tk.NORMAL)
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, "...")
        entry_widget.config(state="readonly")
        
        self._temp_key_listener = KeyboardListener(on_press=self._on_temp_key_press)
        self._temp_key_listener.start()

    def _on_temp_key_press(self, key):
        try:
            if self.listening_for_key:
                key_str = self._key_to_string(key)
                if key_str:
                    self.root.after(0, self._process_captured_key, key_str)
                    return False 
                else:
                    self.write_log(f"Desteklenmeyen tuş basıldı: {key}. Lütfen başka bir tuş deneyin.", tag="warn")
        except Exception as e:
            self.write_log(f"Tuş yakalama sırasında hata: {e}", tag="error")
        return True 

    def _process_captured_key(self, key_str):
        key_name = self.listening_for_key["key_name"]
        entry_widget = self.listening_for_key["entry"]
        
        entry_widget.config(state=tk.NORMAL) 
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, key_str.upper())
        entry_widget.config(state="readonly") 
        
        self.write_log(f"Yeni kısayol tuşu '{key_str.upper()}', '{key_name.upper()}' için atandı.", tag="info")
        self.listening_for_key = None 
        
        for k_name, btn in self.entry_fields.items():
            if "_button" in k_name:
                btn.config(state=tk.NORMAL)
        
        if self._temp_key_listener and self._temp_key_listener.running:
            self._temp_key_listener.stop()
            self._temp_key_listener.join()
            
        self.kaydet_tuslar_to_file(auto=True)
        
    def _key_to_string(self, key):
        if isinstance(key, KeyCode):
            return key.char
        elif isinstance(key, Key):
            return key.name
        return None

    def kaydet_tuslar_to_file(self, auto=False):
        yeni_tuslar = {}
        for key_name in DEFAULT_TUS_ATAMALARI.keys():
            entry = self.entry_fields[key_name]
            yeni_tuslar[key_name] = entry.get().lower()
            if not key_from_string(yeni_tuslar[key_name]):
                messagebox.showerror("Kısayol Hatası", f"'{key_name.upper()}' için geçersiz kısayol: {yeni_tuslar[key_name]}! Lütfen geçerli bir tuş kullanın.")
                self.write_log(f"'{key_name.upper()}' için geçersiz kısayol: {yeni_tuslar[key_name]}.", tag="error")
                return

        global TUS_ATAMALARI
        TUS_ATAMALARI.update(yeni_tuslar)
        save_tuslar(TUS_ATAMALARI)
        
        
        self.control_frame.winfo_children()[1].winfo_children()[2].config(text=f"AÇ/KAPA [{TUS_ATAMALARI['sol_tik'].upper()}]")
        self.control_frame.winfo_children()[1].winfo_children()[5].config(text=f"AÇ/KAPA [{TUS_ATAMALARI['sag_tik'].upper()}]")
        self.cikis_button.config(text=f"SİSTEMİ KAPAT [{TUS_ATAMALARI['cikis'].upper()}]")
        
        for key_name in DEFAULT_TUS_ATAMALARI.keys():
             self.entry_fields[f"{key_name}_status"].config(text=f"Aktif: {TUS_ATAMALARI[key_name].upper()}")

        self.write_log("Konfigürasyon parametreleri başarıyla kaydedildi ve uygulandı.", tag="info")
        if not auto:
             messagebox.showinfo("Konfigürasyon Kaydedildi", "Yeni kısayol tuşları ve ayarlar kaydedildi.")

    def klavye_dinle(self):
        try:
            with KeyboardListener(on_press=self.manager.on_press) as listener:
                listener.join()
        except Exception as e:
            self.write_log(f"Klavye dinleyici hatası: {e}", tag="error")
            messagebox.showerror("Sistem Hatası", f"Klavye dinleyici çöktü: {e}. Uygulama kapatılacak.")
        finally:
            if self.root.winfo_exists():
                self.root.after(0, self.kapat)

    def kapat(self):
        self.write_log("BYFORGEON sistem kapatma sırası başlatılıyor...", tag="warn")
        self.manager.stop_all()
        time.sleep(0.7) 
        if self.root.winfo_exists():
            self.root.quit()
        print("[BYFORGEON] Sistem Çevrimdışı. Hoşça kalın.")
if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = MacroGUI(root)
    root.mainloop()
