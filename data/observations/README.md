# Gözlem verileri

## `koeri_strong_motion.csv`

KOERI (Kandilli Rasathanesi ve Deprem Araştırma Enstitüsü) kuvvetli yer hareketi kayıtlarından
türetilmiş tepe değerler: 949 kayıt, 332 deprem (Mw 4.3–7.8), 74 istasyon.

- Kaynak tablo: [Ayberkrk/turkiye-deprem-verisi](https://github.com/Ayberkrk/turkiye-deprem-verisi)
  `data/processed/event_station_table.csv`, commit `ed2305c3`. Yeniden üretmek için:
  `python scripts/build_koeri_observations.py <event_station_table.csv>`
- Filtre: `usable_for_engineering`, Mw mevcut, PGV > 0, `label_ambiguous` olmayan kayıtlar
  (kayıt penceresinde etiketten daha büyük başka bir deprem bulunanlar çıkarıldı).
- PGV: iki yatay bileşenin geometrik ortalaması (cm/s). Vs30: USGS Global Vs30 Mosaic.
- `window_group`: kayıt pencereleri örtüşen depremleri birleştirir; çapraz doğrulamada grup olarak kullanılır.

**Lisans ve atıf.** Dalga formları KOERI / ORFEUS-EIDA'dan gelir ve **yalnızca akademik / ticari olmayan
kullanım** içindir (EIDA veri politikası; ticari kullanım için Boğaziçi Üniversitesi'nden yazılı izin gerekir).
Vs30 değerleri USGS (kamu malı). Bu dosyayı kullanırken KOERI'ye ve kaynak veri setine atıf yapın.

**Bilinen sınırlama.** Kaynak veri setinin belgelerine göre mutlak PGA düzeyi Akkar, Sandıkkaya & Bommer (2014)
modeline kıyasla log10'da ~0,24 düşüktür (nedeni ayrıştırılmamış).

## `usgs_observations.csv`

Altı büyük deprem için USGS ComCat ürünlerinden türetilmiş 1 324 gözlem (olay listesi: `data/events.csv`):
Kahramanmaraş (Pazarcık) 2023 `us6000jllz`, Kahramanmaraş (Elbistan) 2023 `us6000jlqa`, Elazığ 2020 `us60007ewc`,
Sisam/İzmir 2020 `us7000c7y0`, Düzce 1999 `usp0009hev`, Kocaeli (İzmit) 1999 `usp0009d4z`.
Üretmek için: `python scripts/download_data.py usgs <event_id>` ve `python scripts/build_usgs_observations.py`.

- **USGS DYFI** (`cdi_geo.txt`): ≥ 3 yanıtlı, şüpheli işaretli olmayan hücreler.
- **İstasyonlar** (ShakeMap `stationlist.json`, `station_type = seismic`): ShakeMap'in aykırı işaretlemediği
  istasyonların PGV'si (büyük yatay bileşen, cm/s). Ağ kodu TK → AFAD, KO → KOERI, diğerleri (Yunan ağları,
  1999 ağları) → "istasyon (ShakeMap)".
- **Makrosismik** (ShakeMap listesinde ağ kodu `INTENSITY`): 1999 depremlerinin gözlenen saha şiddetleri ve
  Sisam 2020 için EMSC şiddetleri. Ölçek dönüşümü uygulanmamıştır.
- **Vs30:** tüm noktalarda USGS Global Vs30 rasteri (`data/vs30/vs30_turkey.tif`, dışında küresel ızgara).
  ShakeMap listesindeki değer `vs30_shakemap` sütunundadır; AFAD istasyonlarının ~%48'inde bu değer 760 m/s
  yer tutucusudur.
- Lisans: USGS verileri kamu malıdır. İstasyon verisi AFAD, KOERI ve ilgili ağlara aittir; atıf yapın.

## `../vs30/vs30_turkey.tif`

USGS Global Vs30 Mosaic'in (Heath vd. 2020; `global_vs30.grd`, 30 yay saniyesi) 24–46°D, 33–43,5°K kırpımı.
Kaynak: https://earthquake.usgs.gov/data/vs30/ — kamu malı.
