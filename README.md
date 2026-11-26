# MMI Intensity Mapper: Deprem Şiddeti Haritalama

Bu proje, olmuş bir depremin büyüklüğünden, konumundan ve derinliğinden yola çıkarak sarsıntının farklı noktalarda Değiştirilmiş Mercalli Şiddeti (MMI) cinsinden nasıl hissedildiğini tahmin eden bir Python aracı. Türkiye odaklı, açık ve tekrarlanabilir olmasına özen gösterdim.

Baştan belirtmem gereken bir şey var: araç olmuş bir depremin etkisini tahmin eder. Gelecekteki depremlerin zamanını, yerini ya da büyüklüğünü tahmin etmez.

![Kahramanmaraş 2023 MMI haritası](images/kahramanmaras_mmi_map.png)

## Neden böyle bir şey yaptım?

Haberlerde önce depremin büyüklüğünü duyarız: "7,8". Ama bu sayı depremin kendisini anlatır, sizin bulunduğunuz yerde sarsıntının ne kadar sert hissedildiğini anlatmaz. Aynı deprem fayın dibindeki bir şehirde binaları yıkarken 300 km ötede yalnızca avizeleri sallayabilir. Yerel sarsıntıyı anlatan şey şiddettir ve burada I'den XII'ye giden Mercalli ölçeğini kullanıyorum:

| Şiddet | Kabaca ne olur? |
|---|---|
| II–III | Yalnızca içeride, durgun duran bazı kişiler hisseder |
| IV–V | Çoğu kişi hisseder, camlar tıngırdar, uyuyanlar uyanır |
| VI | Herkes hisseder, eşyalar devrilir, sıvalar çatlar |
| VII | Ayakta durmak zorlaşır, zayıf binalarda hasar başlar |
| VIII | Sıradan binalarda ciddi hasar, kısmi çökmeler |
| IX ve üstü | Yaygın yıkım |

Deprem sonrasındaki ilk saatlerde "en çok nereler etkilendi?" sorusu çok önemli. ABD'de USGS'in ShakeMap ve PAGER ürünleri bu soruya cevap veriyor. Bu proje aynı fikrin Türkiye'ye odaklanan ve sonuçları gerçek gözlemlerle karşılaştırılmış küçük bir sürümü.

Projenin ilk hâli `MMI = 1.62 + 1.22·Mw − 0.00255·R − 1.29·log10(R)` formülüne dayanıyordu. Literatür taramasını yaparken ([`docs/literatur_taramasi.pdf`](docs/literatur_taramasi.pdf)) bu formülün yayımlanmış bir kaynağını bulamadım; üstelik Allen vd. (2012)'ye göre 100–300 km'de şiddeti 1,6–2,2 MMI fazla veriyordu. Nokta kaynak varsayımı büyük depremlerde çöküyordu, zemin ve belirsizlik hesapta yoktu. Bu yüzden aracı yayımlanmış modeller üzerine yeniden kurdum. Eski formülü yalnızca karşılaştırma için `legacy_unverified` adıyla tutuyorum.

## Ne yapıyor?

Depremin büyüklüğünü, yerini ve derinliğini veriyorsunuz; araç istediğiniz noktalarda ya da bütün bölge için bir harita olarak hangi şiddetin hissedilmiş olabileceğini tahmin ediyor. Bunu yaparken:

