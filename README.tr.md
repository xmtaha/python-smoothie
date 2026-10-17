# Smoothie (Python Surumu) - Ag Birlestirici ve Yuk Dengeleyici

[English](README.md) | [Türkçe](README.tr.md)

Smoothie, birden fazla internet baglantisini (ornegin: Kablolu Ethernet + Wi-Fi veya Ethernet + Telefon USB Baglantisi / Tethering) birlestirerek toplam internet bant genisliginizi ortak kullanmanizi saglayan bir Windows uygulamasidir.

Bu proje, Seth Stalley tarafindan gelistirilen acik kaynakli [SethStalley/network-smoothie](https://github.com/SethStalley/network-smoothie) projesinden **Gemini 3.8 Flash** tarafindan tamamen Python diline portlanmis, guvenlik aciklari kapatilmis ve modern ozelliklerle yeniden insa edilmistir.

---

## Orijinal Proje ve Portlanma Nedeni

Orijinal uygulama (SethStalley/network-smoothie), Node.js, Electron ve CoffeeScript ile yazilmis olan `dispatch-proxy` paketini temel almaktaydi. Yapilan kod incelemesinde orijinal projede asagidaki kritik sorunlar tespit edilmistir:

1. **Sistem Internetinin Kilitlenmesi Riski:** Uygulama beklenmedik bir sekilde kapandiginda veya coktugunde Windows kayit defterindeki proxy ayari acik kalmakta ve bilgisayarin tum internet baglantisi kopmaktaydi.
2. **Hantal PowerShell Entegrasyonu:** Proxy ayarlarini yenilemek icin her seferinde arka planda `powershell.exe -ExecutionPolicy Bypass` calistirilmakta, bu durum gecikmeye (2-3 saniye) ve guvenlik yazilimlari tarafindan engellenmeye yol acmaktaydi.
3. **IPv6 ve Gecersiz Ag Karti Hatalari:** Ag karti algilama dongusu IPv4/IPv6 ayrimi yapmadigi icin link-local IPv6 adreslerini secip baglantilari cokertmekteydi. Sanal ag kartlari (Hyper-V, VirtualBox, WSL) filtrelenmemekteydi.
4. **Kaynak Tuketime ve Zombi Surecler:** Uygulama kapatildiginda proxy sunucusu arkada asili kalmakta (`Smoothie.exe` zombi surecler olarak 1080 portunu bloke etmekte) ve Chromium motoru yuzunden 300+ MB RAM harcamaktaydi.
5. **Baglanti Takilmalari ve Hizin Sifira Dusmesi:** Nagle gecikmesi ve hatali oran dagitimi sebebiyle coklu baglanti kullanan servislerde (Steam, Speedtest, IDM) baglanti kopmalari ve hizin dalgalanmasi yasaniyordu.

Bu sorunlari kalici olarak cozmek adina proje tumuyle saf Python standart kitapliklari temel alinarak sifirdan yazilmistir.

---

## Teknik Ozellikler ve Son Guncellemeler

- **Gemini 3.8 Flash Tarafindan Portlandi:** Eski Node.js/Electron/CoffeeScript yapisi tamamen kaldirilarak modern Python 3 mimarisine gecildi.
- **Uclu Hibrit (Tri-Hybrid) Proxy Motoru:** Ayni port (`127.0.0.1:1080`) uzerinden uc farkli protokol tipini ilk baytindan otomatik tespit ederek yonetir:
  - **HTTP/HTTPS CONNECT Proxy:** Firefox, Edge ve genel tarayicilarin guvenli web isteklerini tüneller (`HTTP/1.1 200 Connection Established`).
  - **SOCKS5 Proxy:** Chrome, Steam, Speedtest, Torrent istemcileri ve oyunlar icin tam uyumlu SOCKS5 destegi.
  - **SOCKS4/SOCKS4a Proxy:** Eski Windows araclari icin yedek protokol destegi.
- **Least-Connections ve Round-Robin Yuk Dengeleme Algoritmasi:**
  - Aktif adaptorlerin anlik yuklerini takip eder.
  - Baglanti yukleri esit oldugunda Round-Robin ile hatlar arasinda dengeli dagitim yapar.
  - Steam, Speedtest ve IDM gibi coklu indirmelerde hatlari tam %50-%50 oraninda paylastirarak iki agin ortak hizini tek potada birlestirir.
- **Sifir Takilmali (Zero-Stall) Yuksek Hizli Tunelleme:**
  - `TCP_NODELAY` aktif edilerek Nagle gecikmesi sonlandirildi.
  - Soket tamponlari 256 KB boyutuna genisletildi.
  - Cift yonlu soket kapatma mekanizmasi sayesinde Steam indirmelerinde hizin 0'a vurmasi engellendi.
- **Windows C-API ile Sifir Gecikme:** PowerShell bagimliligi kaldirilmistir. Windows kayit defteri `winreg` ile dogrudan yonetilmekte, ayarlar ise `ctypes.windll.wininet.InternetSetOptionW` C-API cagrisi ile 0 milisaniyede aninda devreye sokulmaktadir.
- **Cokme Korumasi (Crash-Safe Guard) ve Gunluk Dosyasi:**
  - `atexit` ve isletim sistemi sinyal (`SIGINT`, `SIGTERM`) yakalayicilari entegre edilmistir. Uygulama kapandigi an Windows proxy ayari otomatik sifirlanir.
  - Global `sys.excepthook` beklenmeyen hatalari `smoothie.log` dosyasina yazar ve proxy'yi derhal kapatir.
- **Cift Dil (Turkce ve Ingilizce) Destegi:** Arayuzde yer alan `TR / EN` butonu ile tek tikla aninda dil gecisi saglanir; acilista sistem dili otomatik algilanir.
- **Bellek ve Kaynak Kazanimi:** Bellek kullanimi ~300 MB seviyesinden ~35 MB seviyesine dusurulmustur.

---

## Sistem Karsilastirmasi

| Kriter | Orijinal Smoothie (Node.js / Electron) | Yeni Smoothie (Python 2.0) |
| :--- | :--- | :--- |
| Kaynak Proje | SethStalley/network-smoothie | Gemini 3.8 Flash tarafindan portlandi |
| Desteklenen Protokoller | Yalnizca SOCKS5 | Uclu Hibrit (HTTP CONNECT + SOCKS5 + SOCKS4) |
| Proxy Degistirme Yontemi | powershell.exe spawn (hantal, 2-3s gecikme) | ctypes WinINet C-API (0 ms, aninda) |
| Cokme Korumasi | Yok (Internet kilitlenebiliyordu) | Var (atexit + sinyaller + smoothie.log) |
| Yuk Dengeleme Mantigi | Basit oncelik hesaplama | Least-Connections + Round-Robin tie-breaker |
| Ag Tespiti | Tum arayuzler (IPv6 link-local dahil) | Sadece Default Gateway'li aktif IPv4 |
| RAM Tukitimi | ~300 MB | ~35 MB |
| Harici Bagimlilik | Yuzlerce MB node_modules | Sifir (Python yerlesik modulleri) |

---

## Calistirma Yontemleri

### 1. Grafik Kullanici Arayuzu (GUI):
Uygulamayi Windows Python Launcher uzerinden baslatabilirsiniz:
```bash
py python-smoothie/main.py
```
*(Istege bagli dil tercihi ile: `py python-smoothie/main.py --lang tr`)*

### 2. Terminal Modu (CLI / Headless):
Arayuz olmadan dogrudan arka plan servisi olarak calistirmak icin:
```bash
py python-smoothie/main.py --cli
```
*(Dil secenegi ile: `py python-smoothie/main.py --cli --lang tr`)*

---

## Calisma Mantigi

Uygulama yerel bir coklu protokol vekil sunucusu (`127.0.0.1:1080`) baslatir:
1. Sistemdeki aktif internet baglantilari taranir (ornegin: Kablolu Ethernet ve Telefon USB Baglantisi).
2. Windows internet ayarlari yerel proxy'ye yonlendirilir; loopback (`127.0.0.1`, `localhost`) haric tutulur.
3. Gelen her yeni baglanti istegi sirayla en az yuklu ag kartinin yerel IP adresine baglanarak (`sock.bind((adapter_ip, 0))`) disari cikartilir.
4. Coklu baglanti destekleyen indirme yoneticileri (Steam, Speedtest, Torrent istemcileri veya coklu sekme kullaniminda) toplam bant genisligi ortak kullanilir.

---

## Proje Dizin Yapisi

```
network-smoothie-main/
|-- README.md                  # Ingilizce dokumantasyon
|-- README.tr.md               # Turkce dokumantasyon
|
`-- python-smoothie/           # Python Uygulama Paketi
    |-- main.py                # Giris noktasi (GUI ve CLI destegi)
    |-- requirements.txt       # Gereksinimler (Sifir harici bagimlilik)
    |-- test_core.py           # Otomatik birim ve entegrasyon testi
    |-- smoothie.log           # Teshis ve hata gunlugu
    |
    |-- core/
    |   |-- i18n.py            # Cift dilli ceviri sozlugu (TR / EN)
    |   |-- windows_proxy.py   # Registry & WinINet C-API yonetimi (Crash-Safe)
    |   |-- network_detector.py# Ag karti ve Gateway algilama modulu
    |   `-- proxy_engine.py    # Uclu hibrit yuk dengeleyici proxy motoru
    |
    `-- ui/
        `-- gui.py             # Koyu tema Tkinter kullanici arayuzu
```

---

## Bagimsiz Calistirilabilir (.exe) Dosyasi Uretme

Uygulamayi Python kurulu olmayan bilgisayarlarda da calistirmak uzere tek bir `.exe` dosyasina donusturmek icin:

```bash
py -m pip install pyinstaller
pyinstaller --noconsole --onefile --name "Smoothie" python-smoothie/main.py
```
Olusan calistirilabilir dosya `dist/Smoothie.exe` konumunda yer alacaktir.
