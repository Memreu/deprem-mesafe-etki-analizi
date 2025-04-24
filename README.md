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
```

---

## 🚀 Kullanım
Uygulama çalıştırıldığında:

-Depremin episantr koordinatlarını (DMS formatında) girin.
-Birden fazla konum girerek analiz yapabilirsiniz.
-Depremin derinliği ve moment büyüklüğünü (Mw) belirtin.
-Sonuçlar hem terminalde hem de deprem_haritasi.html dosyasında görsel olarak gösterilecektir.


--- 

📸 Örnek Harita Çıktısı

Haritada: Deprem noktası (kırmızı), kullanıcı konumları (mavi), MMI değerine göre bağlantı çizgileri.

---

📚 Bilimsel Arka Plan
MMI Hesabı:
MMI = 1.62 + 1.22Mw - 0.00255R - 1.29log10(R)
Bu formül, hiposantr uzaklığına göre zayıflayan deprem ivmesini baz alır.

Yaklaşık Mw tahmini:
MMI değerine karşılık gelen ortalama moment büyüklüğü hesaplanır.

Bu sistem yalnızca deprem büyüklüğü ve mesafeye göre analiz yapar. Zemin tipi, yapı dayanımı gibi faktörleri içermemektedir.

---

🔗 Kaynaklar ve Referanslar
AFAD Türkiye Deprem Tehlike Haritası  
MTA Yer Bilimleri Portalı
Boore et al. (1997): Ground motion prediction equations
USGS MMI Explanation

---

🤝 Katkı
Her türlü katkıya açığız! Şunları yapabilirsin:

📥 Gerçek PGA ve zemin verileriyle entegrasyon
🌍 Raster veri destekli analiz (AFAD WMS, MTA TIFF)
🖼️ GUI arayüz geliştirme (Tkinter, PyQt)
📄 PDF rapor çıktısı oluşturma

---

🧠 Lisans
MIT Lisansı ile lisanslanmıştır.
Lütfen AFAD ve MTA kaynaklarını kullandığınızda uygun atıfta bulunun.


---

>👨‍💻 Hazırlayan: Mehmet Emre Ünlü
📅 Proje Başlangıcı: 2025
📍 Türkiye
