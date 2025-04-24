# Gerekli kütüphanelerin sessiz kurulumunu yapan fonksiyon
import subprocess
import sys
def sessiz_kurulum(paket_adi):
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install"] + paket_adi.split(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

# Kurulacak paketler
sessiz_kurulum("folium geopy")
sessiz_kurulum("colorama")

# Gerekli kütüphaneler içe aktarılıyor
import math
import re
from colorama import Fore, init
from geopy.distance import geodesic
import folium
import webbrowser
import warnings
warnings.filterwarnings("ignore")

# Renkli terminal çıktısı için colorama başlatılıyor
init(autoreset=True)

print("\n📘 Bilgi: Yüzeysel mesafe, yer yüzeyinden episantra olan uzaklıktır.")
print("📘 Hiposantrik mesafe, depremin yer altındaki gerçek konumuna (hiposantr) olan uzaklıktır.")

# DMS (derece/dakika/saniye) formatındaki koordinatları ondalık dereceye çeviren fonksiyon
def dms_to_decimal(koordinat):
    eslesen = re.match(r"(\d+)°(\d+)'([\d.]+)\"?([NSEW])", koordinat.strip())
    if not eslesen:
        raise ValueError("Koordinat formatı hatalı.")
    derece, dakika, saniye, yon = eslesen.groups()
    ondalik = float(derece) + float(dakika)/60 + float(saniye)/3600
    if yon in ['S', 'W']:  # Güney ve batı negatif değer taşır
        ondalik *= -1
    return ondalik

# MMI değerine göre açıklama ve renk döndüren fonksiyon
def mmi_aciklama_renkli(mmi):
    if mmi < 3:
        return ("Hissedilmez", Fore.BLUE)
    elif 3 <= mmi < 4:
        return ("Zayıf hissedilir", Fore.CYAN)
    elif 4 <= mmi < 5:
        return ("Hafif", Fore.LIGHTGREEN_EX)
    elif 5 <= mmi < 6:
        return ("Orta", Fore.YELLOW)
    elif 6 <= mmi < 7:
        return ("Güçlü", Fore.LIGHTYELLOW_EX)
    elif 7 <= mmi < 8:
        return ("Çok güçlü", Fore.LIGHTRED_EX)
    elif 8 <= mmi < 10:
        return ("Yıkıcı", Fore.RED)
    else:
        return ("Aşırı yıkıcı", Fore.MAGENTA)

# MMI değerinden yaklaşık Mw tahmini yapan fonksiyon
def mw_karsilik_mmi(mmi):
    if mmi < 3:
        mw = 2.5 + (mmi - 0) * (0.5 / 3)
    elif 3 <= mmi < 4:
        mw = 3.0 + (mmi - 3) * (0.7 / 1)
    elif 4 <= mmi < 5:
        mw = 3.7 + (mmi - 4) * (0.8 / 1)
    elif 5 <= mmi < 6:
        mw = 4.5 + (mmi - 5) * (0.7 / 1)
    elif 6 <= mmi < 7:
        mw = 5.2 + (mmi - 6) * (0.6 / 1)
    elif 7 <= mmi < 8:
        mw = 5.8 + (mmi - 7) * (0.5 / 1)
    elif 8 <= mmi < 9:
        mw = 6.3 + (mmi - 8) * (0.4 / 1)
    else:
        mw = 6.7 + (mmi - 9) * (0.3 / 1)
    return f"~Mw {round(mw, 1)}"

# Mw, episantr uzaklığı ve derinlik kullanarak MMI tahmini yapan fonksiyon
def tahmini_mmi_hesapla(mw, uzaklik_km, derinlik_km):
    R = math.sqrt(uzaklik_km**2 + derinlik_km**2)  # Hiposantr uzaklığı
    if R < 1:
        R = 1  # Logaritmanın negatif çıkmaması için
    mmi = 1.62 + 1.22 * mw - 0.00255 * R - 1.29 * math.log10(R)
    return round(mmi, 2)

