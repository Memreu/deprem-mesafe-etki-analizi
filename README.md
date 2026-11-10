# 🌍 MMI Intensity Mapper

**MMI Intensity Mapper**, kullanıcıdan alınan deprem ve konum bilgilerini kullanarak, sarsıntının farklı noktalarda nasıl hissedildiğini tahmin eden bir analiz ve görselleştirme aracıdır. Uygulama, deprem büyüklüğü (**Mw**), episantr uzaklığı ve derinlik bilgilerini temel alarak **Modified Mercalli Intensity (MMI)** değerini hesaplar ve sonuçları **etkileşimli bir HTML haritası** üzerinde görsel olarak sunar.

> Proje Python ile geliştirilmiş olup, haritalama için `folium`, mesafe hesaplamaları için `geopy`, renkli terminal çıktısı için `colorama` kullanmaktadır.

---

## 📌 Özellikler

- 📍 **DMS formatında koordinat girişi**  
  Kullanıcılar hem deprem episantrı hem de analiz yapılacak konumları DMS (derece, dakika, saniye) formatında girebilirler.
  
- 🧭 **Yüzeysel ve hiposantrik mesafe hesaplamaları**  
  En doğru sismik analiz için yer yüzeyinden ve yer altındaki depremin merkezine olan uzaklıklar hesaplanır.

- 📈 **Yayımlanmış modellerle MMI hesabı**  
  Allen vd. (2012) ve Bayrak vd. (2019) IPE'leriyle medyan MMI ve standart sapma hesaplanır.

- 🎨 **Terminalde renkli çıktı**  
  MMI şiddeti kullanıcıya renkli ve anlamlı açıklamalarla sunulur (örn: Hafif, Orta, Yıkıcı).

- 🗺️ **Etkileşimli harita çıktısı**  
  Folium kullanılarak oluşturulan HTML haritada deprem ve kullanıcı konumları işaretlenir, mesafeler ve tahmini etkiler gösterilir.

---

## 🛠️ Kurulum

Bu proje pek çok Python ile çalışır. Kütüphaneler script içerisinde otomatik olarak kurulsa da manuel kurulum için:

```bash
pip install -r requirements.txt
```

---

## 🚀 Kullanım
Uygulama çalıştırıldığında:
- 1.Depremin episantr koordinatlarını girin (örn: 39°49'39.0"N 30°32'26.9"E)
- 2.Birden fazla analiz yapılacak konum ekleyin.
- 3.Depremin derinliği ve moment büyüklüğünü (Mw) girin.

Sonuçlar:
- 📊 Terminalde açıklamalı olarak sunulur.
- 🗺️ Harita üzerinde görsel olarak sunulur. (deprem_haritasi.html)
- Harita, çalıştırılan dizine kaydedilir ve otomatik olarak tarayıcıda açılır.

--- 

## 📸 Örnek Harita Çıktısı
Harita açıklamaları:
- 🔴 Kırmızı: Deprem merkez üssü
- 🔵 Mavi: Kullanıcı konumları
- 🟠 Turuncu çizgiler: Merkez ile konum arasındaki bağlantılar
- 💬 Popup: Tahmini MMI ve mesafe bilgileri
![image](https://github.com/user-attachments/assets/f2819266-d82e-41e2-9196-3a1448202527)

---

## 📚 Teorik Arka Plan

Bir konumdaki şiddeti tahmin etmenin kabul görmüş iki yolu vardır: büyüklük ve uzaklıktan doğrudan şiddet veren **şiddet tahmin denklemleri (IPE)** ya da önce yer hareketini (PGV) tahmin edip bunu şiddete çeviren **GMPE + GMICE zinciri**. Ayrıntılar: [`docs/literatur_taramasi.pdf`](docs/literatur_taramasi.pdf).

**Kullanılan IPE'ler** (`mmi_mapper/ipe.py`):

| Model | Uzaklık | Denklem | σ (MMI) |
|---|---|---|---|
| Allen, Wald & Worden (2012), Rrup | fay uzaklığı | `3.950 + 0.913·M − 1.107·ln√(Rrup² + (1 + 0.813·e^(M−5))²)` | `0.72 + 0.23/(1+(R/44.7)²)` |
| Allen, Wald & Worden (2012), Rhyp | hiposantral | `2.085 + 1.428·M − 1.402·ln√(Rhyp² + Rm²) + 0.078·ln(Rhyp/50)` (R>50 km), `Rm = −0.209 + 2.042·e^(M−5)` | `0.82 + 0.37/(1+(R/22.9)²)` |
| Bayrak, Nas & Bayrak (2019), R3 — Türkiye | episantral + derinlik | `7.494 + 0.744·Mw − 3.377·log((Repi³+h³)^(1/3)) + 0.017·h` | 1.270 |

Allen 2012 katsayıları OpenQuake `AllenEtAl2012` / `AllenEtAl2012Rhypo` sınıflarından, Bayrak 2019 katsayıları makalenin Tablo 4'ünden alınmıştır (R1–R4 dördü de kodda mevcuttur). Bayrak 2019'da logaritmanın tabanı açıkça belirtilmediği için log10 varsayılmıştır.

> ⚠️ **Eski formül kaldırıldı.** İlk sürümdeki `MMI = 1.62 + 1.22·Mw − 0.00255·R − 1.29·log10(R)` için yayımlanmış bir kaynak bulunamadı. Allen vd. (2012)'ye göre 100–300 km aralığında şiddeti **1,6–2,2 MMI fazla** tahmin ediyor (bkz. `tests/test_ipe.py`). Yalnızca karşılaştırma için `legacy_unverified` adıyla tutulur.
>
> **MMI → Mw dönüşümü kaldırıldı.** Büyüklük depremin, şiddet konumun özelliğidir. Bir noktadaki şiddetten depremin büyüklüğü geri hesaplanamaz.

---
## 📖 Literatür Taraması

Projenin teorik temeli için hazırlanan kapsamlı literatür taraması: [`docs/literatur_taramasi.pdf`](docs/literatur_taramasi.pdf) (29 sayfa). Şiddet tahmin denklemleri (IPE), GMPE + GMICE zinciri, Türkiye'ye özgü modeller, zemin etkisi (Vs30), sonlu fay, belirsizlik, ShakeMap/AFAD/KOERI, Kahramanmaraş 2023 dersleri ve aşamalı geliştirme yol haritasını kapsar.

## 🔗 Kaynaklar ve Referanslar

- 📊 AFAD Türkiye Deprem Tehlike Haritası (TDTH)
- 🧭 MTA Yerbilimleri Veri Portalı
- 📘 USGS MMI Açıklamaları
- 📄 Boore et al. (1997) — Zemin ivme tahmin denklemleri (GMPE)

---

## 🤝 Katkı
Her türlü katkıya açığız! Şunları yapabilirsin:

- 📥 Gerçek PGA ve zemin verileriyle entegrasyon
- 🌍 Raster veri destekli analiz (AFAD WMS, MTA TIFF)
- 🖼️ GUI arayüz geliştirme (Tkinter, PyQt)
- 📄 PDF rapor çıktısı oluşturma

---

## 🧠 Lisans
- MIT Lisansı ile lisanslanmıştır.
- Lütfen AFAD ve MTA kaynaklarını kullandığınızda uygun atıfta bulunun.


---

> - 👨‍💻 Hazırlayan: Mehmet Emre Ünlü
- 📅 Proje Başlangıcı: 2025
- 📍 Türkiye
