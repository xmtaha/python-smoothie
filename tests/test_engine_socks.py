"""
SOCKS5 / protokol davranisinin cevrimdisi (offline) testleri.
Trafik yalnizca loopback (127.0.0.1) uzerinden dolasir; internet, sistem proxy'si
veya Windows Registry hic kullanilmaz.
"""

import asyncio
import socket
import struct
import unittest

from core.network_detector import NetworkAdapter
from core.proxy_engine import ProxyEngine, REP_CMD_NOT_SUPPORTED


def build_socks5_connect_request(host: str, port: int, atyp: int = 1) -> bytes:
    """ATYP'ten bagimsiz SOCKS5 CONNECT isteği üretir."""
    req = b"\x05\x01\x00" + bytes([atyp])
    if atyp == 1:
        req += socket.inet_aton(host)
    elif atyp == 3:
        req += bytes([len(host)]) + host.encode()
    elif atyp == 4:
        req += b"\x00" * 16
    return req + struct.pack("!H", port)


class Socks5OfflineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Sahte hedef HTTP sunucusu (sadece loopback)
        self.upstream = await asyncio.start_server(self._fake_http_handler, "127.0.0.1", 0)
        self.upstream_port = self.upstream.sockets[0].getsockname()[1]

        # Engel motoru: loopback adaptoru ile port 0 (serbest port secilmesini saglar)
        self.engine = ProxyEngine(host="127.0.0.1", port=0)
        self.engine.update_adapters(
            [NetworkAdapter(name="Loopback", ip_address="127.0.0.1", gateway="127.0.0.1")]
        )
        await self.engine.start()
        self.proxy_port = self.engine._server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        await self.engine.stop()
        self.upstream.close()
        await self.upstream.wait_closed()

    async def _fake_http_handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            await reader.readline()  # istek satiri
            while True:
                header = await reader.readline()
                if header in (b"\r\n", b"\n", b""):
                    break
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello")
            await writer.drain()
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _open_sock(self):
        return await asyncio.open_connection("127.0.0.1", self.proxy_port)

    async def _socks5_handshake(self, reader, writer):
        writer.write(b"\x05\x01\x00")
        await writer.drain()
        reply = await reader.readexactly(2)
        self.assertEqual(reply, b"\x05\x00")

    # --- Basari senaryolari ---------------------------------------------------

    async def test_socks5_success_via_domain_and_ipv4(self):
        for atyp in (1, 3):
            with self.subTest(atyp=atyp):
                reader, writer = await self._open_sock()
                await self._socks5_handshake(reader, writer)
                writer.write(build_socks5_connect_request("127.0.0.1", self.upstream_port, atyp=atyp))
                await writer.drain()
                rep = await reader.readexactly(10)
                self.assertEqual(rep[1], 0x00)  # REP_SUCCESS
                writer.write(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
                await writer.drain()
                data = await reader.read()
                self.assertIn(b"HTTP/1.1 200 OK", data)
                self.assertIn(b"hello", data)
                writer.close()

    # --- Reddedilen / gecersiz handshake --------------------------------------

    async def test_unknown_first_byte_closes_connection_and_engine_survives(self):
        reader, writer = await self._open_sock()
        writer.write(b"\x07\x00\x00")
        await writer.drain()
        writer.close()  # yarim biraktik
        # Motor hayatta kalmali ve ayni islem guclenmeli
        await asyncio.sleep(0.1)
        reader2, writer2 = await self._open_sock()
        await self._socks5_handshake(reader2, writer2)
        writer2.close()

    async def test_socks5_unsupported_cmd_rejected(self):
        reader, writer = await self._open_sock()
        await self._socks5_handshake(reader, writer)
        req = b"\x05\x02\x00\x01" + socket.inet_aton("127.0.0.1") + struct.pack("!H", self.upstream_port)  # cmd=BIND
        writer.write(req)
        await writer.drain()
        rep = await reader.readexactly(10)
        self.assertEqual(rep[1], REP_CMD_NOT_SUPPORTED)
        writer.close()

    async def test_socks5_ipv6_addr_type_refused(self):
        reader, writer = await self._open_sock()
        await self._socks5_handshake(reader, writer)
        writer.write(build_socks5_connect_request("::1", self.upstream_port, atyp=4))
        await writer.drain()
        rep = await reader.readexactly(10)
        self.assertEqual(rep[1], 0x08)  # REP_ADDR_NOT_SUPPORTED
        writer.close()

    # --- Hedef sunucuya erisim / hata yanitlari --------------------------------

    async def test_upstream_connection_refused_returns_host_unreachable(self):
        # Lokali dinleyen bir sunucuyu ac-kapat: port garantili olarak REFUSED doner
        tmp = await asyncio.start_server(lambda r, w: r.read(), "127.0.0.1", 0)
        dead_port = tmp.sockets[0].getsockname()[1]
        tmp.close()
        await tmp.wait_closed()

        reader, writer = await self._open_sock()
        await self._socks5_handshake(reader, writer)
        writer.write(build_socks5_connect_request("127.0.0.1", dead_port))
        await writer.drain()
        rep = await reader.readexactly(10)
        self.assertEqual(rep[1], 0x04)  # REP_HOST_UNREACHABLE
        writer.close()

    async def test_no_adapters_returns_net_unreachable(self):
        self.engine.update_adapters([])  # engel listesinin bos hali
        reader, writer = await self._open_sock()
        await self._socks5_handshake(reader, writer)
        writer.write(build_socks5_connect_request("127.0.0.1", self.upstream_port))
        await writer.drain()
        rep = await reader.readexactly(10)
        self.assertEqual(rep[1], 0x03)  # REP_NET_UNREACHABLE
        writer.close()

    async def test_engine_stop_refuses_new_connections(self):
        await self.engine.stop()
        with self.assertRaises(ConnectionRefusedError):
            await asyncio.open_connection("127.0.0.1", self.proxy_port)


if __name__ == "__main__":
    unittest.main()
