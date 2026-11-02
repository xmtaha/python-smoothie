"""
Smoothie Python - Main Entry Point
Uygulamanin ana calistirma dosyasi.
Turkce ve Ingilizce cift dil destegi, GUI ve CLI secenekleri.
"""

import argparse
import asyncio
import logging
import os
import sys
import tkinter as tk

# Core ve UI yollarini sys.path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.i18n import I18n
from core.network_detector import NetworkDetector
from core.proxy_engine import ProxyEngine
from core.version import __version__
from core.windows_proxy import WindowsProxyManager
from ui.gui import SmoothieApp


def is_port_in_use_error(e: OSError) -> bool:
    """Windows (10048 WSAEADDRINUSE) ve POSIX (48/98 EADDRINUSE) uyumlu kontrol."""
    return getattr(e, "winerror", None) == 10048 or e.errno in (48, 98, 10048)


def run_gui(lang: str = None):
    """Grafik Kullanici Arayuzunu (GUI) baslatir."""
    root = tk.Tk()
    app = SmoothieApp(root, default_lang=lang)
    root.mainloop()


async def run_cli(host: str = "127.0.0.1", port: int = 1080, lang: str = "tr") -> int:
    """Terminal / Bassiz (Headless) modda calistirir. Exit code dondurur."""
    i18n = I18n(lang)
    logging.info(f"Smoothie CLI ({lang.upper()}) starting...")

    adapters = NetworkDetector.get_active_adapters()
    if not adapters:
        logging.error(i18n("empty_adapters"))
        return 1

    logging.info(f"{i18n('header_adapters')}:")
    for a in adapters:
        logging.info(f" - {a.name} ({a.ip_address}) -> {i18n('gateway_label')}: {a.gateway}")

    engine = ProxyEngine(host=host, port=port, enable_sticky=False)
    engine.update_adapters(adapters)

    try:
        await engine.start()
    except OSError as e:
        if is_port_in_use_error(e):
            logging.error(i18n("error_port_in_use", port=port))
        else:
            logging.error(f"Proxy engine could not start: {e}")
        return 1

    # Motorun basladigini dogruladiktan SONRA sistem proxy'sini ac (Baslatma hatasi sistem ayarlarina dokunmasin)
    proxy_manager = WindowsProxyManager(host=host, port=port)
    if not proxy_manager.enable_proxy():
        logging.error("Windows proxy settings could not be written.")
        await engine.stop()
        return 1
    logging.info(f"{i18n('status_on')} (Port: {port})")

    try:
        while True:
            await asyncio.sleep(1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        logging.info("Shutting down...")
        proxy_manager.disable_proxy()
        await engine.stop()
    return 0


def main():
    parser = argparse.ArgumentParser(description=f"Smoothie - Network Blender (Python) v{__version__}")
    parser.add_argument("--cli", action="store_true", help="Run in headless terminal mode without GUI")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Local proxy bind address (Default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=1080, help="SOCKS5 Proxy Port (Default: 1080)")
    parser.add_argument("--lang", type=str, choices=["tr", "en"], default=None, help="UI / CLI Language (tr or en)")
    parser.add_argument("--version", action="version", version=f"Smoothie v{__version__}")
    args = parser.parse_args()

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoothie.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8", mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    def uncaught_exception_handler(exc_type, exc_val, exc_tb):
        logging.critical("Uncaught Exception / Beklenmeyen Hata:", exc_info=(exc_type, exc_val, exc_tb))
        try:
            WindowsProxyManager().disable_proxy()
        except Exception:
            pass

    sys.excepthook = uncaught_exception_handler

    if args.cli:
        try:
            exit_code = asyncio.run(run_cli(host=args.host, port=args.port, lang=args.lang or "tr"))
        except KeyboardInterrupt:
            exit_code = 0
        sys.exit(exit_code)
    else:
        run_gui(lang=args.lang)


if __name__ == "__main__":
    main()