# Ana uygulama başlıyor
try:
    # Depremin episantr koordinatları alınıyor
    print("📍 Depremin episantr koordinatlarını giriniz (örnek: 39°55'29.1\"N 32°50'12.6\"E):")
    deprem_enlem_str = input("Enlem: ")
    deprem_boylam_str = input("Boylam: ")

    # Birden fazla konum girilebilecek yapı
    konumlar = []
    print("\n👤 Konum(lar)ınızı giriniz. Bitirmek için 'q' yazıp enter'a basın.")
    while True:
        konum_enlem_str = input("Enlem (veya 'q' ile bitir): ")
        if konum_enlem_str.strip().lower() == "q":
            break
        konum_boylam_str = input("Boylam: ")
        konumlar.append((konum_enlem_str, konum_boylam_str))

    if not konumlar:
        raise ValueError("En az bir konum girmelisiniz.")

    # Derinlik ve Mw değeri alınıyor
    derinlik = float(input("\n🌐 Depremin derinliği (km): "))
    mw = float(input("🔢 Depremin moment büyüklüğü (Mw): "))

    # Deprem koordinatları ondalık dereceye çevriliyor
    deprem_enlem = dms_to_decimal(deprem_enlem_str)
    deprem_boylam = dms_to_decimal(deprem_boylam_str)

    # Harita oluşturuluyor
    harita = folium.Map(location=[deprem_enlem, deprem_boylam], zoom_start=6)

    # Deprem noktası işaretleniyor
    folium.Marker(
        [deprem_enlem, deprem_boylam],
        popup="📍 Deprem Noktası",
        tooltip="Deprem",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(harita)

    # Tüm girilen konumlar için hesaplama ve işaretleme yapılır
    for i, (konum_enlem_str, konum_boylam_str) in enumerate(konumlar, 1):
        konum_enlem = dms_to_decimal(konum_enlem_str)
        konum_boylam = dms_to_decimal(konum_boylam_str)

        episantr_uzakligi = geodesic((konum_enlem, konum_boylam), (deprem_enlem, deprem_boylam)).km
        hiposantr_uzakligi = math.sqrt(episantr_uzakligi**2 + derinlik**2)

        mmi = tahmini_mmi_hesapla(mw, episantr_uzakligi, derinlik)
        aciklama, renk = mmi_aciklama_renkli(mmi)
        mw_tahmini = mw_karsilik_mmi(mmi)

        # Sonuçları yazdır
        print(f"\n👤 Konum {i}:")
        print(f"{'Yüzeysel Mesafe (km)':<25}: {round(episantr_uzakligi, 2)} km")
        print(f"{'Hiposantr Mesafesi (km)':<25}: {round(hiposantr_uzakligi, 2)} km")
        print(f"{'Tahmini MMI':<25}: {mmi}")
        print(f"{'Şiddet Açıklaması':<25}: {renk + aciklama}")
        print(f"{'Yaklaşık Mw Karşılığı':<25}: {mw_tahmini}")

        # Haritaya kullanıcı konumu işaretleniyor
        folium.Marker(
            [konum_enlem, konum_boylam],
            popup=f"👤 Konum {i}",
            tooltip=f"Konum {i}",
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(harita)

        # Deprem ile konum arasına çizgi ekleniyor
        folium.PolyLine(
            [(deprem_enlem, deprem_boylam), (konum_enlem, konum_boylam)],
            color="orange",
            weight=2,
            tooltip=f"Mesafe: {round(episantr_uzakligi, 2)} km"
        ).add_to(harita)

    # Harita HTML olarak kaydedilip tarayıcıda açılıyor
    harita_path = "deprem_haritasi.html"
    harita.save(harita_path)
    webbrowser.open(harita_path)

except ValueError as hata:
    print(f"⚠️ Hata: {hata}")