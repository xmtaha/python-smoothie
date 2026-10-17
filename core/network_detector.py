"""
Network Adapter Detector
Windows sistemindeki aktif ve internet çıkışı olan (Default Gateway bulunan)
fiziksel ağ bağdaştırıcılarını tespit eder.
"""

import logging
import re
import socket
import subprocess
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("NetworkDetector")


@dataclass
class NetworkAdapter:
    name: str
    ip_address: str
    gateway: str
    is_active: bool = True
    priority: int = 1
    connections_count: int = 0
    bytes_transferred: int = 0

    def __str__(self):
        return f"{self.name} ({self.ip_address}) -> GW: {self.gateway}"


class NetworkDetector:
    @staticmethod
    def get_active_adapters() -> List[NetworkAdapter]:
        adapters = []
        try:
            output = subprocess.check_output(
                ["netsh", "interface", "ipv4", "show", "addresses"],
                text=True,
                encoding="cp850",
                errors="replace",
            )
        except Exception as e:
            logger.error(f"netsh execution failed: {e}")
            return adapters

        current_interface = None
        current_ip = None
        current_gateway = None

        for line in output.splitlines():
            line_clean = line.strip()

            match_iface = re.search(r'interface "([^"]+)"', line_clean, re.IGNORECASE)
            if match_iface:
                if current_interface and current_ip and current_gateway:
                    if not current_interface.lower().startswith("loopback"):
                        adapters.append(
                            NetworkAdapter(
                                name=current_interface,
                                ip_address=current_ip,
                                gateway=current_gateway,
                            )
                        )
                current_interface = match_iface.group(1)
                current_ip = None
                current_gateway = None
                continue

            match_ip = re.search(r'(?:IP Address|IP Adresi)\s*:\s*([\d\.]+)', line_clean, re.IGNORECASE)
            if match_ip:
                current_ip = match_ip.group(1)
                continue

            match_gw = re.search(r'(?:Default Gateway|Varsayılan Ağ Geçidi)\s*:\s*([\d\.]+)', line_clean, re.IGNORECASE)
            if match_gw:
                current_gateway = match_gw.group(1)
                continue

        if current_interface and current_ip and current_gateway:
            if not current_interface.lower().startswith("loopback"):
                adapters.append(
                    NetworkAdapter(
                        name=current_interface,
                        ip_address=current_ip,
                        gateway=current_gateway,
                    )
                )

        verified_adapters = []
        for adapter in adapters:
            if NetworkDetector._can_bind_ip(adapter.ip_address):
                verified_adapters.append(adapter)
            else:
                logger.warning(f"Cannot bind to IP, excluding adapter: {adapter}")

        return verified_adapters

    @staticmethod
    def _can_bind_ip(ip: str) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((ip, 0))
            return True
        except Exception:
            return False
