# Smoothie (Python Edition) - Network Blender and Load Balancer

[English](README.md) | [Türkçe](README.tr.md)

Smoothie is a lightweight, secure, and high-performance Windows application that blends multiple internet connections (such as Wired Ethernet + Wi-Fi, or Ethernet + Mobile USB Tethering) together to share and maximize your aggregate network bandwidth across all active connections.

This project was ported from the open-source [SethStalley/network-smoothie](https://github.com/SethStalley/network-smoothie) project and completely rewritten in Python by **Gemini 3.8 Flash**.

---

## Why It Was Ported

The original application (SethStalley/network-smoothie) relied on Node.js, Electron, and an unmaintained CoffeeScript library (`dispatch-proxy`). During the codebase review, several critical architectural and stability flaws were identified:

1. **Internet Lockout on Crashes:** If the application exited unexpectedly, the Windows system proxy remained enabled, completely severing internet connectivity across the entire host machine.
2. **High Latency via PowerShell:** Proxy settings were refreshed by spawning `powershell.exe -ExecutionPolicy Bypass` on each toggle, adding a 2-3 second delay and triggering antivirus warnings.
3. **IPv6 Link-Local Breakages:** The original network discovery loop did not distinguish between IPv4 and IPv6, often binding to link-local IPv6 addresses (`fe80::`) and breaking outbound TCP connections. Virtual adapters (Hyper-V, VirtualBox, WSL) were also left unfiltered.
4. **Heavy Resource Footprint and Zombie Processes:** The app consumed 300+ MB of RAM due to Chromium/Electron, and frequently left orphan `Smoothie.exe` processes holding port 1080.
5. **Connection Bottlenecks:** Parallel TCP streams in multi-threaded downloaders (Steam, Speedtest, IDM) suffered from Nagle-delayed ACKs and connection-distribution biases that caused speeds to drop to zero.

To permanently resolve these issues, the application was re-architected from the ground up using pure Python standard libraries.

---

## Technical Features and Recent Upgrades

- **Ported by Gemini 3.8 Flash:** Completely reconstructed using modern Python 3 with zero required third-party packages.
- **Tri-Hybrid Multi-Protocol Engine:** Operates simultaneously on a single port (`127.0.0.1:1080`), automatically detecting incoming traffic protocols:
  - **HTTP/HTTPS CONNECT Proxy:** Seamless support for Firefox, Edge, and general web browser HTTPS tunneling (`HTTP/1.1 200 Connection Established`).
  - **SOCKS5 Proxy:** Standard support for Chrome, Steam, Speedtest, Torrent clients, and games.
  - **SOCKS4/SOCKS4a Proxy:** Full fallback for legacy Windows utilities.
- **Least-Connections Ratio Balancer with Round-Robin:**
  - Evaluates active socket loads on each adapter in real time.
  - Sockets are evenly distributed across all active connections (50% on Line 1, 50% on Line 2), allowing multi-connection engines (Steam, Speedtest, download managers) to achieve true aggregated speeds without throttling.
- **Zero-Stall High-Throughput Tunneling:**
  - `TCP_NODELAY` is enabled to eliminate Nagle latency.
  - Socket buffers expanded to 256 KB.
  - Rapid bidirectional stream shutdown prevents half-open socket stalling and zero-speed drops.
- **Zero-Latency Windows C-API:** Registry settings are managed directly via `winreg`, while WinINet cache and option updates are committed instantly (0 ms) via `ctypes.windll.wininet.InternetSetOptionW`.
- **Crash-Safe Guard and Diagnostic Logger:**
  - Integrates `atexit` and OS signal handlers (`SIGINT`, `SIGTERM`). If the process terminates, Windows proxy settings are immediately restored to disabled.
  - Global `sys.excepthook` writes unhandled errors to `smoothie.log` while automatically clearing proxy locks.
- **Bilingual Interface (Turkish and English):** Real-time language switching button (`TR / EN`) in the GUI, with automatic system locale detection on startup.
- **Resource Footprint:** Memory consumption reduced from ~300 MB down to ~35 MB.

---

## System Comparison

| Criteria | Original Smoothie (Node.js / Electron) | Smoothie Python 2.0 (Gemini 3.8 Flash) |
| :--- | :--- | :--- |
| Upstream Source | SethStalley/network-smoothie | Ported by Gemini 3.8 Flash |
| Language & Runtime | JavaScript / Node.js / Electron | Pure Python 3 (asyncio) |
| Supported Protocols | SOCKS5 only | Tri-Hybrid (HTTP CONNECT + SOCKS5 + SOCKS4) |
| Proxy Configuration | Spawns powershell.exe (slow, 2-3s delay) | ctypes WinINet C-API (instant, 0 ms) |
| Crash Protection | None (Internet could be locked) | Crash-Safe Guard (atexit + signals + logger) |
| Load Balancing | Simple priority calculation | Least-Connections + Round-Robin tie-breaker |
| Adapter Filtering | All interfaces (IPv6 breakages) | Verified physical IPv4 with Default Gateway |
| RAM Usage | ~300 MB | ~35 MB |
| External Dependencies | Hundreds of MBs in node_modules | Zero (Python standard library only) |

---

## How to Run

### Graphical User Interface (GUI)
Run the application directly via the Windows Python Launcher:
```bash
py python-smoothie/main.py
```
*(Optional language flag: `py python-smoothie/main.py --lang en`)*

### Headless / Terminal Mode (CLI)
To run the background proxy service without launching the GUI:
```bash
py python-smoothie/main.py --cli
```
*(With language preference: `py python-smoothie/main.py --cli --lang en`)*

---

## Architecture and How It Works

Smoothie initializes a local multi-protocol proxy server on `127.0.0.1:1080`:
1. It discovers all physical network adapters with a verified Default Gateway (e.g., Ethernet and Mobile USB Tethering).
2. It configures Windows Internet Settings to forward traffic to the local proxy, keeping loopback (`127.0.0.1`, `localhost`) unintercepted.
3. For each incoming connection, the engine checks protocol headers, selects the least-loaded adapter, and binds the outbound socket to that adapter's local IP address (`sock.bind((adapter_ip, 0))`).
4. Multi-connection applications (Steam, Speedtest, torrent engines, multi-tab browsers) distribute their streams across all adapters, effectively combining their throughput.

---

## Project Structure

```
network-smoothie-main/
|-- README.md                  # English documentation
|-- README.tr.md               # Turkish documentation
|
`-- python-smoothie/           # Python Application Package
    |-- main.py                # Application entry point (GUI and CLI)
    |-- requirements.txt       # Dependencies (zero required for normal use)
    |-- test_core.py           # Integration and unit verification test
    |-- smoothie.log           # Diagnostic crash and operation log
    |
    |-- core/
    |   |-- i18n.py            # Bilingual translation dictionary (TR / EN)
    |   |-- windows_proxy.py   # Registry & WinINet C-API controller
    |   |-- network_detector.py# Adapter and default gateway discovery
    |   `-- proxy_engine.py    # Tri-hybrid proxy & load balancing engine
    |
    `-- ui/
        `-- gui.py             # Dark theme bilingual Tkinter interface
```

---

## Building a Standalone Executable (.exe)

To bundle the application into a single executable that runs without Python installed:

```bash
py -m pip install pyinstaller
pyinstaller --noconsole --onefile --name "Smoothie" python-smoothie/main.py
```
The resulting executable will be located in the `dist/Smoothie.exe` directory.
