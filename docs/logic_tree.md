# Mantık ağacı ve belirsizlik

## Dallar ve ağırlıklar

| Dal | Ağırlık | Mw ≥ 6.5 sonlu fay (normalize) | Gerekçe |
|---|---|---|---|
| Allen vd. 2012 · Rrup | 0.30 | 0.353 | Küresel aktif kabuk IPE'si; sonlu fay uzaklığı; uzaklığa bağlı yayımlanmış σ |
| Kale vd. 2015 → Worden vd. 2012 | 0.30 | 0.353 | Türkiye GMPE'si, zemin (Vs30) terimi içerir; WGRW12 ShakeMap'in varsayılan GMICE'sidir |
| Kale vd. 2015 → Bilal & Askan 2014 | 0.20 | 0.235 | Türkiye GMICE'si; σ_GMICE birincil kaynaktan doğrulanamadığı için (0.63 varsayımı) daha düşük ağırlık |
| Bayrak vd. 2019 · R3 | 0.20 | 0.059 | Türkiye IPE'si; ancak episantral uzaklık kullanır. Büyük faylarda nokta kaynak varsayımı çöktüğü için sonlu fay senaryolarında 0.05'e indirilir |

Ağırlıklar uzman yargısıdır; `mmi_mapper.uncertainty.LogicTree(weights=...)` ile değiştirilebilir.
Aşama 3 benchmark sonuçları (`results/`), ağırlıkların veriyle yeniden değerlendirilmesi için kullanılabilir.

## Hesap

Her dal bir noktada MMI ~ N(μᵢ, σᵢ) verir.

* IPE'ler: σ makaleden (Allen 2012 uzaklığa bağlı; Bayrak 2019 sabit σY).
* GMPE + GMICE: σ² = (dMMI/dlnPGV · σ_lnPGV)² + σ²_GMICE. σ_lnPGV, Kale 2015'in toplam sigmasıdır (OpenQuake).

Mantık ağacı dağılımı ağırlıklı karışımdır: F(x) = Σ wᵢ Φ((x − μᵢ)/σᵢ).

* **%16 / %50 / %84**: F(x) = p denkleminin sayısal çözümü.
* **Aşma olasılığı**: P(MMI ≥ k) = Σ wᵢ [1 − Φ((k − μᵢ)/σᵢ)], k = 7 (VII) ve 8 (VIII).
  Eşik, literatür taramasındaki tanıma uygun olarak tam sayı alınmıştır. Yuvarlama kuralına göre
  "VII ve üzeri" isteniyorsa k = 6.5 kullanılabilir (`add_uncertainty(levels=(6.5, 7.5))`).

## Sınırlamalar

* Uzamsal korelasyon modellenmez; her nokta bağımsız değerlendirilir. Bölgesel toplamlar (ör. etkilenen nüfus)
  medyan ve çeyreklik haritalarından ayrı ayrı hesaplanır, birleşik dağılım değildir.
* Kale 2015 geometrik ortalama PGV verir; GMICE'lere bileşen dönüşümü uygulanmaz (≈0,1–0,3 MMI sistematik etki).
