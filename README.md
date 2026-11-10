# 🌍 MMI Intensity Mapper

**MMI Intensity Mapper**, kullanıcıdan alınan deprem ve konum bilgilerini kullanarak, sarsıntının farklı noktalarda nasıl hissedildiğini tahmin eden bir analiz ve görselleştirme aracıdır. Uygulama, deprem büyüklüğü (**Mw**), episantr uzaklığı ve derinlik bilgilerini temel alarak **Modified Mercalli Intensity (MMI)** değerini hesaplar ve sonuçları **etkileşimli bir HTML haritası** üzerinde görsel olarak sunar.

> Proje Python ile geliştirilmiş olup, haritalama için `folium`, mesafe hesaplamaları için `geopy`, renkli terminal çıktısı için `colorama` kullanmaktadır.

---

## 📌 Özellikler

- 📍 **DMS formatında koordinat girişi**  
  Kullanıcılar hem deprem episantrı hem de analiz yapılacak konumları DMS (derece, dakika, saniye) formatında girebilirler.
  
- 🧭 **Yüzeysel ve hiposantrik mesafe hesaplamaları**  
  En doğru sismik analiz için yer yüzeyinden ve yer altındaki depremin merkezine olan uzaklıklar hesaplanır.

- 📈 **MMI ve Mw hesaplamaları**  
  Kullanıcının verdiği Mw değeriyle MMI hesaplanır. Aynı zamanda hissedilen MMI'dan geri tahminle yaklaşık Mw da verilir.

- 🎨 **Terminalde renkli çıktı**  
  MMI şiddeti kullanıcıya renkli ve anlamlı açıklamalarla sunulur (örn: Hafif, Orta, Yıkıcı).

- 🗺️ **Etkileşimli harita çıktısı**  
  Folium kullanılarak oluşturulan HTML haritada deprem ve kullanıcı konumları işaretlenir, mesafeler ve tahmini etkiler gösterilir.

---

## 🛠️ Kurulum

Bu proje pek çok Python ile çalışır. Kütüphaneler script içerisinde otomatik olarak kurulsa da manuel kurulum için:

```bash
pip install folium geopy colorama
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

## 📚 Bilimsel Arka Plan
**MMI Hesabı:**
- MMI = 1.62 + 1.22Mw - 0.00255R - 1.29log10(R)
- Bu formül, hiposantr uzaklığına göre zayıflayan deprem ivmesini baz alır.
-- **Mw**: Moment büyüklüğü
-- **R**: Hiposantr uzaklığı (km)
> Formül, depremin şiddetinin mesafeye ve büyüklüğe göre logaritmik olarak zayıflamasına dayalıdır.

#### **Yaklaşık Mw Hesabı:**
- MMI değerinden yaklaşık olarak hissedilen Mw değeri tahmin edilir. Bu tahmin, ampirik ilişkilere dayalıdır ve mühendislik hesaplamalarına referans niteliğindedir.
- Bu sistem yalnızca deprem büyüklüğü ve mesafeye göre analiz yapar. Zemin tipi, yapı dayanımı gibi faktörleri içermemektedir.

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
