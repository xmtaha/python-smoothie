"""
High-Performance Asyncio SOCKS5 Proxy & Dispatcher Engine
Orijinal dispatch-proxy algoritmasi (Least-Connections Ratio Balancer) ile calisir.
Steam, Speedtest ve multi-threaded indirme yoneticileri icin optimize edilmistir.
"""

import asyncio
import logging
import socket
import struct
from typing import Dict, List, Optional
from .network_detector import NetworkAdapter

logger = logging.getLogger("ProxyEngine")

# SOCKS5 Sabitleri
SOCKS_VERSION = 5
CMD_CONNECT = 1

ATYP_IPV4 = 1
ATYP_DOMAINNAME = 3
ATYP_IPV6 = 4

REP_SUCCESS = 0
REP_GEN_FAILURE = 1
REP_CONN_NOT_ALLOWED = 2
REP_NET_UNREACHABLE = 3
REP_HOST_UNREACHABLE = 4
REP_CONN_REFUSED = 5
REP_CMD_NOT_SUPPORTED = 7
REP_ADDR_NOT_SUPPORTED = 8

BUFFER_SIZE = 131072  # 128 KB yuksek hizli transfer tamponu


class ProxyEngine:
    def __init__(self, host: str = "127.0.0.1", port: int = 1080, enable_sticky: bool = False):
        self.host = host
        self.port = port
        self.enable_sticky = enable_sticky  # Steam ve Speedtest icin varsayilan olarak FALSE!
        self.adapters: List[NetworkAdapter] = []
        self._server: Optional[asyncio.Server] = None
        self._is_running = False
        self._active_connections = 0

        # Orijinal dispatch-proxy dengeleme sayaclari
        self._connections_by_address: Dict[str, int] = {}
        self._total_active_connections: int = 0
        self._round_robin_counter = 0

    def update_adapters(self, adapters: List[NetworkAdapter]):
        """Aktif ag adaptorlerini gunceller."""
        self.adapters = [a for a in adapters if a.is_active]
        # Silinen adaptorleri temizle
        active_ips = {a.ip_address for a in self.adapters}
        self._connections_by_address = {ip: count for ip, count in self._connections_by_address.items() if ip in active_ips}
        for a in self.adapters:
            if a.ip_address not in self._connections_by_address:
                self._connections_by_address[a.ip_address] = 0

        logger.info(f"Aktif adaptorler guncellendi: {[a.name + ' (' + a.ip_address + ')' for a in self.adapters]}")

    def _select_adapter(self) -> Optional[NetworkAdapter]:
        """
        En Az Baglantili (Least-Connections) + Round-Robin Yuk Dengeleme Algoritmasi:
        1. Mevcut aktif baglanti sayisi en az olan adaptorleri tespit eder.
        2. Esitlik durumunda (orn. ikisi de bos veya ayni yukteyse) Round-Robin ile dagitir.
        Steam, Speedtest ve IDM coklu indirmelerinde hatlari tam %50-%50 esit paylastirir.
        """
        if not self.adapters:
            return None

        if len(self.adapters) == 1:
            adapter = self.adapters[0]
            self._increment_connection(adapter.ip_address)
            return adapter

        # En az yuklu adaptorleri bul
        min_conns = min(self._connections_by_address.get(a.ip_address, 0) for a in self.adapters)
        least_loaded = [a for a in self.adapters if self._connections_by_address.get(a.ip_address, 0) == min_conns]

        if len(least_loaded) > 1:
            chosen = least_loaded[self._round_robin_counter % len(least_loaded)]
            self._round_robin_counter += 1
        else:
            chosen = least_loaded[0]

        self._increment_connection(chosen.ip_address)
        return chosen

    def _increment_connection(self, ip: str):
        self._connections_by_address[ip] = self._connections_by_address.get(ip, 0) + 1
        self._total_active_connections += 1

    def _free_connection(self, ip: str):
        if ip in self._connections_by_address:
            self._connections_by_address[ip] = max(0, self._connections_by_address[ip] - 1)
        self._total_active_connections = max(0, self._total_active_connections - 1)

    async def _handle_socks5_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Her bir SOCKS4/SOCKS5 istemci baglantisini yonetir."""
        self._active_connections += 1
        chosen_ip = None
        is_socks4 = False
        is_http = False
        s4_port_bytes = b"\x00\x00"
        s4_ip_bytes = b"\x00\x00\x00\x00"

        try:
            # 1. Protokol Tespiti (SOCKS4, SOCKS5 veya HTTP CONNECT Proxy)
            first_byte = (await client_reader.readexactly(1))[0]

            if first_byte == 4:
                # SOCKS4 Protokolu
                is_socks4 = True
                cmd = (await client_reader.readexactly(1))[0]
                if cmd != 1:  # Sadece CONNECT desteklenir
                    client_writer.write(b"\x00\x5B\x00\x00\x00\x00\x00\x00")
                    await client_writer.drain()
                    client_writer.close()
                    return

                s4_port_bytes = await client_reader.readexactly(2)
                dest_port = struct.unpack("!H", s4_port_bytes)[0]
                s4_ip_bytes = await client_reader.readexactly(4)

                # Null-terminated userid'yi tuket
                while True:
                    b = await client_reader.readexactly(1)
                    if b == b"\x00":
                        break

                # SOCKS4a (Domain name) destegi
                if s4_ip_bytes[:3] == b"\x00\x00\x00" and s4_ip_bytes[3] != 0:
                    domain_bytes = b""
                    while True:
                        b = await client_reader.readexactly(1)
                        if b == b"\x00":
                            break
                        domain_bytes += b
                    dest_host = domain_bytes.decode("utf-8", errors="replace")
                else:
                    dest_host = socket.inet_ntoa(s4_ip_bytes)

            elif first_byte == 5:
                # SOCKS5 Protokolu
                nmethods = (await client_reader.readexactly(1))[0]
                await client_reader.readexactly(nmethods)
                # No-Auth (0x00)
                client_writer.write(bytes([SOCKS_VERSION, 0]))
                await client_writer.drain()

                # SOCKS5 Baglanti Istegi
                version, cmd, rsv, atyp = await client_reader.readexactly(4)
                if version != SOCKS_VERSION or cmd != CMD_CONNECT:
                    self._send_reply(client_writer, REP_CMD_NOT_SUPPORTED)
                    await client_writer.drain()
                    client_writer.close()
                    return

                dest_host = ""
                if atyp == ATYP_IPV4:
                    addr_bytes = await client_reader.readexactly(4)
                    dest_host = socket.inet_ntoa(addr_bytes)
                elif atyp == ATYP_DOMAINNAME:
                    domain_len = (await client_reader.readexactly(1))[0]
                    domain_bytes = await client_reader.readexactly(domain_len)
                    dest_host = domain_bytes.decode("utf-8", errors="replace")
                elif atyp == ATYP_IPV6:
                    await client_reader.readexactly(16)
                    # IPv4 cift hat baglantisi kullandigimiz icin Happy Eyeballs fallback tetikle
                    self._send_reply(client_writer, REP_ADDR_NOT_SUPPORTED)
                    await client_writer.drain()
                    client_writer.close()
                    return
                else:
                    self._send_reply(client_writer, REP_ADDR_NOT_SUPPORTED)
                    await client_writer.drain()
                    client_writer.close()
                    return

                port_bytes = await client_reader.readexactly(2)
                dest_port = struct.unpack("!H", port_bytes)[0]

            elif chr(first_byte).isalpha():
                # HTTP Proxy / CONNECT Istegi (Firefox veya Windows HTTP istekleri)
                is_http = True
                line_rest = await client_reader.readline()
                req_line = (bytes([first_byte]) + line_rest).decode("utf-8", errors="replace").strip()
                parts = req_line.split()
                if len(parts) < 2:
                    client_writer.close()
                    return

                method, target = parts[0].upper(), parts[1]
                if method == "CONNECT":
                    if ":" in target:
                        dest_host, port_str = target.split(":", 1)
                        dest_port = int(port_str)
                    else:
                        dest_host = target
                        dest_port = 443
                    # Kalan HTTP basliklarini oku ve tuket
                    while True:
                        hdr = await client_reader.readline()
                        if not hdr or hdr in (b"\r\n", b"\n"):
                            break
                else:
                    # Duz HTTP GET/POST proxy istegi
                    from urllib.parse import urlparse
                    parsed = urlparse(target)
                    dest_host = parsed.hostname or target
                    dest_port = parsed.port or 80

            else:
                client_writer.close()
                return

            # 2. Yuk Dengeleme ile Adaptor Secimi
            adapter = self._select_adapter()
            if not adapter:
                if is_http:
                    client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                elif is_socks4:
                    client_writer.write(b"\x00\x5B\x00\x00\x00\x00\x00\x00")
                else:
                    self._send_reply(client_writer, REP_NET_UNREACHABLE)
                await client_writer.drain()
                client_writer.close()
                return

            chosen_ip = adapter.ip_address

            # 3. Secilen Adaptor Uzerinden Baglanti Kur
            remote_reader, remote_writer = await self._connect_via_adapter(dest_host, dest_port, chosen_ip)
            if not remote_writer:
                if is_http:
                    client_writer.write(b"HTTP/1.1 504 Gateway Timeout\r\n\r\n")
                elif is_socks4:
                    client_writer.write(b"\x00\x5B\x00\x00\x00\x00\x00\x00")
                else:
                    self._send_reply(client_writer, REP_HOST_UNREACHABLE)
                await client_writer.drain()
                client_writer.close()
                return

            # Basarili Cevabi Gonder
            if is_http:
                client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            elif is_socks4:
                # SOCKS4 0x5A = Request Granted (Basarili)
                client_writer.write(b"\x00\x5A" + s4_port_bytes + s4_ip_bytes)
            else:
                self._send_reply(client_writer, REP_SUCCESS, chosen_ip)
            await client_writer.drain()

            adapter.connections_count += 1

            # 5. Cift Yonlu Yuksek Hizli Veri Tuneli (High-Throughput Piping)
            await self._tunnel_traffic(client_reader, client_writer, remote_reader, remote_writer, adapter)

        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            logger.debug(f"SOCKS5 handler error: {e}")
        finally:
            if chosen_ip:
                self._free_connection(chosen_ip)
            self._active_connections = max(0, self._active_connections - 1)
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except Exception:
                pass

    def _send_reply(self, writer: asyncio.StreamWriter, rep_code: int, bind_ip: str = "0.0.0.0", bind_port: int = 0):
        try:
            ip_bytes = socket.inet_aton(bind_ip)
        except OSError:
            ip_bytes = b"\x00\x00\x00\x00"
        port_bytes = struct.pack("!H", bind_port)
        reply = bytes([SOCKS_VERSION, rep_code, 0, ATYP_IPV4]) + ip_bytes + port_bytes
        writer.write(reply)

    async def _connect_via_adapter(self, dest_host: str, dest_port: int, local_ip: str):
        """Yerel IP'ye bind olmus yuksek performansli TCP soketi acar."""
        loop = asyncio.get_running_loop()

        def _blocking_connect():
            try:
                # Localhost veya Loopback kontrolu: Loopback'e dis fiziksel IP'den bind olunamaz!
                is_loopback = dest_host in ("127.0.0.1", "localhost", "::1") or dest_host.startswith("127.")

                # Host adi verilirse dogrudan IPv4 (AF_INET) olarak coz
                addrinfo = socket.getaddrinfo(dest_host, dest_port, family=socket.AF_INET, type=socket.SOCK_STREAM)
                if not addrinfo:
                    return None
                target_ip, target_port = addrinfo[0][4]

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # TCP Optimizasyonlari: Gecikmeyi onle, buffer'i genislet
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
                sock.settimeout(8.0)
                # Loopback degilse secilen adaptore bind et
                if not is_loopback and not target_ip.startswith("127."):
                    sock.bind((local_ip, 0))
                sock.connect((target_ip, target_port))
                sock.setblocking(False)
                return sock
            except Exception as e:
                logger.debug(f"{local_ip} -> {dest_host}:{dest_port} baglanti hatasi: {e}")
                return None

        sock = await loop.run_in_executor(None, _blocking_connect)
        if not sock:
            return None, None

        try:
            remote_reader, remote_writer = await asyncio.open_connection(sock=sock)
            return remote_reader, remote_writer
        except Exception as e:
            logger.debug(f"Stream wrapper hatasi: {e}")
            sock.close()
            return None, None

    async def _tunnel_traffic(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        remote_reader: asyncio.StreamReader,
        remote_writer: asyncio.StreamWriter,
        adapter: NetworkAdapter,
    ):
        """
        Istemci ve hedef sunucu arasindaki trafigi sifir takilmayla (Zero-Stall) tuneller.
        Bir taraf baglantiyi sonlandirdiginda diger taraf derhal duzgunce kapatilir.
        """
        async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, other_writer: asyncio.StreamWriter):
            try:
                while True:
                    data = await reader.read(BUFFER_SIZE)
                    if not data:
                        break
                    writer.write(data)
                    # Sadece yazma kuyrugu yuksekse drain et (Throughput optimizasyonu)
                    if writer.transport and writer.transport.get_write_buffer_size() > BUFFER_SIZE:
                        await writer.drain()
                    adapter.bytes_transferred += len(data)
            except Exception:
                pass
            finally:
                # Kapanma sinyalini karsi tarafa ilet
                try:
                    writer.close()
                except Exception:
                    pass
                try:
                    other_writer.close()
                except Exception:
                    pass

        await asyncio.gather(
            pipe(client_reader, remote_writer, client_writer),
            pipe(remote_reader, client_writer, remote_writer),
            return_exceptions=True,
        )

    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_socks5_client,
            self.host,
            self.port,
            backlog=1024,
            reuse_address=True,
        )
        self._is_running = True
        logger.info(f"SOCKS5 Proxy {self.host}:{self.port} uzerinde baslatildi.")

    async def stop(self):
        self._is_running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("SOCKS5 Proxy durduruldu.")
