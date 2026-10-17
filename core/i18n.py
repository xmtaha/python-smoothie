"""
Internationalization (i18n) Module
Smoothie için Türkçe ve İngilizce çoklu dil desteği sağlar.
"""

from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "tr": {
        "app_title": "Smoothie - Ağ Birleştirici (Python)",
        "badge_version": "PYTHON v2.0",
        "status_off": "Ağ Birleştirme Kapalı",
        "status_on": "Ağlar Birleştirildi (Aktif)",
        "btn_start": "BİRLEŞTİRMEYİ BAŞLAT",
        "btn_stop": "BİRLEŞTİRMEYİ DURDUR",
        "header_adapters": "AKTİF AĞ HATLARI",
        "btn_refresh": "↻ Tara",
        "gateway_label": "Ağ Geçidi",
        "empty_adapters": "Aktif internet bağlantısı olan adaptör bulunamadı!\nLütfen kabloyu, Wi-Fi'ı veya USB Bağlantısını kontrol edin.",
        "footer_idle": "Toplam Aktarılan: 0 KB | Aktif Bağlantı: 0",
        "footer_stats": "Toplam: {total} | Aktif Bağlantı: {active} | Toplam İstek: {reqs}",
        "warning_title": "Uyarı",
        "warning_no_adapter": "Lütfen en az bir aktif ağ hattı seçin!",
        "stats_format": "{size} | {count} istek",
        "lang_switch_btn": "EN",
    },
    "en": {
        "app_title": "Smoothie - Network Blender (Python)",
        "badge_version": "PYTHON v2.0",
        "status_off": "Network Blending Disabled",
        "status_on": "Networks Blended (Active)",
        "btn_start": "START BLENDING",
        "btn_stop": "STOP BLENDING",
        "header_adapters": "ACTIVE NETWORK ADAPTERS",
        "btn_refresh": "↻ Scan",
        "gateway_label": "Gateway",
        "empty_adapters": "No active network adapters with internet access found!\nPlease check Ethernet, Wi-Fi, or USB Tethering.",
        "footer_idle": "Total Transferred: 0 KB | Active Connections: 0",
        "footer_stats": "Total: {total} | Active Conns: {active} | Total Requests: {reqs}",
        "warning_title": "Warning",
        "warning_no_adapter": "Please select at least one active network adapter!",
        "stats_format": "{size} | {count} reqs",
        "lang_switch_btn": "TR",
    },
}


class I18n:
    def __init__(self, current_lang: str = "tr"):
        self.current_lang = current_lang if current_lang in TRANSLATIONS else "tr"

    def set_language(self, lang: str):
        if lang in TRANSLATIONS:
            self.current_lang = lang

    def toggle_language(self) -> str:
        self.current_lang = "en" if self.current_lang == "tr" else "tr"
        return self.current_lang

    def get(self, key: str, **kwargs) -> str:
        text = TRANSLATIONS.get(self.current_lang, {}).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

    def __call__(self, key: str, **kwargs) -> str:
        return self.get(key, **kwargs)
