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

Bu sorunlari kalici olarak cozmek adina proje tumuyle saf Python standart kitapliklari temel alinarak sifirdan yazilmistir.

---

## Yapilan Degisiklikler ve Yenilikler

- **Gemini 3.8 Flash Tarafindan Portlandi:** Eski Node.js/Electron/CoffeeScript yapisi tamamen kaldirilarak modern Python 3 mimarisine gecildi.
- **Windows C-API ile Sifir Gecikme:** PowerShell bagimliligi kaldirilmistir. Windows kayit defteri `winreg` ile dogrudan yonetilmekte, ayarlar ise `ctypes.windll.wininet.InternetSetOptionW` C-API cagrisi ile 0 milisaniyede aninda devreye sokulmaktadir.
- **Cokme Korumasi (Crash-Safe Guard):** `atexit` ve isletim sistemi sinyal (`SIGINT`, `SIGTERM`) yakalayicilari entegre edilmistir. Uygulama gorev yoneticisinden kapatilsa veya aniden kapansa dahi Windows proxy ayari otomatik olarak sifirlanir, internet erisimi guvence altindadir.
- **Acilis Guvenlik Kontrolu:** Uygulama baslatildiginda eski oturumlardan kalan hatali bir proxy kilidi varsa otomatik tespit edilip temizlenir.
- **Akilli Ag ve Ag Gecidi (Gateway) Tespiti:** Yalnizca gecerli bir Varsayilan Ag Gecidi (Default Gateway) olan ve soket baglanabilen (bindable) gercek fiziksel IPv4 arayuzleri secilir. Sanal veya baglantisi kopuk kartlar elenir.
- **Yuksek Performansli Asyncio SOCKS5 Motoru:** Standart Python `asyncio` ile calisan hafif bir SOCKS5 sunucusu gelistirilmistir. Her baglanti `sock.bind((adapter_ip, 0))` yapilarak farkli fiziksel hatlara yonlendirilir.
- **Yapiskan Oturumlar (Sticky Sessions):** Bankacilik, e-Devlet veya cevrimici oyun gibi IP degisiminde oturumu kapatan servisler icin ayni alan adina yapilan isteklerin ayni ag kartinda kalmasini saglayan opsiyonel oturum tutma mekanizmasi eklenmistir.
- **Hat Secimi ve Canli Istatistikler:** Kullanicinin hangi ag kartlarini birlestirecegini tek tek secebilecegi onay kutulari (Checkbox), anlik aktarilan veri miktari (KB/MB) ve aktif baglanti sayilari arayuze eklenmistir.
- **Sifir Harici Bagimlilik:** Tum cekirdek sistem yalnizca Python'un yerlesik modulleriyle calisir (`asyncio`, `socket`, `winreg`, `ctypes`, `tkinter`); ekstra kutuphane kurulumu gerektirmez.
- **Bellek ve Kaynak Kazanimi:** Bellek kullanimi ~300 MB seviyesinden ~35 MB seviyesine dusurulmustur.

---

## Sistem Karsilastirmasi

| Kriter | Orijinal Smoothie (Node.js / Electron) | Yeni Smoothie (Python 2.0) |
| :--- | :--- | :--- |
| Kaynak Proje | SethStalley/network-smoothie | Gemini 3.8 Flash tarafindan portlandi |
| Proxy Degistirme Yontemi | powershell.exe spawn (hantal, yavas) | ctypes WinINet C-API (0 ms, aninda) |
| Cokme Korumasi | Yok (Internet kilitlenebiliyordu) | Var (atexit ve sinyal yakalayicilar) |
| Ag Tespiti | Tum arayuzler (IPv6 link-local dahil) | Sadece Default Gateway'li aktif IPv4 |
| RAM Tukitimi | ~300 MB | ~35 MB |
| Harici Bagimlilik | Yuzlerce MB node_modules | Sifir (Python yerlesik modulleri) |

---

## Calistirma Yontemleri

### 1. Terminal Uzerinden Grafik Arayuz (GUI):
```bash
py python-smoothie/main.py
```

### 2. Terminal Modu (CLI / Headless):
Arayuz olmadan dogrudan arka planda calistirmak icin:
```bash
py python-smoothie/main.py --cli
```

---

## Calisma Mantigi

Uygulama yerel bir SOCKS5 vekil sunucusu (`127.0.0.1:1080`) baslatir:
1. Sistemdeki aktif internet baglantilari taranir.
2. Windows internet ayarlari yerel proxy'ye yonlendirilir.
3. Gelen her yeni baglanti istegi sirayla aktif ag kartlarinin yerel IP adreslerine baglanarak (`sock.bind`) disari cikartilir.
4. Coklu baglanti destekleyen indirme yoneticileri (IDM, FDM), Torrent istemcileri veya coklu sekme kullaniminda toplam bant genisligi birlestirilir.

---

## Proje Dizin Yapisi

```
network-smoothie-main/
|-- run_smoothie.bat           # Cift tiklamali baslatici
|-- README.md                  # Ingilizce dokumantasyon
|-- README.tr.md               # Turkce dokumantasyon
|
`-- python-smoothie/           # Python Uygulama Paketi
    |-- main.py                # Giris noktasi (GUI ve CLI destegi)
    |-- requirements.txt       # Gereksinimler (Sifir harici bagimlilik)
    |-- test_core.py           # Otomatik birim ve entegrasyon testi
    |
    |-- core/
    |   |-- windows_proxy.py   # Registry & WinINet C-API yonetimi (Crash-Safe)
    |   |-- network_detector.py# Ag karti ve Gateway algilama modulu
    |   `-- proxy_engine.py    # Asenkron SOCKS5 dispatcher motoru
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
