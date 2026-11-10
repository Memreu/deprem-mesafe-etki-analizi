# 🌍 MMI Intensity Mapper — Deprem Şiddeti Haritalama

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/OpenQuake-hazardlib_3.26-1F6FB2" alt="OpenQuake">
  <img src="https://img.shields.io/badge/LightGBM-monoton_artık_modeli-9ACD32" alt="LightGBM">
  <img src="https://img.shields.io/badge/RMSE-0.68→0.45_MMI-29A36A" alt="RMSE">
  <img src="https://img.shields.io/badge/test-25_geçti-2EA44F?logo=pytest&logoColor=white" alt="Testler">
  <img src="https://img.shields.io/badge/lisans-MIT-lightgrey" alt="MIT">
</p>

<p align="center">
  <a href="notebooks/kahramanmaras_demo.ipynb"><img src="https://img.shields.io/badge/📓_Demo_notebook-Jupyter-F37626?logo=jupyter&logoColor=white" alt="Notebook"></a>
  <a href="app/streamlit_app.py"><img src="https://img.shields.io/badge/Arayüz-Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="docs/literatur_taramasi.pdf"><img src="https://img.shields.io/badge/📖_Literatür_taraması-29_sayfa-6E5494" alt="Literatür"></a>
  <a href="https://www.kaggle.com/memreu"><img src="https://img.shields.io/badge/Kaggle-memreu-20BEFF?logo=kaggle&logoColor=white" alt="Kaggle"></a>
</p>

Olmuş bir depremin büyüklüğü, konumu ve derinliğinden, farklı noktalarda sarsıntının **Değiştirilmiş Mercalli Şiddeti (MMI)** cinsinden nasıl hissedildiğini tahmin eden, Türkiye odaklı, açık ve tekrarlanabilir bir Python aracı. Yayımlanmış şiddet modellerini (IPE), OpenQuake üzerinden **GMPE + GMICE** zincirini, **sonlu fay** geometrisini, **zemin (Vs30)** etkisini, **belirsizlik** bantlarını ve gözlemle **doğrulamayı** tek bir pakette birleştirir.

> Bu araç **olmuş bir depremin etkisini** tahmin eder. Gelecekteki depremlerin zamanını, yerini ya da büyüklüğünü **tahmin etmez**.

<p align="center"><img src="images/kahramanmaras_mmi_map.png" width="100%"></p>

> 🇬🇧 **In English:** A lightweight, documented and validated rapid-intensity tool for Türkiye. It replaces an unsourced legacy formula with published models: Allen, Wald & Worden (2012) and Bayrak et al. (2019) IPEs, plus a Kale et al. (2015) GMPE → Worden et al. (2012) / Bilal & Askan (2014) GMICE chain run through OpenQuake. Large events use a finite fault built from GEM active-fault traces and Thingbaijam et al. (2017) scaling. A four-branch logic tree yields 16/50/84th percentiles and P(MMI ≥ VII/VIII). For the 2023 Kahramanmaraş Mw 7.8 and 7.5 earthquakes (552 USGS DYFI, AFAD and KOERI observations), the legacy formula over-predicts by **1.75 MMI** (RMSE 2.05), while Allen et al. (2012) with the USGS rupture has a bias of **+0.10** (RMSE 0.89). Within 50 km of the fault, the automatically built GEM-based rupture (logic-tree RMSE 1.09) performs almost as well as the USGS ShakeMap rupture (1.05), whereas a point source gives 2.26. Across 18 Turkish Mw ≥ 6 earthquakes recorded by KOERI, the GMPE+GMICE chain has a bias of **−0.17** (RMSE 0.69). A monotonic-constrained LightGBM residual model, validated with event-grouped CV, lowers out-of-fold RMSE from **0.68 to 0.45** across 949 records. Outputs include a PAGER-style population exposure table, a layered Folium map, a Streamlit app and CI tests that check the IPEs against OpenQuake.

<details>
<summary><b>📑 İçindekiler</b></summary>

