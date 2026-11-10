"""MMI Intensity Mapper — etkileşimli giriş noktası.

Hesaplamalar `mmi_mapper` paketindedir. Kurulum:  pip install -r requirements.txt
Çalıştırma:  python "1.1.MMI Intensity Mapper.py"

Not: Projenin ilk sürümündeki MMI formülü (1.62 + 1.22·Mw − 0.00255·R − 1.29·log10 R)
yayımlanmış bir kaynağa dayanmadığı için kaldırıldı; yalnızca karşılaştırma amacıyla
`mmi_mapper.ipe.legacy_unverified` adıyla, "doğrulanmamış" etiketiyle tutulur.
Kaynaksız `mw_karsilik_mmi` (MMI → Mw) dönüşümü tamamen kaldırıldı.
"""

from mmi_mapper.cli import main

if __name__ == "__main__":
    main()
