# Smoothie (Python Edition) - Network Blender and Load Balancer

[English](README.md) | [Türkçe](README.tr.md)

Smoothie is a lightweight, secure, and high-performance Windows application that blends multiple internet connections (such as Wired Ethernet + Wi-Fi, or Ethernet + Mobile USB Tethering) together to share and maximize your aggregate network bandwidth across all active connections.

This project is a pure-Python rewrite of the open-source [SethStalley/network-smoothie](https://github.com/SethStalley/network-smoothie) project (originally Node.js / Electron).

---

## Features

- **Tri-Hybrid Multi-Protocol Engine:** Operates simultaneously on a single port (`127.0.0.1:1080`), automatically detecting incoming traffic protocols:
  - **HTTP/HTTPS CONNECT Proxy:** Seamless support for Firefox, Edge, and general web browser HTTPS tunneling (`HTTP/1.1 200 Connection Established`).
  - **SOCKS5 Proxy:** Standard support for Chrome, Steam, Speedtest, Torrent clients, and games.
  - **SOCKS4/SOCKS4a Proxy:** Full fallback for legacy Windows utilities.
- **Least-Connections Balancer with Round-Robin tie-breaking:** Active socket loads on each adapter are evaluated in real time and streams are distributed evenly across all lines, allowing multi-connection applications (Steam, Speedtest, download managers) to use aggregated bandwidth.
- **Zero-Stall High-Throughput Tunneling:** `TCP_NODELAY` enabled, 256 KB socket buffers, rapid bidirectional socket shutdown to avoid half-open stalls.
- **Zero-Latency Windows C-API:** Registry settings are managed directly via `winreg`; WinINet option updates are applied instantly (0 ms) via `ctypes.windll.wininet.InternetSetOptionW` (no `powershell.exe` spawning).
- **Proxy Ownership Safety:** Smoothie only touches the system proxy it set itself (`socks=127.0.0.1:1080`). If the system proxy is managed by another application, Smoothie warns and never overwrites or disables it. Leftover settings from a previous Smoothie session are cleaned up on startup.
- **Crash-Safe Guard:** `atexit`, signal handlers (`SIGINT`, `SIGTERM`) and a global `sys.excepthook` make sure the proxy is only reverted when it actually belongs to Smoothie; unexpected errors are written to `smoothie.log`.
- **Bilingual Interface (Turkish / English):** Real-time language switch button (`TR / EN`) with automatic system locale detection at startup.
- **Zero Dependencies:** Pure Python 3 standard library; no third-party packages required for normal use.

---

## Requirements

- Windows 10 / 11 (of any edition)
- Python 3.10+ (only when running from source)

---

## How to Run

### Windows Executable (recommended)

Download `Smoothie.exe` from the project's GitHub Releases, place it in any folder, and run it by double-clicking. No Python installation required.

- `Smoothie.exe` – Windowed application (GUI). Does not open a console window.
- `SmoothieCLI.exe` – Console build for terminal/headless usage.

Both support the CLI options below; the windowed build also accepts `--cli` to run headless (logs go to `smoothie.log` next to the EXE).

### From Source

Graphical User Interface (GUI):
```bash
py main.py
```
Optional language flag: `py main.py --lang en`

Headless / Terminal mode (CLI):
```bash
py main.py --cli
```
With language preference: `py main.py --cli --lang en`

### Command Line Options

| Option | Description | Default |
| :--- | :--- | :--- |
| `--cli` | Run in headless terminal mode without the GUI | disabled |
| `--host` | Local proxy bind address | `127.0.0.1` |
| `--port` | SOCKS5 proxy port | `1080` |
| `--lang` | UI / CLI language (`tr` or `en`) | auto-detected |
| `--version` | Print the version and exit | – |

---

## Architecture and How It Works

Smoothie initializes a local multi-protocol proxy server on `127.0.0.1:1080`:
1. It discovers all physical network adapters with a verified Default Gateway (e.g., Ethernet and Mobile USB Tethering).
2. It configures Windows Internet Settings to forward traffic to the local proxy, keeping loopback (`127.0.0.1`, `localhost`) unintercepted.
3. For each incoming connection, the engine checks protocol headers, selects the least-loaded adapter, and binds the outbound socket to that adapter's local IP address (`sock.bind((adapter_ip, 0))`).
4. Multi-connection applications (Steam, Speedtest, torrent engines, multi-tab browsers) distribute their streams across all adapters, effectively combining their throughput.

---

## Running the Tests

Offline unit tests (no internet, no registry changes — safe to run anywhere):
```bash
py -m unittest discover -s tests -v
```

`test_core.py` is a separate, manual **integration test** that requires real network adapters and internet access; run it only when at least two live connections are present:
```bash
py test_core.py
```

---

## Troubleshooting

- **"Port 1080 is being used by another application"** – Another program is listening on port 1080. Close that application or start Smoothie with a different port (`--port 1081` in CLI/EXE mode).
- **"The system proxy is managed by another application"** – Windows proxy is currently controlled by another program (VPN, corporate proxy, etc.). Smoothie does not modify it; disable that proxy first, then start blending.
- **Internet not restored after a crash?** Smoothie only reverts proxy settings it set itself. If the proxy was disabled by another tool, re-enable your usual settings manually.
- Diagnostic logs are written to `smoothie.log` next to the executable / script.

---

## Project Structure

```
python-smoothie/
|-- README.md                  # English documentation
|-- README.tr.md               # Turkish documentation
|
|-- main.py                    # Application entry point (GUI and CLI)
|-- test_core.py               # Manual integration test (needs live network)
|-- smoothie.log               # Runtime diagnostic log (generated, not committed)
|
|-- core/
|   |-- version.py             # Single source of truth for the app version
|   |-- i18n.py                # Bilingual translation dictionary (TR / EN)
|   |-- windows_proxy.py       # Ownership-safe Registry & WinINet C-API controller
|   |-- network_detector.py    # Adapter and default gateway discovery
|   `-- proxy_engine.py        # Tri-hybrid proxy & load balancing engine
|
|-- tests/                     # Offline unit tests (unittest, no internet needed)
|   |-- test_engine_logic.py
|   |-- test_engine_socks.py
|   `-- test_windows_proxy.py
|
`-- ui/
    `-- gui.py                 # Dark theme bilingual Tkinter interface
```

---

## Building a Standalone Executable (.exe)

To bundle the application into executables that run without Python installed:

```bash
py -m pip install pyinstaller
py -m PyInstaller --noconsole --onefile --name "Smoothie" main.py
py -m PyInstaller --onefile --name "SmoothieCLI" main.py
```

The resulting executables are located in the `dist/` directory. The build is reproducible; `build/`, `dist/` and the generated `.spec` file are not committed.

---

## License

See [LICENSE](LICENSE).
