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
from core.windows_proxy import WindowsProxyManager
from ui.gui import SmoothieApp


def run_gui(lang: str = None):
    """Grafik Kullanici Arayuzunu (GUI) baslatir."""
    root = tk.Tk()
    app = SmoothieApp(root, default_lang=lang)
    root.mainloop()


async def run_cli(host: str = "127.0.0.1", port: int = 1080, lang: str = "tr"):
    """Terminal / Bassiz (Headless) modda calistirir."""
    i18n = I18n(lang)
    logging.info(f"Smoothie CLI ({lang.upper()}) starting...")

    adapters = NetworkDetector.get_active_adapters()
    if not adapters:
        logging.error(i18n("empty_adapters"))
        return

    logging.info(f"{i18n('header_adapters')}:")
    for a in adapters:
        logging.info(f" - {a.name} ({a.ip_address}) -> {i18n('gateway_label')}: {a.gateway}")

    proxy_manager = WindowsProxyManager(host=host, port=port)
    engine = ProxyEngine(host=host, port=port, enable_sticky=False)
    engine.update_adapters(adapters)

    await engine.start()
    proxy_manager.enable_proxy()
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


def main():
    parser = argparse.ArgumentParser(description="Smoothie - Network Blender (Python)")
    parser.add_argument("--cli", action="store_true", help="Run in headless terminal mode without GUI")
    parser.add_argument("--port", type=int, default=1080, help="SOCKS5 Proxy Port (Default: 1080)")
    parser.add_argument("--lang", type=str, choices=["tr", "en"], default=None, help="UI / CLI Language (tr or en)")
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
            asyncio.run(run_cli(port=args.port, lang=args.lang or "tr"))
        except KeyboardInterrupt:
            pass
    else:
        run_gui(lang=args.lang)


if __name__ == "__main__":
    main()
