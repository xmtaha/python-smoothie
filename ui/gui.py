"""
Smoothie Python GUI
Modern, koyu temali kullanici arayuzu.
Turkce ve Ingilizce cift dil destegi, anlik dil gecisi, dinamik istatistikler ve hat yonetimi.
"""

import asyncio
import locale
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List

from core.i18n import I18n
from core.network_detector import NetworkAdapter, NetworkDetector
from core.proxy_engine import ProxyEngine
from core.windows_proxy import WindowsProxyManager


class SmoothieApp:
    def __init__(self, root: tk.Tk, default_lang: str = None):
        self.root = root

        # Sistem dilini otomatik tespit et
        if not default_lang:
            try:
                sys_lang = locale.getdefaultlocale()[0] or ""
                default_lang = "tr" if "tr" in sys_lang.lower() else "en"
            except Exception:
                default_lang = "tr"

        self.i18n = I18n(default_lang)

        self.root.title(self.i18n("app_title"))
        self.root.geometry("430x640")
        self.root.minsize(390, 520)
        self.root.configure(bg="#1e1e2e")

        # Core bilesenler
        self.windows_proxy = WindowsProxyManager(port=1080)
        self.proxy_engine = ProxyEngine(host="127.0.0.1", port=1080, enable_sticky=False)
        self.adapters: List[NetworkAdapter] = []
        self.adapter_vars: Dict[str, tk.BooleanVar] = {}
        self.adapter_cards: Dict[str, tk.Label] = {}
        self.adapter_gw_labels: Dict[str, tk.Label] = {}

        # Asyncio arka plan dongusu
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.loop_thread.start()

        self.is_running = False

        # Baslangicta eski oturumdan kalan proxy varsa kapat (Crash-Safe)
        if self.windows_proxy.is_proxy_currently_enabled_in_system():
            self.windows_proxy.disable_proxy()

        self._setup_styles()
        self._build_ui()
        self._refresh_adapters()

        # Duzenli istatistik guncelleme dongusu
        self.root.after(1000, self._update_stats_loop)

        # Pencere kapatma protokolu
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _run_async_loop(self):
        """Proxy motorunun calistigi arka plan asyncio dongusu."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _setup_styles(self):
        """Modern koyu tema stilleri."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TFrame", background="#1e1e2e")
        style.configure("Card.TFrame", background="#2a2b3d", relief="flat")
        style.configure(
            "TCheckbutton",
            background="#2a2b3d",
            foreground="#cdd6f4",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TCheckbutton",
            background=[("active", "#2a2b3d")],
            foreground=[("active", "#89b4fa")],
        )

    def _build_ui(self):
        """Arayuz bilesenlerini insa eder."""
        # Ana Kapsayici
        main_frame = ttk.Frame(self.root, style="Dark.TFrame", padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Baslik, Logo ve Dil Secici
        title_box = tk.Frame(main_frame, bg="#1e1e2e")
        title_box.pack(fill=tk.X, pady=(0, 15))

        lbl_title = tk.Label(
            title_box,
            text="Smoothie",
            font=("Segoe UI", 22, "bold"),
            fg="#f38ba8",
            bg="#1e1e2e",
        )
        lbl_title.pack(side=tk.LEFT)

        lbl_badge = tk.Label(
            title_box,
            text=self.i18n("badge_version"),
            font=("Segoe UI", 9, "bold"),
            fg="#a6adc8",
            bg="#313244",
            padx=6,
            pady=2,
        )
        lbl_badge.pack(side=tk.LEFT, padx=10, pady=(6, 0))

        # Dil Degistirme Butonu (TR / EN)
        self.btn_lang = tk.Button(
            title_box,
            text="TR / EN",
            font=("Segoe UI", 9, "bold"),
            bg="#45475a",
            fg="#cdd6f4",
            activebackground="#585b70",
            activeforeground="#cdd6f4",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._switch_language,
        )
        self.btn_lang.pack(side=tk.RIGHT, pady=(6, 0))

        # Durum Karti (Ana Kart)
        self.status_card = tk.Frame(main_frame, bg="#313244", padx=15, pady=15, highlightthickness=1, highlightbackground="#45475a")
        self.status_card.pack(fill=tk.X, pady=(0, 15))

        self.lbl_status_icon = tk.Label(
            self.status_card,
            text="●",
            font=("Segoe UI", 16),
            fg="#f38ba8",
            bg="#313244",
        )
        self.lbl_status_icon.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_status_text = tk.Label(
            self.status_card,
            text=self.i18n("status_off"),
            font=("Segoe UI", 12, "bold"),
            fg="#cdd6f4",
            bg="#313244",
        )
        self.lbl_status_text.pack(side=tk.LEFT)

        # Ana Ac/Kapa Butonu
        self.btn_toggle = tk.Button(
            main_frame,
            text=self.i18n("btn_start"),
            font=("Segoe UI", 12, "bold"),
            bg="#a6e3a1",
            fg="#11111b",
            activebackground="#94e2d5",
            activeforeground="#11111b",
            relief=tk.FLAT,
            pady=12,
            cursor="hand2",
            command=self._toggle_bonding,
        )
        self.btn_toggle.pack(fill=tk.X, pady=(0, 15))

        # Ag Bagdastiricilari Basligi ve Yenile Butonu
        header_frame = tk.Frame(main_frame, bg="#1e1e2e")
        header_frame.pack(fill=tk.X, pady=(10, 5))

        self.lbl_adapters_header = tk.Label(
            header_frame,
            text=self.i18n("header_adapters"),
            font=("Segoe UI", 10, "bold"),
            fg="#a6adc8",
            bg="#1e1e2e",
        )
        self.lbl_adapters_header.pack(side=tk.LEFT)

        self.btn_refresh = tk.Button(
            header_frame,
            text=self.i18n("btn_refresh"),
            font=("Segoe UI", 9),
            bg="#313244",
            fg="#cdd6f4",
            activebackground="#45475a",
            relief=tk.FLAT,
            padx=8,
            cursor="hand2",
            command=self._refresh_adapters,
        )
        self.btn_refresh.pack(side=tk.RIGHT)

        # Adaptorler Listesi (Kapsayici)
        self.adapters_container = tk.Frame(main_frame, bg="#1e1e2e")
        self.adapters_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # Alt Bilgi ve Toplam Veri Sayaci
        footer_card = tk.Frame(main_frame, bg="#181825", padx=10, pady=8)
        footer_card.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        self.lbl_total_stats = tk.Label(
            footer_card,
            text=self.i18n("footer_idle"),
            font=("Segoe UI", 9),
            fg="#bac2de",
            bg="#181825",
        )
        self.lbl_total_stats.pack(anchor=tk.W)

    def _switch_language(self):
        """Turkce ve Ingilizce arasinda aninda gecis yapar."""
        new_lang = self.i18n.toggle_language()
        self.root.title(self.i18n("app_title"))

        # Butonlar ve basliklar
        self.lbl_adapters_header.config(text=self.i18n("header_adapters"))
        self.btn_refresh.config(text=self.i18n("btn_refresh"))

        # Durum ve ac/kapa butonu
        if self.is_running:
            self.lbl_status_text.config(text=self.i18n("status_on"))
            self.btn_toggle.config(text=self.i18n("btn_stop"))
        else:
            self.lbl_status_text.config(text=self.i18n("status_off"))
            self.btn_toggle.config(text=self.i18n("btn_start"))

        # Ag gecidi etiketleri
        gw_prefix = self.i18n("gateway_label")
        for adapter in self.adapters:
            if adapter.ip_address in self.adapter_gw_labels:
                self.adapter_gw_labels[adapter.ip_address].config(text=f"{gw_prefix}: {adapter.gateway}")

        # Sayac guncellemesi
        self._update_stats_display()

    def _refresh_adapters(self):
        """Ag adaptorlerini yeniden tarar ve listeyi gunceller."""
        self.adapters = NetworkDetector.get_active_adapters()

        for widget in self.adapters_container.winfo_children():
            widget.destroy()

        self.adapter_cards.clear()
        self.adapter_gw_labels.clear()

        if not self.adapters:
            lbl_empty = tk.Label(
                self.adapters_container,
                text=self.i18n("empty_adapters"),
                font=("Segoe UI", 10),
                fg="#f38ba8",
                bg="#1e1e2e",
                justify=tk.CENTER,
            )
            lbl_empty.pack(pady=30)
            return

        for adapter in self.adapters:
            var = self.adapter_vars.get(adapter.ip_address, tk.BooleanVar(value=True))
            self.adapter_vars[adapter.ip_address] = var

            # Kart
            card = tk.Frame(self.adapters_container, bg="#2a2b3d", padx=12, pady=10, highlightthickness=1, highlightbackground="#363a4f")
            card.pack(fill=tk.X, pady=4)

            top_row = tk.Frame(card, bg="#2a2b3d")
            top_row.pack(fill=tk.X)

            chk = ttk.Checkbutton(
                top_row,
                text=adapter.name,
                variable=var,
                command=self._on_adapter_selection_changed,
                style="TCheckbutton",
            )
            chk.pack(side=tk.LEFT)

            lbl_ip = tk.Label(
                top_row,
                text=adapter.ip_address,
                font=("Consolas", 10, "bold"),
                fg="#89b4fa",
                bg="#2a2b3d",
            )
            lbl_ip.pack(side=tk.RIGHT)

            # Alt satir
            bottom_row = tk.Frame(card, bg="#2a2b3d")
            bottom_row.pack(fill=tk.X, pady=(4, 0))

            lbl_gw = tk.Label(
                bottom_row,
                text=f"{self.i18n('gateway_label')}: {adapter.gateway}",
                font=("Segoe UI", 8),
                fg="#a6adc8",
                bg="#2a2b3d",
            )
            lbl_gw.pack(side=tk.LEFT)
            self.adapter_gw_labels[adapter.ip_address] = lbl_gw

            lbl_stats = tk.Label(
                bottom_row,
                text=self.i18n("stats_format", size="0 KB", count="0"),
                font=("Segoe UI", 8),
                fg="#a6e3a1",
                bg="#2a2b3d",
            )
            lbl_stats.pack(side=tk.RIGHT)
            self.adapter_cards[adapter.ip_address] = lbl_stats

        self._on_adapter_selection_changed()

    def _on_adapter_selection_changed(self):
        """Kullanici secim yaptiginda proxy motorunu gunceller."""
        for adapter in self.adapters:
            adapter.is_active = self.adapter_vars[adapter.ip_address].get()

        active_list = [a for a in self.adapters if a.is_active]
        self.proxy_engine.update_adapters(active_list)

    def _toggle_bonding(self):
        """Ag birlestirmeyi baslatir veya durdurur."""
        if not self.is_running:
            self._start_service()
        else:
            self._stop_service()

    def _start_service(self):
        active_list = [a for a in self.adapters if a.is_active]
        if not active_list:
            messagebox.showwarning(self.i18n("warning_title"), self.i18n("warning_no_adapter"))
            return

        try:
            self.proxy_engine.update_adapters(active_list)
            # Motorun tamamen basladigini bekle ve hata varsa yakala
            future = asyncio.run_coroutine_threadsafe(self.proxy_engine.start(), self.loop)
            future.result(timeout=4.0)

            # Motor basariyla basladiysa Windows Proxy'sini ac
            self.windows_proxy.enable_proxy()
            self.is_running = True
            self._update_ui_state(running=True)
        except Exception as e:
            messagebox.showerror(self.i18n("warning_title"), f"Proxy baslatilamadi:\n{e}")
            self.windows_proxy.disable_proxy()
            self.is_running = False
            self._update_ui_state(running=False)

    def _stop_service(self):
        try:
            self.windows_proxy.disable_proxy()
            future = asyncio.run_coroutine_threadsafe(self.proxy_engine.stop(), self.loop)
            future.result(timeout=3.0)
        except Exception:
            pass
        finally:
            self.is_running = False
            self._update_ui_state(running=False)

    def _update_ui_state(self, running: bool):
        if running:
            self.lbl_status_icon.config(fg="#a6e3a1")
            self.lbl_status_text.config(text=self.i18n("status_on"))
            self.btn_toggle.config(
                text=self.i18n("btn_stop"),
                bg="#f38ba8",
                activebackground="#eba0ac",
            )
            self.status_card.config(highlightbackground="#a6e3a1")
        else:
            self.lbl_status_icon.config(fg="#f38ba8")
            self.lbl_status_text.config(text=self.i18n("status_off"))
            self.btn_toggle.config(
                text=self.i18n("btn_start"),
                bg="#a6e3a1",
                activebackground="#94e2d5",
            )
            self.status_card.config(highlightbackground="#45475a")

    def _update_stats_display(self):
        """Istatistik metinlerini secili dile gore yeniler."""
        total_bytes = 0
        total_conn = 0
        for adapter in self.adapters:
            if adapter.ip_address in self.adapter_cards:
                kb = adapter.bytes_transferred / 1024
                mb = kb / 1024
                size_str = f"{mb:.1f} MB" if mb >= 1.0 else f"{kb:.0f} KB"
                self.adapter_cards[adapter.ip_address].config(
                    text=self.i18n("stats_format", size=size_str, count=str(adapter.connections_count))
                )
                total_bytes += adapter.bytes_transferred
                total_conn += adapter.connections_count

        if self.is_running:
            tot_mb = (total_bytes / 1024) / 1024
            tot_str = f"{tot_mb:.2f} MB" if tot_mb >= 1.0 else f"{total_bytes/1024:.0f} KB"
            self.lbl_total_stats.config(
                text=self.i18n(
                    "footer_stats",
                    total=tot_str,
                    active=str(self.proxy_engine._active_connections),
                    reqs=str(total_conn),
                )
            )
        else:
            self.lbl_total_stats.config(text=self.i18n("footer_idle"))

    def _update_stats_loop(self):
        """Her saniye canli verileri yenileyen dongu."""
        if self.is_running:
            self._update_stats_display()
        self.root.after(1000, self._update_stats_loop)

    def _on_close(self):
        """Pencere kapatildiginda proxy'yi guvenle kapat."""
        if self.is_running:
            self._stop_service()
        self.root.destroy()
