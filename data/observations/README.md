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
