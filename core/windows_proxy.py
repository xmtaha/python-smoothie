"""
Windows Internet Settings Proxy Controller
Registry tabanlı Windows SOCKS5 proxy ayarlarını yönetir.
ctypes ile doğrudan WinINet C-API çağrısı yaparak 0 ms gecikmeyle ayarları yeniler.
Crash-Safe: Beklenmeyen kapanmalarda proxy'nin açık kalıp interneti kilitlemesini engeller.
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
        self._wininet = ctypes.windll.wininet

        atexit.register(self.disable_proxy)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (ValueError, AttributeError):
            pass

    def _signal_handler(self, sig, frame):
        logger.info(f"Signal received ({sig}), disabling proxy...")
        self.disable_proxy()
        sys.exit(0)

    def _refresh_wininet(self):
        try:
            self._wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            self._wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
        except Exception as e:
            logger.error(f"WinINet refresh error: {e}")

    def is_proxy_currently_enabled_in_system(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "ProxyEnable")
                return bool(val)
        except Exception:
            return False

    def enable_proxy(self) -> bool:
        proxy_server = f"socks={self.host}:{self.port}"
        override = "<local>;localhost;127.0.0.1"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
                winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, override)

            self._refresh_wininet()
            self.is_enabled = True
            logger.info(f"Windows proxy enabled -> {proxy_server}")
            return True
        except Exception as e:
            logger.error(f"Proxy enable error: {e}")
            return False

    def disable_proxy(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)

            self._refresh_wininet()
            self.is_enabled = False
            logger.info("Windows proxy disabled.")
            return True
        except Exception as e:
            logger.error(f"Proxy disable error: {e}")
            return False
