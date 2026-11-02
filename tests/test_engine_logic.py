"""
ProxyEngine yuk dengeleme mantiginin cevrimdisi (offline) unit testleri.
Gercek ag, registry veya internet baglantisi kullanilmez; yalnizca sahte adaptor listeleri.
"""

import unittest

from core.network_detector import NetworkAdapter
from core.proxy_engine import ProxyEngine


def make_adapter(ip: str, active: bool = True) -> NetworkAdapter:
    return NetworkAdapter(name=f"Adaptör {ip}", ip_address=ip, gateway="10.0.0.254", is_active=active)


class SelectAdapterTests(unittest.TestCase):
    def _engine_with(self, *ips):
        engine = ProxyEngine()
        engine.update_adapters([make_adapter(ip) for ip in ips])
        return engine

    def test_empty_adapter_list_returns_none(self):
        engine = ProxyEngine()
        self.assertIsNone(engine._select_adapter())

    def test_single_adapter_always_selected(self):
        engine = self._engine_with("10.0.0.1")
        for _ in range(3):
            self.assertEqual(engine._select_adapter().ip_address, "10.0.0.1")

    def test_round_robin_tie_break_on_equal_load(self):
        # Her secimden sonra baglanti serbest birakilirsa yukler esit kalir →
        # esitlikte round-robin sirasiyla dagitir.
        engine = self._engine_with("10.0.0.1", "10.0.0.2")
        picked = []
        for _ in range(4):
            chosen = engine._select_adapter().ip_address
            picked.append(chosen)
            engine._free_connection(chosen)
        self.assertEqual(picked, ["10.0.0.1", "10.0.0.2", "10.0.0.1", "10.0.0.2"])

    def test_loads_balance_out_over_many_requests(self):
        # Serbest birakmadan 16 istek: toplam yuk iki hatta da esit dagilir.
        engine = self._engine_with("10.0.0.1", "10.0.0.2")
        for _ in range(16):
            engine._select_adapter()
        counts = engine._connections_by_address
        self.assertEqual(counts["10.0.0.1"], counts["10.0.0.2"])

    def test_least_loaded_wins_when_loads_differ(self):
        engine = self._engine_with("10.0.0.1", "10.0.0.2")
        # 10.0.0.1'e yuk bindir
        for _ in range(3):
            engine._increment_connection("10.0.0.1")
        self.assertEqual(engine._select_adapter().ip_address, "10.0.0.2")

    def test_free_connection_never_goes_negative(self):
        engine = self._engine_with("10.0.0.1")
        engine._free_connection("10.0.0.1")
        engine._free_connection("10.0.0.1")
        self.assertEqual(engine._connections_by_address["10.0.0.1"], 0)
        self.assertEqual(engine._total_active_connections, 0)

    def test_free_unknown_adapter_is_safe(self):
        engine = self._engine_with("10.0.0.1")
        engine._free_connection("10.0.0.99")  # bilinmeyen IP: hata vermeden yok say
        self.assertEqual(engine._total_active_connections, 0)

    def test_update_adapters_filters_inactive(self):
        engine = ProxyEngine()
        engine.update_adapters([make_adapter("10.0.0.1", active=True), make_adapter("10.0.0.2", active=False)])
        self.assertEqual([a.ip_address for a in engine.adapters], ["10.0.0.1"])

    def test_update_adapters_cleans_stale_connection_counts(self):
        engine = self._engine_with("10.0.0.1", "10.0.0.2")
        engine._increment_connection("10.0.0.1")
        engine._increment_connection("10.0.0.2")
        engine.update_adapters([make_adapter("10.0.0.1")])  # 10.0.0.2 kaldirildi
        self.assertNotIn("10.0.0.2", engine._connections_by_address)
        self.assertEqual(engine._connections_by_address["10.0.0.1"], 1)

    def test_update_adapters_readds_removed_adapter_with_zero_load(self):
        engine = self._engine_with("10.0.0.1")
        engine.update_adapters([make_adapter("10.0.0.1"), make_adapter("10.0.0.5")])
        self.assertEqual(engine._connections_by_address["10.0.0.5"], 0)


if __name__ == "__main__":
    unittest.main()