- uzaklığı merkez üssüne göre değil fayın kendisine göre ölçüyor (Kahramanmaraş 2023'te fay yaklaşık 300 km uzunluğundaydı),
- her noktaya USGS Vs30 rasterinden zemin bilgisi atıyor,
- tek bir sayı yerine %16/%50/%84 aralığı ve P(MMI ≥ VII), P(MMI ≥ VIII) gibi aşma olasılıkları veriyor,
- hangi şiddette kaç kişinin yaşadığını PAGER mantığıyla yaklaşık olarak hesaplıyor.

Kullandığım modeller Allen, Wald & Worden (2012) ve Bayrak vd. (2019) şiddet denklemleri ile OpenQuake üzerinden çalışan Kale vd. (2015) GMPE → Worden vd. (2012) / Bilal & Askan (2014) GMICE zinciri. Bunlar dört dallı bir mantık ağacında birleşiyor; ağırlıkların gerekçesini [`docs/logic_tree.md`](docs/logic_tree.md) içinde yazdım. Mw ≥ 6.5 depremlerde USGS'in fay geometrisi varsa onu, yoksa GEM aktif fay izlerinden Thingbaijam vd. (2017) ölçek yasasıyla otomatik kurulan bir sonlu fayı kullanıyor. Katsayıları hafızadan yazmadım; testler Allen 2012 sonuçlarını OpenQuake ile 1e-10 hassasiyetinde karşılaştırıyor.

## Ne kadar güvenilir?

Aracı Türkiye ve çevresindeki altı büyük depremde (Kahramanmaraş 2023 ×2, Elazığ 2020, Sisam 2020, Düzce 1999, İzmit 1999) 1 324 gerçek gözlemle sınadım. Gözlemler USGS ComCat'ten geliyor: "Hissettiniz mi?" (DYFI) anketleri, AFAD ve KOERI istasyon kayıtları ve saha şiddetleri.

| Model | Sapma | RMSE |
|---|---|---|
| Eski formül (doğrulanmamış) | −2,01 | 2,29 |
| Allen 2012 · Rrup | −0,17 | 0,95 |
| Bayrak 2019 · R3 | −0,48 | 1,21 |
| Kale 2015 → WGRW12 | +0,01 | 0,99 |
| Mantık ağacı | −0,11 | 0,93 |

Sapma gözlem eksi tahmin; negatif değer modelin fazla tahmin ettiğini gösteriyor. Sade bir dille söylersem: tahminler ortalama yaklaşık bir şiddet derecesi sapıyor. Gözlemlerin %72'sinde hata bir dereceden az, %88'inde tahmin edilen derece ya tam isabet ya da bir derece komşusu; hatanın iki dereceyi aştığı durumlar %3. Verilen olasılıklar da kalibre görünüyor: "VII'yi aşma olasılığı %80" denen yerlerde gerçekten yaklaşık %80 oranında VII ve üstü görülmüş.

Birkaç bulgu benim için öne çıktı:

1. Eski formül altı depremin hepsinde açık ara en kötü model. Literatür taramasındaki "uzak mesafede 1,5–2 MMI fazla" tespiti gerçek gözlemlerle doğrulandı.
2. Büyük depremde sonlu fay belirleyici. Kahramanmaraş'ta faya 50 km içindeki RMSE nokta kaynakla 2,26, otomatik GEM fayıyla 1,10, USGS fayıyla 1,07. Yani USGS ürünü yayımlanmadan önce de makul bir harita üretmek mümkün.
3. Tek bir "en iyi" model yok. Deprem bazında kazanan değişiyor, mantık ağacı ise her depremde en iyi modelden en fazla 0,15 MMI uzakta kalıyor. Ağırlıklı birleştirmeyi tercih etmemin ampirik gerekçesi bu.
4. Bayrak 2019 orta büyüklükteki depremlerde iyi, Sisam ve İzmit gibi uzun ya da denizdeki faylarda zayıf; episantral uzaklığın sınırı burada görülüyor.

Deprem bazında tablolar, gözlem türüne göre ayrıntılar, KOERI tablosuyla Türkiye geneli sonuçlar ve grafikler [`results/`](results/README.md) klasöründe.

## Makine öğrenmesi kısmı

Fiziksel modelin üzerine bir artık modeli ekledim: `MMI = MMI_fizik + f_LightGBM(özellikler)`. Omurga Kale 2015 → WGRW12; LightGBM yalnızca artığı öğreniyor ve Mw, Rrup ve Vs30 üzerinde monotonluk kısıtları var, böylece toplam tahmin fiziksel olarak tutarlı kalıyor. Deprem bazında gruplanmış 5 katlı GroupKFold ile 949 kayıtta katman dışı RMSE 0,68'den 0,45'e iniyor (istasyon bazlı CV'de 0,49).

SHAP'a göre en büyük katkı konumdan ve uzaklıktan geliyor. Vs30'un ek katkısı neredeyse sıfır (|SHAP| ≈ 0,001); bu Allen vd. (2012) bulgusuyla uyumlu. Ayrıntılar: [`results/ml/`](results/ml/README.md).

## Nüfus maruziyeti

Kahramanmaraş Mw 7.8 senaryosunda medyan tahminle yaklaşık 5,3 milyon kişi (15 000 ve üzeri nüfuslu yerleşimlerde) MMI ≥ VII bölgede kalıyor. Kırsal nüfus dahil olmadığı için bu sayı PAGER değerlerinden düşük. Tam tablo `results/kahramanmaras_exposure.csv`, katmanlı harita `results/kahramanmaras_map.html` içinde.

## Kurulum ve kullanım

```bash
git clone https://github.com/Memreu/deprem-mesafe-etki-analizi.git
cd deprem-mesafe-etki-analizi
pip install -r requirements.txt
pip install --no-deps openquake.engine==3.26.2   # hazardlib; GDAL derlemesini atlamak için bağımlılıksız
pip install --no-deps -e .                       # mmi-mapper komutu
```

```bash
mmi-mapper                                      # etkileşimli; python -m mmi_mapper de olur
mmi-mapper --mag 7.8 --lat 37.2256 --lon 37.0143 --depth 10 \
       --site 37.5753,36.9228 --site 36.2023,36.1613 --vs30 400
mmi-mapper --event us6000jllz --site 37.5753,36.9228
streamlit run app/streamlit_app.py              # arayüz
jupyter lab notebooks/kahramanmaras_demo.ipynb  # demo not defteri
python scripts/run_benchmark.py                 # results/ tabloları ve grafikleri
python scripts/train_residual_model.py          # LightGBM + SHAP
pytest -q                                       # 31 test
```

Altı depremin USGS gözlemleri, fayları ve Türkiye Vs30 rasteri repoda hazır, benchmark için ek indirme gerekmiyor. Ek veri indirmek için `scripts/download_data.py` kullanılabilir. CI, Python 3.11, 3.12 ve 3.13'te çalışıyor.

## Sınırları

- En şiddetli bölgelerde sarsıntıyı biraz az tahmin ediyor. Gerçekte VIII ve üstü yaşanan yerlerde tahmin ortalama 0,8 derece düşük kalıyor; faya 10 km içindeki 15 istasyonda gözlenen ortalama 9,0 iken mantık ağacı medyanı 8,3. Yönelim (directivity) ve havza etkileri modelde yok.
- Bina hasarını ya da can kaybını tahmin etmiyor. Şiddet sarsıntının sertliği; hasar binanın sağlamlığına da bağlı.
- Albayrak vd. (2024) saha şiddetleri ve TADAS'ın tam istasyon tablosu henüz eklenmedi.
- Resmî bir uyarı ya da afet yönetimi aracı değil, araştırma ve eğitim amaçlı. Gerçek bir deprem sonrasında AFAD'ın ve resmî kurumların açıklamalarını esas alın.

Bundan sonra ML modelini DYFI ve saha verisiyle genişletmeyi, bu 1 324 gözlemle Türkiye için Rrup tabanlı bir şiddet denklemi kalibre etmeyi ve gözlemleri açık bir veri seti olarak yayımlamayı düşünüyorum.

## Veri ve lisanslar

| Veri | Kaynak | Lisans |
|---|---|---|
| Aktif fay izleri | GEM Global Active Faults (Styron & Pagani 2020) | CC BY-SA 4.0 |
| Kuvvetli yer hareketi | KOERI / ORFEUS-EIDA, [turkiye-deprem-verisi](https://github.com/Ayberkrk/turkiye-deprem-verisi) üzerinden | Yalnızca akademik / ticari olmayan kullanım |
| DYFI, ShakeMap istasyonları, saha şiddetleri ve faylar | USGS ComCat | Kamu malı |
| Vs30 rasteri | USGS Global Vs30 Mosaic (Türkiye kırpımı) | Kamu malı |
| Yerleşim nüfusu | GeoNames (`geonamescache`) | CC BY 4.0 |

Ayrıntılar: [`data/faults/README.md`](data/faults/README.md), [`data/observations/README.md`](data/observations/README.md).

## Kaynaklar

- Allen, T.I., Wald, D.J., Worden, C.B. (2012). Intensity attenuation for active crustal regions. *J. Seismology* 16, 409–433. doi:10.1007/s10950-012-9278-7
- Bayrak, E., Nas, M., Bayrak, Y. (2019). New macroseismic intensity predictive models for Turkey. *Acta Geophysica* 67, 1483–1513. doi:10.1007/s11600-019-00357-4
- Kale, Ö., Akkar, S., Ansari, A., Hamzehloo, H. (2015). A ground-motion predictive model for Iran and Turkey. *BSSA* 105(2A), 963–980.
- Worden, C.B., Gerstenberger, M.C., Rhoades, D.A., Wald, D.J. (2012). Probabilistic relationships between ground-motion parameters and MMI in California. *BSSA* 102(1), 204–221. doi:10.1785/0120110156
- Bilal, M., Askan, A. (2014). Relationships between felt intensity and recorded ground-motion parameters for Turkey. *BSSA* 104(1), 484–496. doi:10.1785/0120130093
- Thingbaijam, K.K.S., Mai, P.M., Goda, K. (2017). New empirical earthquake source-scaling laws. *BSSA* 107(5), 2225–2246. doi:10.1785/0120170017
- Styron, R., Pagani, M. (2020). The GEM Global Active Faults Database. *Earthquake Spectra* 36(S1), 160–180. doi:10.1177/8755293020944182
- Pagani, M. vd. (2014). OpenQuake Engine: an open hazard (and risk) software for the Global Earthquake Model. *SRL* 85(3), 692–702.
- Tam kaynakça: [`docs/literatur_taramasi.pdf`](docs/literatur_taramasi.pdf)

Proje [MIT lisansı](LICENSE) ile paylaşılıyor; `data/` altındaki veriler kendi lisanslarına tabi.

Mehmet Emre Ünlü · [GitHub](https://github.com/Memreu) · [LinkedIn](https://www.linkedin.com/in/memreu) · [Kaggle](https://www.kaggle.com/memreu)
