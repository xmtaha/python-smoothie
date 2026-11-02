"""
WindowsProxyManager sahiplik (ownership) testleri.
Windows Registry VE WinINet C-API sahte (mock) nesnelerle kullanilir; gerçek
registry veya sistem proxy ayarlarina HIC dokunulmaz.
"""

import unittest
import winreg
from unittest.mock import MagicMock, patch

from core.windows_proxy import WindowsProxyManager

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


class FakeRegistryStore:
    """QueryValueEx / SetValueEx davranisini taklit eden kucuk anahtar-değer deposu."""

    def __init__(self, initial=None):
        self.values = dict(initial or {})

    def query(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], type(self.values[name])

    def set(self, key, name, reserved, regtype, value):
        self.values[name] = value


def make_winreg_mock(store_values):
    """core.windows_proxy.winreg icin sahte modul üretir (gerçek modül görünmez)."""
    store = FakeRegistryStore(store_values)
    fake = MagicMock()
    fake.HKEY_CURRENT_USER = winreg.HKEY_CURRENT_USER
    fake.KEY_READ = winreg.KEY_READ
    fake.KEY_SET_VALUE = winreg.KEY_SET_VALUE
    fake.REG_DWORD = winreg.REG_DWORD
    fake.REG_SZ = winreg.REG_SZ
    fake.QueryValueEx.side_effect = lambda key, name: store.query(key, name)
    fake.SetValueEx.side_effect = lambda key, name, r, t, v: store.set(key, name, r, t, v)
    fake.store = store
    return fake


class WindowsProxyOwnershipTests(unittest.TestCase):
    def _manager(self, store_values=None):
        fake_winreg = make_winreg_mock(store_values)
        patcher = patch("core.windows_proxy.winreg", fake_winreg)
        mock_module = patcher.start()
        self.addCleanup(patcher.stop)

        manager = WindowsProxyManager(port=1080)
        manager._wininet = None  # WinINet C-API'yi bypass et
        import atexit as _atexit
        _atexit.unregister(manager._safe_teardown)  # test sürecinin çıkışına dokunma
        self._store = fake_winreg.store
        return manager

    # --- Uygulama kendi proxy'sini acip kapatabilir ----------------------------

    def test_enable_writes_our_socks_settings(self):
        m = self._manager()
        self.assertTrue(m.enable_proxy())
        self.assertEqual(self._store.values["ProxyEnable"], 1)
        self.assertEqual(self._store.values["ProxyServer"], "socks=127.0.0.1:1080")
        self.assertTrue(m.is_enabled)
        self.assertTrue(m._owns_proxy)

    def test_disable_after_own_enable_clears_proxy(self):
        m = self._manager()
        m.enable_proxy()
        self.assertTrue(m.disable_proxy())
        self.assertEqual(self._store.values["ProxyEnable"], 0)
        self.assertFalse(m.is_enabled)
        self.assertFalse(m._owns_proxy)

    def test_disable_is_noop_when_proxy_already_off(self):
        m = self._manager({"ProxyEnable": 0})
        self.assertTrue(m.disable_proxy())
        self.assertEqual(self._store.values["ProxyEnable"], 0)

    # --- Baska uygulamaya ait proxy / foreign proxy ------------------------------

    def test_enable_refuses_over_foreign_proxy(self):
        foreign = {"ProxyEnable": 1, "ProxyServer": "http=10.0.0.5:8080"}
        m = self._manager(foreign)
        self.assertFalse(m.enable_proxy())  # yeni yazma yapmadi
        self.assertEqual(self._store.values["ProxyServer"], "http=10.0.0.5:8080")
        self.assertEqual(self._store.values["ProxyEnable"], 1)
        self.assertTrue(m.has_foreign_proxy())

    def test_disable_refuses_on_foreign_proxy(self):
        foreign = {"ProxyEnable": 1, "ProxyServer": "http=10.0.0.5:8080"}
        m = self._manager(foreign)
        self.assertFalse(m.disable_proxy())
        self.assertEqual(self._store.values["ProxyEnable"], 1)  # ayara dokunulmadi
        self.assertTrue(m.has_foreign_proxy())

    def test_leftover_own_proxy_is_cleanable_at_startup(self):
        leftover = {"ProxyEnable": 1, "ProxyServer": "socks=127.0.0.1:1080"}
        m = self._manager(leftover)
        self.assertFalse(m.has_foreign_proxy())
        self.assertTrue(m.is_our_proxy_active())
        self.assertTrue(m.disable_proxy())
        self.assertEqual(self._store.values["ProxyEnable"], 0)

    def test_owning_flag_guides_safe_teardown(self):
        m = self._manager()
        m.enable_proxy()
        m._owns_proxy = True
        m._safe_teardown()  # atexit guvenli kapanma davranisi
        self.assertEqual(self._store.values["ProxyEnable"], 0)

    def test_teardown_skips_when_not_owned(self):
        foreign = {"ProxyEnable": 1, "ProxyServer": "http=10.0.0.5:8080"}
        m = self._manager(foreign)
        m._safe_teardown()  # owns=False: hicbir yazma yapmamali
        self.assertEqual(self._store.values["ProxyEnable"], 1)

    def test_error_paths_return_false_and_keep_state(self):
        m = self._manager()
        with patch("core.windows_proxy.winreg.QueryValueEx", side_effect=OSError("boom")):
            self.assertEqual(m.get_current_proxy_server(), "")
            self.assertFalse(m.is_our_proxy_active())
            self.assertFalse(m.has_foreign_proxy())


if __name__ == "__main__":
    unittest.main()
