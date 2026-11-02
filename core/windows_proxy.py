"""
Windows Internet Settings Proxy Controller
Registry tabanlı Windows SOCKS5 proxy ayarlarını yönetir.
ctypes ile doğrudan WinINet C-API çağrısı yaparak 0 ms gecikmeyle ayarları yeniler.

Sahiplik-güvenli (ownership-safe):
- Yalnızca ProxyServer değeri bizi ((socks=host:port)) işaret ediyorsa kapatır.
- Başka bir uygulamaya ait proxy açıkken üzerine yazmaz veya kapatmaz; False döner.
- Crash-Safe: Beklenmeyen kapanmalarda yalnızca bizim açtığımız proxy devre dışı kalır.
"""

import atexit
import ctypes
import logging
import signal
import sys
import winreg

logger = logging.getLogger("WindowsProxy")

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37


class WindowsProxyManager:
    def __init__(self, host: str = "127.0.0.1", port: int = 1080):
        self.host = host
        self.port = port
        self.is_enabled = False
        self._owns_proxy = False  # Bu örnek kendi ayarını açtıysa True
        try:
            self._wininet = ctypes.windll.wininet
        except AttributeError:
            self._wininet = None  # Windows dışı ortam / test

        atexit.register(self._safe_teardown)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (ValueError, AttributeError):
            pass

    # --- Sahiplik yardımcıları ------------------------------------------------

    def _our_proxy_string(self) -> str:
        return f"socks={self.host}:{self.port}"

    def get_current_proxy_server(self) -> str:
        """Registry'deki güncel ProxyServer değerini döndürür, okunamazsa '' döner."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "ProxyServer")
                return val if isinstance(val, str) else str(val)
        except Exception:
            return ""

    def is_proxy_currently_enabled_in_system(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "ProxyEnable")
                return bool(val)
        except Exception:
            return False

    def is_our_proxy_active(self) -> bool:
        """Sistem proxy'si açık VE bizi işaret ediyor mu?"""
        if not self.is_proxy_currently_enabled_in_system():
            return False
        return self.get_current_proxy_server() == self._our_proxy_string()

    def has_foreign_proxy(self) -> bool:
        """Sistem proxy'si açık ama bize değil, başka bir uygulamaya/kullanıcıya mı ait?"""
        if not self.is_proxy_currently_enabled_in_system():
            return False
        server = self.get_current_proxy_server()
        return bool(server) and server != self._our_proxy_string()

    # --- Yaşam döngüsü ---------------------------------------------------------

    def _safe_teardown(self):
        """atexit: yalnızca hâlâ bizim ayarımız aktifse kapat."""
        if self._owns_proxy:
            self.disable_proxy()

    def _signal_handler(self, sig, frame):
        logger.info(f"Signal received ({sig}), disabling proxy...")
        if self._owns_proxy:
            self.disable_proxy()
        sys.exit(0)

    def _refresh_wininet(self):
        if not self._wininet:
            return
        try:
            self._wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            self._wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
        except Exception as e:
            logger.error(f"WinINet refresh error: {e}")

    # --- Ana işlemler -----------------------------------------------------------

    def enable_proxy(self) -> bool:
        """Kendi SOCKS5 ayarımızı yazar. Başka bir uygulamaya ait proxy aktifse dokunmaz."""
        current_server = self.get_current_proxy_server()
        if self.is_proxy_currently_enabled_in_system() and current_server != self._our_proxy_string() and current_server:
            logger.warning(f"Foreign proxy aktif ({current_server}); üzerine yazma reddedildi.")
            return False

        proxy_server = self._our_proxy_string()
        override = "<local>;localhost;127.0.0.1"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, override)

            self._refresh_wininet()
            self.is_enabled = True
            self._owns_proxy = True
            logger.info(f"Windows proxy enabled -> {proxy_server}")
            return True
        except Exception as e:
            logger.error(f"Proxy enable error: {e}")
            return False

    def disable_proxy(self) -> bool:
        """Proxy'yi kapatır. ProxyServer öyleyse yalnızca bizi işaret ediyorsa yazar; yoksa dokunmaz."""
        if not self.is_proxy_currently_enabled_in_system():
            self.is_enabled = False
            return True

        current_server = self.get_current_proxy_server()
        if current_server != self._our_proxy_string():
            logger.warning(
                f"Proxy degismis, bize ait degil ({current_server or 'bos'}); kapatma atlandi."
            )
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)

            self._refresh_wininet()
            self.is_enabled = False
            self._owns_proxy = False
            logger.info("Windows proxy disabled.")
            return True
        except Exception as e:
            logger.error(f"Proxy disable error: {e}")
            return False
