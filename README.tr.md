# Smoothie (Python Surumu) - Ag Birlestirici ve Yuk Dengeleyici

[English](README.md) | [Türkçe](README.tr.md)

Smoothie, birden fazla internet baglantisini (ornegin: Kablolu Ethernet + Wi-Fi veya Ethernet + Telefon USB Baglantisi / Tethering) birlestirerek toplam internet bant genisliginizi ortak kullanmanizi saglayan hafif, guvenli ve yuksek performansli bir Windows uygulamasidir.

Bu proje, Seth Stalley tarafindan gelistirilen acik kaynakli [SethStalley/network-smoothie](https://github.com/SethStalley/network-smoothie) projesinin (orijinalde Node.js / Electron) tamamen Python ile yeniden yazilmis surumudur.

---

## Ozellikler

- **Uclu Hibrit (Tri-Hybrid) Proxy Motoru:** Ayni port (`127.0.0.1:1080`) uzerinden uc farkli protokol tipini ilk baytindan otomatik tespit ederek yonetir:
  - **HTTP/HTTPS CONNECT Proxy:** Firefox, Edge ve genel tarayicilarin guvenli web isteklerini tüneller (`HTTP/1.1 200 Connection Established`).
  - **SOCKS5 Proxy:** Chrome, Steam, Speedtest, Torrent istemcileri ve oyunlar icin tam uyumlu SOCKS5 destegi.
  - **SOCKS4/SOCKS4a Proxy:** Eski Windows araclari icin yedek protokol destegi.
- **Least-Connections Yuk Dengeleme + Round-Robin Estitirme:** Aktif adaptorlerin anlik yuklerini takip eder; baglantilari hatlar arasinda dengeli dagitir. Steam, Speedtest ve IDM gibi coklu indirmelerde hatlarin ortak bant genisligi kullanilir.
- **Sifir Takilmali (Zero-Stall) Yuksek Hizli Tunelleme:** `TCP_NODELAY` aktif, 256 KB soket tamponlari ve cift yonli soket kapatma ile hiz sifira vurmaz.
- **Windows C-API ile Sifir Gecikme:** Kayit defteri `winreg` ile dogrudan yonetilmekte, ayarlar `ctypes.windll.wininet.InternetSetOptionW` C-API cagrisi ile 0 milisaniyede devreye alinmaktadir (powershell.exe calistirilmaz).
- **Proxy Sahiplik Guvenligi:** Smoothie yalnizca kendi actigi sistem proxy'sini (`socks=127.0.0.1:1080`) yonetir. Sistem proxy'si baska bir uygulama tarafindan yonetiliyor ise Smoothie uyarir ve o ayarlara kesinlikle dokunmaz. Bir onceki oturumdan kalma Smoothie proxy ayarlari acilista otomatik temizlenir.
- **Cokme Korumasi (Crash-Safe Guard):** `atexit`, isletim sistemi sinyalleri (`SIGINT`, `SIGTERM`) ve global `sys.excepthook` ile uygulama ne sekilde kapanirsa kapansin yalnizca bize ait proxy ayari geri alinir; beklenmeyen hatalar `smoothie.log` dosyasina yazilir.
- **Cift Dil (Turkce ve Ingilizce) Destegi:** Arayuzde yer alan `TR / EN` butonu ile tek tikla aninda dil gecisi; acilista sistem dili otomatik algilanir.
- **Sifir Bagimlilik:** Tamamı saf Python 3 standart kutuphanesidir; normal kullanimda hicbir harici paket gerekmez.

---

## Gereksinimler

- Windows 10 / 11
- Kaynaktan calistirmak icin Python 3.10+

---

## Calistirma Yontemleri

### Windows calistirilabilir dosyasi (onerilen)

GitHub Releases sayfasindan `Smoothie.exe` dosyasini indirin, dilediginiz klasore koyun ve cift tiklayarak calistirin. Python kurulu olmasi gerekmez.

- `Smoothie.exe` – Pencere (GUI) surumu. Fazladan konsol penceresi acmaz.
- `SmoothieCLI.exe` – Terminal / headless kullanim icin konsol surumu.

Her iki surum de asagidaki komut satiri seceneklerini destekler; pencere surumu `--cli` bayragiyle headless modda da calisabilir (log dosyasi EXE yanindaki `smoothie.log`).

### Kaynaktan

Grafik Kullanici Arayuzu (GUI):
```bash
py main.py
```
Istege bagli dil tercihi: `py main.py --lang en`

Terminal Modu (CLI / Headless):
```bash
py main.py --cli
```
Dil seceneginin komut ile: `py main.py --cli --lang en`

### Komut Satiri Secenekleri

| Secenek | Aciklama | Varsayilan |
| :--- | :--- | :--- |
| `--cli` | GUI olmadan terminal modunda calistir | kapali |
| `--host` | Yerel proxy baglama adresi | `127.0.0.1` |
| `--port` | SOCKS5 proxy portu | `1080` |
| `--lang` | Arayuz / CLI dili (`tr` veya `en`) | otomatik algilanir |
| `--version` | Surum bilgisi yazip cikar | - |

---

## Calisma Mantigi

Uygulama yerel bir coklu protokol vekil sunucusu (`127.0.0.1:1080`) baslatir:
1. Sistemdeki aktif internet baglantilari taranir (ornegin: Kablolu Ethernet ve Telefon USB Baglantisi); yalnizca varsayilan ag gecidi dogrulanmis fiziksel IPv4 adaptörleri kullanilir.
2. Windows internet ayarlari yerel proxy'ye yonlendirilir; loopback (`127.0.0.1`, `localhost`) haric tutulur.
3. Gelen her yeni baglanti isteginde protokol tipi kontrol edilir, en az yuklu ag karti secilir ve disari cikan soket o kartin yerel IP adresine baglanarak (`sock.bind((adapter_ip, 0))`) cikartilir.
4. Coklu baglanti destekleyen uygulamalar (Steam, Speedtest, Torrent istemcileri, coklu sekme) akislarini tum hatlara dagitir; toplam bant genisligi ortak kullanilir.

---

## Testleri Calistirma

Cevrimdisi unit testler (internet, registry veya ag degisikligi gerekmez; her yerde guvenle calisir):
```bash
py -m unittest discover -s tests -v
```

`test_core.py` ayri bir **entegrasyon testidir**; gercek ag adaptörleri ve internet baglantısı ister. En az iki aktif hat varken yalnizca manuel calistirin:
```bash
py test_core.py
```

---

## Sorun Giderme

- **"Port 1080 baska bir uygulama tarafindan kullaniliyor"** – 1080 portunda baska bir program dinliyor. O uygulamayi kapatiny veya Smoothie'yi farkli port ile baslatin (`--port 1081`).
- **"Sistem proxy'si baska bir uygulama tarafindan yonetiliyor"** – Windows proxy ayarlarini baska bir yazilim (VPN, kurumsal proxy vb.) aktif kullaniyor. Smoothie bu ayara dokunmaz; once o proxy'yi kapatip birlestirmeyi baslatin.
- **Cokme sonrasi internet geri gelmedi mi?** Smoothie yalnizca kendisinin actigi ayari geri alir. Proxy baska bir aracila kapatildiysa kendi ag ayarlarinizi elle kontrol edin.
- Tani gunlukleri, calistirilabilir dosyanin / scriptin yanindaki `smoothie.log` dosyasindadir.

---

## Proje Dizin Yapisi

```
python-smoothie/
|-- README.md                  # Ingilizce dokumantasyon
|-- README.tr.md               # Turkce dokumantasyon
|
|-- main.py                    # Giris noktasi (GUI ve CLI destegi)
|-- test_core.py               # Manuel entegrasyon testi (aktif ag ister)
|-- smoothie.log               # Calisma anı tani gunlugu (uretilir, commit edilmez)
|
|-- core/
|   |-- version.py             # Uygulama surumunun tek kaynagi
|   |-- i18n.py                # Cift dilli ceviri sozlugu (TR / EN)
|   |-- windows_proxy.py       # Sahiplik-guvenli Registry & WinINet C-API yonetimi
|   |-- network_detector.py    # Ag karti ve Gateway algilama modulu
|   `-- proxy_engine.py        # Uclu hibrit yuk dengeleyici proxy motoru
|
|-- tests/                     # Cevrimdisi unit testler (unittest)
|   |-- test_engine_logic.py
|   |-- test_engine_socks.py
|   `-- test_windows_proxy.py
|
`-- ui/
    `-- gui.py                 # Koyu tema Tkinter kullanici arayuzu
```

---

## Bagimsiz Calistirilabilir (.exe) Dosyasi Uretme

Uygulamayi Python kurulu olmayan bilgisayarlar da calistirmak icin tek bir `.exe` dosyasina donus turmek icin:

```bash
py -m pip install pyinstaller
py -m PyInstaller --noconsole --onefile --name "Smoothie" main.py
py -m PyInstaller --onefile --name "SmoothieCLI" main.py
```

Olusan calistirilabilir dosyalar `dist/` klasorunde yer alir. Build tekrar edilebilirdir (reproducible); `build/`, `dist/` ve uretilecek `.spec` dosyasi depoya eklenmez.

---

## Lisans

Lisans detaylari icin [LICENSE](LICENSE) dosyasina bakiniz.
