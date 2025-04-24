# 🌍 MMI Intensity Mapper

Bu proje, kullanıcıdan alınan deprem ve konum bilgileri ile **deprem büyüklüğü**, **merkez üssüne uzaklık** ve **derinlik** temelinde **MMI (Modified Mercalli Intensity)** değerini hesaplayıp **interaktif bir harita** üzerinde görselleştirmeyi amaçlar.

> Proje Python ile geliştirilmiş olup, haritalama için `folium`, mesafe hesaplamaları için `geopy`, renkli terminal çıktısı için `colorama` kullanmaktadır.

---

## 📌 Özellikler

- 📍 **DMS formatında (örn: `40°14'56.6"N`) koordinat girişi**
- 🧮 Deprem merkezinden konuma:
  - **Yüzeysel (episantr) mesafe**
  - **Hiposantrik mesafe**
  - **Tahmini MMI değeri**
  - **Renkli MMI açıklaması**
  - **Yaklaşık Mw (moment magnitüdü) karşılığı**
- 🌐 Interaktif HTML harita çıktısı
- 🎨 Terminalde renkli çıktılar
- 📏 Konumlar arası çizgiler ile görsel bağlantı

---

## 🛠️ Kurulum

Gerekli kütüphaneler script içinde otomatik kurulur. Manuel kurulum yapmak istersen:

```bash
pip install folium geopy colorama

---

## 🚀 Kullanım
Uygulama çalıştırıldığında:

Depremin episantr koordinatlarını (DMS formatında) girin.

Birden fazla konum girerek analiz yapabilirsiniz.

Depremin derinliği ve moment büyüklüğünü (Mw) belirtin.

Sonuçlar hem terminalde hem de deprem_haritasi.html dosyasında görsel olarak gösterilecektir.
