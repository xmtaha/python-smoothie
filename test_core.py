"""
Core bileşenlerini doğrulayan entegrasyon testi.
"""

import asyncio
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.network_detector import NetworkDetector
from core.proxy_engine import ProxyEngine
from core.windows_proxy import WindowsProxyManager


async def test_socks_request():
    print("[1] Ag bagdastiricilari taraniyor...")
    adapters = NetworkDetector.get_active_adapters()
    for a in adapters:
        print(f"  Bulundu: {a}")

    if not adapters:
        print("HATA: Aktif adaptor bulunamadi!")
        return

    print("\n[2] ProxyEngine baslatiliyor...")
    engine = ProxyEngine(host="127.0.0.1", port=1080, enable_sticky=False)
    engine.update_adapters(adapters)
    await engine.start()

    print("\n[3] SOCKS5 Multi-Connect testi (4 ardisik istek)...")
    for i in range(4):
        c_reader, c_writer = await asyncio.open_connection("127.0.0.1", 1080)

        # Handshake
        c_writer.write(b"\x05\x01\x00")
        await c_writer.drain()
        resp = await c_reader.readexactly(2)
        assert resp == b"\x05\x00"

        # Connect
        target = b"example.com"
        req = b"\x05\x01\x00\x03" + bytes([len(target)]) + target + struct.pack("!H", 80)
        c_writer.write(req)
        await c_writer.drain()
        resp = await c_reader.readexactly(10)
        assert resp[1] == 0

        # Disari cikan yerel IP
        bound_ip = ".".join(str(b) for b in resp[4:8])
        print(f"  -> Istek #{i+1} baglandi! Cikis Yapilan Yerel IP: {bound_ip}")

        # HTTP GET
        c_writer.write(b"GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n")
        await c_writer.drain()
        data = await c_reader.read(100)
        assert b"HTTP/1.1" in data
        c_writer.close()
        await c_writer.wait_closed()

    print("\n[4] ProxyEngine durduruluyor...")
    await engine.stop()
    print(">>> Multi-Connect Testi Basariyla Tamamlandi! <<<")


if __name__ == "__main__":
    asyncio.run(test_socks_request())