- [Öne çıkan sonuçlar](#öne-çıkan-sonuçlar)
- [Neden yeniden yazıldı?](#neden-yeniden-yazıldı)
- [Yöntem](#yöntem)
- [Doğrulama sonuçları](#doğrulama-sonuçları)
- [Makine öğrenmesi: artık modeli](#makine-öğrenmesi-artık-modeli)
- [Nüfus maruziyeti](#nüfus-maruziyeti)
- [Kurulum ve çalıştırma](#kurulum-ve-çalıştırma)
- [Klasör yapısı](#klasör-yapısı)
- [Veri ve lisanslar](#veri-ve-lisanslar)
- [Sınırlılıklar ve sonraki adımlar](#sınırlılıklar-ve-sonraki-adımlar)
- [Kaynaklar](#kaynaklar)

</details>

## Öne çıkan sonuçlar

| | Sonuç |
|---|---|
| ❌ **Eski formül** | Kaynağı bulunamadı. Kahramanmaraş 2023'te 552 gözlemde ortalama **1,75 MMI fazla** (RMSE 2,05), Türkiye Mw ≥ 6 depremlerinde **2,4 MMI fazla** tahmin ediyor |
| 📐 **Yerine gelen modeller** | Allen 2012 (Rrup/Rhyp), Bayrak 2019 (Türkiye), Kale 2015 → WGRW12 / Bilal & Askan 2014 |
| 🎯 **En iyi modeller** | Kahramanmaraş (DYFI + AFAD + KOERI): Allen 2012 Rrup sapma **+0,10**, RMSE **0,89** · Türkiye Mw ≥ 6 (KOERI): Kale 2015 → WGRW12 sapma **−0,17**, RMSE **0,69** |
| 🧭 **Sonlu fay** | Fay boyunca 50 km içinde RMSE: nokta kaynak **2,26** → otomatik GEM fayı **1,09** ≈ USGS ShakeMap fayı **1,05**. Antakya'ya episantral uzaklık 137 km, fay uzaklığı 20 km |
| 🎲 **Belirsizlik** | 4 dallı mantık ağacı · %16/%50/%84 · P(MMI ≥ VII), P(MMI ≥ VIII) haritaları |
| 🤖 **ML katkısı** | Monoton kısıtlı LightGBM artık modeli: katman dışı RMSE **0,68 → 0,45** (istasyon bazlı CV'de 0,49) |
| 🧱 **Zemin** | Vs30'un artıklara ek katkısı neredeyse sıfır (|SHAP| ≈ 0,001); Allen vd. (2012) bulgusuyla uyumlu |
| 👥 **Maruziyet** | Kahramanmaraş Mw 7.8 senaryosunda medyan tahminle **2,3 milyon** kişi (≥ 15 000 nüfuslu yerleşimlerde) MMI ≥ VII |

## Neden yeniden yazıldı?

Projenin ilk sürümü `MMI = 1.62 + 1.22·Mw − 0.00255·R − 1.29·log10(R)` formülünü kullanıyordu. Literatür taramasında ([`docs/literatur_taramasi.pdf`](docs/literatur_taramasi.pdf)) bu formülün yayımlanmış bir kaynağı bulunamadı. Formül, Allen vd. (2012)'ye göre 100–300 km'de şiddeti **1,6–2,2 MMI** fazla tahmin ediyordu; gerçek gözlemler bunu doğruladı. Ayrıca:

- **Nokta kaynak varsayımı** büyük depremlerde çöküyordu (Mw 7.8 için Thingbaijam vd. 2017 medyan fay uzunluğu 234 km).
- **Zemin** ve **belirsizlik** hesapta yoktu.
- MMI'dan Mw'ye "geri dönüşüm" bilimsel olarak geçersizdi: büyüklük depremin, şiddet konumun özelliğidir. Bu fonksiyon kaldırıldı.

Eski formül, karşılaştırma amacıyla `legacy_unverified` adıyla ve "doğrulanmamış" etiketiyle tutuluyor.

<p align="center"><img src="images/attenuation_comparison.png" width="70%"></p>

## Yöntem

### Modeller

| Model | Tür | Girdiler | Katsayı kaynağı |
|---|---|---|---|
| Allen, Wald & Worden (2012) · Rrup | IPE (küresel) | Mw, Rrup | OpenQuake `AllenEtAl2012` |
| Allen, Wald & Worden (2012) · Rhyp | IPE (küresel) | Mw, Rhyp | OpenQuake `AllenEtAl2012Rhypo` |
| Bayrak, Nas & Bayrak (2019) · R3 | IPE (Türkiye) | Mw, Repi, derinlik | Makale, Tablo 4 (R1–R4 kodda) |
| Kale vd. (2015) → Worden vd. (2012) | GMPE + GMICE | Mw, Rjb, Vs30, rake | OpenQuake `KaleEtAl2015Turkey` + USGS `esi-shakelib` WGRW12 |
| Kale vd. (2015) → Bilal & Askan (2014) | GMPE + GMICE (Türkiye) | Mw, Rjb, Vs30, rake | OpenQuake + makale özeti |
| ~~Eski formül~~ | doğrulanmamış | Mw, Rhyp | — |

Katsayılar hafızadan yazılmadı. Testler Allen 2012 sonuçlarını OpenQuake ile 1e-10 hassasiyetinde, fay uzaklıklarını OpenQuake `PlanarSurface` ile 0,3 km içinde karşılaştırır.

### Kaynak geometrisi

- **Mw < 6.5:** nokta kaynak (Rjb ≈ Repi, Rrup ≈ Rhyp).
- **Mw ≥ 6.5:** sonlu fay. USGS FFM ya da ShakeMap `rupture.json` verilirse doğrudan kullanılır. Verilmezse episantr çevresindeki GEM Global Active Faults izleri uç uca zincirlenir ve episantrın izdüşümü etrafında Thingbaijam vd. (2017) ölçek yasasıyla L uzunluğunda (Mw 7.8 doğrultu atımlı için 234 km), W genişliğinde bir parça kesilir.
- Rjb, fay izdüşümüne olan uzaklıktır ve `shapely` ile hesaplanır. Rrup düşey faylarda `shapely` ile, eğimli faylarda 1 km aralıklı yüzey ağıyla hesaplanır.

### Zemin

Her noktaya USGS Global Vs30 Mosaic rasterinden `rasterio` ile Vs30 atanır (`scripts/download_data.py vs30`). Raster yoksa 760 m/s referans değeri kullanılır ve kullanıcı uyarılır. Doğrulamada istasyonların kendi Vs30 değerleri kullanıldı.

### Belirsizlik ve mantık ağacı

Her dal bir noktada MMI ~ N(μ, σ) verir. GMPE+GMICE zincirinde σ² = (dMMI/dlnPGV · σ_lnPGV)² + σ²_GMICE. Mantık ağacı dalların ağırlıklı karışımıdır. %16/%50/%84 değerleri karışımın ters dağılım fonksiyonundan, aşma olasılığı ise P(MMI ≥ k) = Σ wᵢ[1 − Φ((k − μᵢ)/σᵢ)] ile hesaplanır.

| Dal | Ağırlık | Sonlu fayda |
|---|---|---|
| Allen 2012 · Rrup | 0.30 | 0.35 |
| Kale 2015 → WGRW12 | 0.30 | 0.35 |
| Kale 2015 → Bilal & Askan 2014 | 0.20 | 0.24 |
| Bayrak 2019 · R3 | 0.20 | 0.06 (episantral uzaklık kullandığı için) |

Gerekçeler: [`docs/logic_tree.md`](docs/logic_tree.md).

## Doğrulama sonuçları

Artık = gözlem − tahmin; **negatif sapma, modelin fazla tahmin ettiğini** gösterir. Enstrümantal gözlemlerde PGV, Worden vd. (2012) ile MMI'ya çevrildi. Tüm tablolar ve grafikler: [`results/`](results/README.md).

### Kahramanmaraş 2023 (Mw 7.8 Pazarcık + Mw 7.5 Elbistan)

Gözlemler: **248 USGS DYFI** hücresi (≥ 3 yanıt, şüpheliler hariç), ShakeMap istasyon listesindeki **296 AFAD** istasyonu ve **8 KOERI** kaydı. Fay geometrisi: USGS ShakeMap `rupture.json` (Pazarcık 286 km, Elbistan 136 km).

| Model | Tümü (552) | DYFI (248) | AFAD (296) |
|---|---|---|---|
| Eski formül (doğrulanmamış) | −1,75 · 2,05 | −2,14 · 2,40 | −1,42 · 1,71 |
| Allen 2012 · Rhyp | −0,06 · 1,05 | | |
| **Allen 2012 · Rrup** | **+0,10 · 0,89** | −0,31 · 0,96 | **+0,44 · 0,82** |
| Bayrak 2019 · R3 | +0,12 · 1,02 | −0,30 · 1,03 | +0,46 · 1,02 |
| Kale 2015 → WGRW12 | +0,48 · 1,04 | +0,01 · 0,95 | +0,87 · 1,11 |
| Kale 2015 → Bilal & Askan 2014 | +0,46 · 1,07 | | |
| **Mantık ağacı (ortalama)** | +0,32 · 0,90 | **−0,05 · 0,85** | +0,63 · 0,93 |

<sub>Hücreler: sapma · RMSE (MMI). Ayrıntı: `results/metrics_kahramanmaras*.csv`.</sub>

<p align="center"><img src="results/residual_distance_kahramanmaras.png" width="100%"></p>

**Kaynak geometrisi ne kadar önemli?** Aynı 552 gözlem, üç kaynak geometrisiyle (mantık ağacı ortalaması):

| Geometri | RMSE (tümü) | RMSE (USGS fayına Rjb ≤ 50 km, 64 nokta) |
|---|---|---|
| Nokta kaynak | 1,22 | 2,26 |
| GEM izi + Thingbaijam 2017 (**otomatik**, dış veri gerektirmez) | 0,93 | 1,09 |
| USGS ShakeMap fayı | 0,90 | 1,05 |

### Türkiye geneli (KOERI kuvvetli yer hareketi)

| Model | Mw ≥ 6 (18 deprem, 54 kayıt) | Tüm KOERI (332 deprem, 949 kayıt) |
|---|---|---|
| Eski formül (doğrulanmamış) | −2,36 · 2,45 | −2,64 · 2,69 |
| Allen 2012 · Rhyp | −0,61 · 0,89 | −0,59 · 0,77 |
| Allen 2012 · Rrup | −0,56 · 0,89 | −1,22 · 1,32 |
| Bayrak 2019 · R3 | −1,63 · 1,91 | −2,52 · 2,60 ¹ |
| **Kale 2015 → WGRW12** | **−0,17 · 0,69** | **−0,41 · 0,68** |
| Kale 2015 → Bilal & Askan 2014 | +0,20 · 0,95 | +0,73 · 1,06 |
| Mantık ağacı (ortalama) | −0,48 · 0,81 | −0,84 · 0,98 |

<sub>¹ Bayrak 2019, MMI ≥ 4 ve Mw ≥ 4.5 için türetildi; tüm-KOERI kümesinin büyük kısmı bu aralığın dışında.</sub>

**Bulgular**

1. **Eski formül uzaklıkla çok yavaş azalıyor.** Kahramanmaraş'ta fayın 25 km yakınında sapması küçük (−0,16). Ama 100–200 km'de −1,65'e, 400 km ötesinde −2,38'e çıkıyor. Literatür taramasındaki "uzak mesafede 1,5–2 MMI fazla" tespiti gerçek gözlemlerle doğrulandı.
2. **Büyük depremde sonlu fay belirleyici.** Nokta kaynakla fay yakınındaki RMSE 2,26 iken, fay geometrisiyle 1,05–1,09'a iniyor. GEM izlerinden otomatik kurulan fay, USGS'in deprem sonrası yayımladığı faya neredeyse eşdeğer. Bu, USGS ürünü yayımlanmadan önce de hızlı ve doğru harita üretilebileceğini gösteriyor.
3. **Model seçimi gözlem türüne bağlı.** Kahramanmaraş'ta Allen 2012 en dengeli model. Kale zinciri DYFI'yi iyi yakalıyor (sapma +0,01), ama AFAD istasyonlarını 0,9 MMI düşük tahmin ediyor. Bunun bir kısmı bileşen farkından (AFAD büyük bileşen, Kale geometrik ortalama), bir kısmı da Mw 7.8'deki yakın alan doygunluğundan geliyor. Daha küçük Türkiye depremlerinde (Mw ≥ 6) ise en iyi model Kale zinciri. Mantık ağacı her iki durumda da en iyiye yakın kalıyor.
4. **Enstrümantal "gözlem" de bir modele bağlı.** Aynı PGV'ler Bilal & Askan ile MMI'ya çevrildiğinde Kahramanmaraş RMSE'leri 0,7–0,8 MMI artıyor (`results/sensitivity_observed_gmice.csv`). DYFI bu döngüselliği kırıyor: DYFI'ye karşı da eski formül açık ara en kötü (RMSE 2,40), mantık ağacı en iyi (0,85).

## Makine öğrenmesi: artık modeli

Literatürün önerdiği hibrit yapı uygulandı: `MMI = MMI_fizik + f_LightGBM(özellikler)`. Omurga Kale 2015 → WGRW12'dir. LightGBM `init_score` ile yalnızca artığı öğrenir. Mw (+), Rrup (−) ve Vs30 (−) üzerinde **monotonluk kısıtları** vardır, bu yüzden toplam tahmin fiziksel olarak tutarlı kalır. Doğrulama, deprem bazında gruplandırılmış 5 katlı **GroupKFold** ile yapıldı; gruplar, kayıt pencereleri örtüşen depremleri de birleştirir.

| Küme | Omurga | + sabit kaydırma | **+ LightGBM** |
|---|---|---|---|
| Tümü (deprem bazlı CV) | 0,68 | 0,54 | **0,45** |
| Tümü (istasyon bazlı CV) | 0,68 | 0,55 | **0,49** |
| Mw ≥ 6 | 0,69 | 0,72 | **0,66** |
| Rrup ≤ 50 km | 0,59 | 0,70 | **0,53** |

<sub>Katman dışı RMSE (MMI). Ayrıntı: [`results/ml/`](results/ml/README.md).</sub>

<p align="center"><img src="results/ml/shap_summary.png" width="60%"></p>

- Basit bir sabit düzeltme, küçük depremlerdeki genel sapmayı giderir ama **büyük depremleri ve yakın mesafeyi bozar**. LightGBM bunu büyüklüğe ve uzaklığa bağlı öğrendiği için bu sorunu yaşamaz.
- SHAP'a göre en büyük katkı konumdan (bölgesel yol ve istasyon etkileri) ve uzaklıktan geliyor. **Vs30'un ek bilgisi yok.** Bu, literatür taramasındaki "zemin düzeltmesinin etkisi belirsiz" boşluğuna ilk sayısal katkıdır.

## Nüfus maruziyeti

USGS PAGER mantığıyla, tahmin edilen MMI sınıflarına göre nüfus toplanır. Kahramanmaraş Mw 7.8 senaryosu (sonlu fay, Vs30 = 760 m/s, episantrın ±3° çevresi, Suriye dahil):

| MMI | %16 | Medyan | %84 |
|---|---|---|---|
| V | 9 679 190 | 11 397 279 | 3 660 996 |
| VI | 1 352 247 | 9 482 003 | 10 039 265 |
| VII | 534 663 | 1 730 637 | 7 147 940 |
| VIII | 0 | 570 603 | 3 755 596 |
| IX | 0 | 0 | 879 707 |

<sub>Nüfus: GeoNames ≥ 15 000 nüfuslu yerleşimler (kırsal nüfus hariç, bu yüzden PAGER değerlerinden düşüktür). GHSL ya da TÜİK rasteri `exposure(..., raster=...)` ile kullanılabilir. Tam tablo: `results/kahramanmaras_exposure.csv`.</sub>

Katmanlı harita (`results/kahramanmaras_map.html`) şu katmanları içerir: medyan, %16, %84, σ, P(≥VII), P(≥VIII), fay, istasyon gözlemleri ve yerleşimler.

## Kurulum ve çalıştırma

```bash
git clone https://github.com/Memreu/deprem-mesafe-etki-analizi.git
cd deprem-mesafe-etki-analizi
pip install -r requirements.txt
pip install --no-deps openquake.engine==3.26.2   # hazardlib; GDAL derlemesini atlamak için bağımlılıksız
```

**Komut satırı**

```bash
python "1.1.MMI Intensity Mapper.py"            # etkileşimli (ondalık ya da DMS koordinat)
python -m mmi_mapper.cli --mag 7.8 --lat 37.2256 --lon 37.0143 --depth 10 \
       --site 37.5753,36.9228 --site 36.2023,36.1613 --vs30 400
```

**Arayüz, not defteri ve çoğaltma**

```bash
streamlit run app/streamlit_app.py              # harita, maruziyet, nokta sorgusu, mantık ağacı ağırlıkları
jupyter lab notebooks/kahramanmaras_demo.ipynb  # uçtan uca demo (çıktılarıyla)
python scripts/run_benchmark.py                 # Aşama 3: results/ tabloları ve grafikleri
python scripts/train_residual_model.py          # Aşama 4: LightGBM + SHAP
python scripts/make_figures.py                  # README görselleri, maruziyet tablosu, katmanlı harita
pytest -q                                       # 25 test
```

**Ek veriyle genişletme**

```bash
python scripts/download_data.py usgs us6000jllz          # DYFI, ShakeMap istasyonları, rupture.json, FFM
python scripts/build_usgs_observations.py us6000jllz      # → data/observations/usgs_observations.csv
python scripts/download_data.py vs30 --url <GeoTIFF>     # USGS Global Vs30 Mosaic
# AFAD TADAS tablosu → data/raw/us6000jllz/afad_stations.csv (station, lat, lon, pgv_cms)
# Saha haritası     → data/raw/us6000jllz/field_map.csv     (lat, lon, mmi)
```

Kahramanmaraş için USGS gözlemleri ve ShakeMap fayları repoda hazır (`data/observations/usgs_observations.csv`, `data/ruptures/`); benchmark ek indirme gerektirmez.

## Klasör yapısı

```
├── 1.1.MMI Intensity Mapper.py     # Etkileşimli giriş noktası
├── mmi_mapper/
│   ├── ipe.py                      # Allen 2012, Bayrak 2019, eski formül (doğrulanmamış)
│   ├── gmpe.py · gmice.py          # OpenQuake Kale 2015 · WGRW12, Bilal & Askan 2014
│   ├── rupture.py                  # Nokta / sonlu fay, GEM + Thingbaijam, Rjb–Rrup
│   ├── site.py                     # Vs30 rasteri, NEHRP sınıfı
│   ├── model.py · grid.py          # Senaryo ve ızgara hesabı
│   ├── uncertainty.py              # Mantık ağacı, çeyreklikler, aşma olasılığı
│   ├── observations.py · benchmark.py   # Gözlem yükleyicileri, metrikler, grafikler
│   ├── ml.py                       # LightGBM artık modeli
│   ├── exposure.py · mapping.py    # PAGER tablosu, katmanlı folium haritası
│   └── cli.py · scale.py · coords.py
├── app/streamlit_app.py
├── notebooks/kahramanmaras_demo.ipynb
├── scripts/                        # benchmark, ML, görseller, veri indirme
├── data/faults/                    # GEM aktif fay izleri (CC BY-SA 4.0)
├── data/observations/              # KOERI kayıtları, USGS DYFI + AFAD (ShakeMap) gözlemleri
├── data/ruptures/                  # USGS ShakeMap fay geometrileri
├── results/                        # Benchmark ve ML çıktıları
├── docs/                           # Literatür taraması, mantık ağacı
├── tests/                          # pytest (OpenQuake karşılaştırmaları dahil)
└── .github/workflows/tests.yml     # GitHub Actions
```

## Veri ve lisanslar

| Veri | Kaynak | Lisans |
|---|---|---|
| Aktif fay izleri | GEM Global Active Faults (Styron & Pagani 2020) | CC BY-SA 4.0 |
| Kuvvetli yer hareketi | KOERI / ORFEUS-EIDA, [turkiye-deprem-verisi](https://github.com/Ayberkrk/turkiye-deprem-verisi) üzerinden | Yalnızca akademik / ticari olmayan kullanım |
| DYFI, ShakeMap istasyonları (AFAD) ve fay | USGS ComCat (us6000jllz, us6000jlqa) | Kamu malı |
| İstasyon Vs30 | USGS Global Vs30 Mosaic | Kamu malı |
| Yerleşim nüfusu | GeoNames (`geonamescache`) | CC BY 4.0 |

Ayrıntılar: [`data/faults/README.md`](data/faults/README.md), [`data/observations/README.md`](data/observations/README.md).

## Sınırlılıklar ve sonraki adımlar

- **Saha haritası ve TADAS henüz yok.** Albayrak vd. (2024) saha şiddetleri ve TADAS'ın tam istasyon tablosu eklenmedi. `data/raw/<event_id>/` altına konduklarında benchmark onları otomatik olarak kullanır.
- **Vs30 rasteri** (`apps.usgs.gov`) bu geliştirme ortamından indirilemedi. Harita senaryolarında 760 m/s kullanılıyor. Doğrulamada istasyon ve DYFI noktalarına ShakeMap'in atadığı Vs30 değerleri kullanıldı. ShakeMap listesindeki AFAD istasyonlarının yaklaşık yarısında bu değer 760 m/s.
- **AFAD PGV bileşeni:** ShakeMap listesindeki PGV büyük yatay bileşendir, Kale 2015 ise geometrik ortalama verir.
- **KOERI veri seti:** kaynak belgesine göre PGA'lar Akkar vd. (2014)'e göre log10'da ~0,24 düşük. Tüm-KOERI kümesindeki negatif sapmanın bir kısmı buradan gelebilir.
- **Kabul edilen varsayımlar:** Bayrak 2019'da log tabanı (log10) ve σY'nin toplam sigma olduğu; Bilal & Askan 2014 için σ_GMICE = 0,63 (WGRW12'den vekil); GEM izlerinde sağ el eğim kuralı; GMPE geometrik ortalama bileşeni ile GMICE bileşeni arasında dönüşüm yapılmaması.
- **Yakın alan:** Fay üzerindeki yerleşimlerde medyan tahmin VIII civarında kalıyor. Fayın 13 km yakınındaki KHMN istasyonunda gözlem 9,2, mantık ağacı medyanı 8,2. Yönelim (directivity) ve havza etkileri modelde yok.
- **Sonraki adımlar:** DYFI ve AFAD ile benchmark'ı genişletmek; kalan artıklar için uzamsal Gauss süreci; Elazığ 2020 ve Düzce 1999'u benchmark setine eklemek; Türkiye için Rrup tabanlı bir IPE kalibre etmek (literatür boşluğu #2).

## Kaynaklar

- Allen, T.I., Wald, D.J., Worden, C.B. (2012). Intensity attenuation for active crustal regions. *J. Seismology* 16, 409–433. doi:10.1007/s10950-012-9278-7
- Bayrak, E., Nas, M., Bayrak, Y. (2019). New macroseismic intensity predictive models for Turkey. *Acta Geophysica* 67, 1483–1513. doi:10.1007/s11600-019-00357-4
- Kale, Ö., Akkar, S., Ansari, A., Hamzehloo, H. (2015). A ground-motion predictive model for Iran and Turkey. *BSSA* 105(2A), 963–980.
- Worden, C.B., Gerstenberger, M.C., Rhoades, D.A., Wald, D.J. (2012). Probabilistic relationships between ground-motion parameters and MMI in California. *BSSA* 102(1), 204–221. doi:10.1785/0120110156
- Bilal, M., Askan, A. (2014). Relationships between felt intensity and recorded ground-motion parameters for Turkey. *BSSA* 104(1), 484–496. doi:10.1785/0120130093
- Thingbaijam, K.K.S., Mai, P.M., Goda, K. (2017). New empirical earthquake source-scaling laws. *BSSA* 107(5), 2225–2246. doi:10.1785/0120170017
- Styron, R., Pagani, M. (2020). The GEM Global Active Faults Database. *Earthquake Spectra* 36(S1), 160–180. doi:10.1177/8755293020944182
- Jaiswal, K., Wald, D.J. (2010). An empirical model for global earthquake fatality estimation. *Earthquake Spectra* 26(4), 1017–1037.
- Pagani, M. vd. (2014). OpenQuake Engine: an open hazard (and risk) software for the Global Earthquake Model. *SRL* 85(3), 692–702.
- Tam kaynakça: [`docs/literatur_taramasi.pdf`](docs/literatur_taramasi.pdf)

---

Bu proje [MIT lisansı](LICENSE) ile paylaşılmaktadır. `data/` altındaki veriler kendi lisanslarına tabidir.

**Mehmet Emre Ünlü** · [GitHub](https://github.com/Memreu) · [LinkedIn](https://www.linkedin.com/in/memreu) · [Kaggle](https://www.kaggle.com/memreu)
