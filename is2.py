import cv2
import mediapipe as mp
import numpy as np
from datetime import datetime

# MediaPipe el tanima ayarlari
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Kamera baslatma ve boyut ayarlama
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Genislik
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # Yukseklik

# Isaret sozlugu - Turkce karakterler duzeltildi
isaret_sozlugu = {
    'A': 'Basparmak acik, diğerleri kapali',
    'B': 'Tum parmaklar acik',
    'C': 'Parmaklar C seklinde kapali',
    'D': 'Isaret parmagi acik',
    'E': 'Tum parmaklar yari kapali',
    'F': 'Basparmak ve isaret birlesik',
    'I': 'Serce parmak acik',
    'L': 'Basparmak ve isaret L seklinde',
    'M': 'Basparmak arada, uc parmak kapali',
    'N': 'Isaret ve orta parmak yari kapali',
    'O': 'Parmaklar yuvarlak',
    'S': 'Yumruk',
    'T': 'Isaret parmagi ile T cizme',
    'U': 'Isaret ve orta parmak bitisik',
    'V': 'Isaret ve orta parmak V seklinde',
    'Y': 'Basparmak ve serce acik'
}

def hesapla_parmak_acilari(landmarks):
    """Parmaklarin acilarini hesaplar"""
    basparmak_acik = landmarks[4][0] > landmarks[3][0]
    isaret_acik = landmarks[8][1] < landmarks[6][1]
    orta_acik = landmarks[12][1] < landmarks[10][1]
    yuzuk_acik = landmarks[16][1] < landmarks[14][1]
    serce_acik = landmarks[20][1] < landmarks[18][1]
    return [basparmak_acik, isaret_acik, orta_acik, yuzuk_acik, serce_acik]

def tani_harf(parmak_durumu):
    """Parmak durumuna gore harfi tanir"""
    [basparmak, isaret, orta, yuzuk, serce] = parmak_durumu
    
    if basparmak and not any([isaret, orta, yuzuk, serce]):
        return 'A'
    elif all([isaret, orta, yuzuk, serce]):
        return 'B'
    elif not any([basparmak, isaret, orta, yuzuk, serce]):
        return 'S'
    elif basparmak and isaret and not any([orta, yuzuk, serce]):
        return 'L'
    elif isaret and orta and not any([basparmak, yuzuk, serce]):
        return 'V'
    elif not any([basparmak, isaret, orta, yuzuk]) and serce:
        return 'I'
    elif basparmak and serce and not any([isaret, orta, yuzuk]):
        return 'Y'
    elif isaret and not any([basparmak, orta, yuzuk, serce]):
        return 'D'
    return '?'

def metni_ortala(img, text, y_position, font_scale=1, color=(255, 255, 255), thickness=2):
    """Metni ekranda ortalar"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    textsize = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = (img.shape[1] - textsize[0]) // 2
    cv2.putText(img, text, (text_x, y_position), font, font_scale, color, thickness)

# İşaret sözlüğü ve diğer tanımlamalar buraya...

class KelimeKayit:
    def __init__(self):
        self.kelime = []
        self.son_harf = None
        self.son_harf_zamani = None
        self.bekleme_suresi = 2.0
        
    def harf_ekle(self, harf):
        simdiki_zaman = datetime.now()
        if self.son_harf != harf:
            self.son_harf = harf
            self.son_harf_zamani = simdiki_zaman
        elif (simdiki_zaman - self.son_harf_zamani).total_seconds() >= self.bekleme_suresi:
            if harf != '?':
                self.kelime.append(harf)
                print(f"Harf eklendi: {harf}")
            self.son_harf = None
            self.son_harf_zamani = None
    
    def kelimeyi_kaydet(self):
        if self.kelime:
            kelime_str = ''.join(self.kelime)
            tarih_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            dosya_adi = f"isaretdili_kelimeler_{tarih_str}.txt"
            with open(dosya_adi, "a", encoding="utf-8") as f:
                f.write(f"{kelime_str}\n")
            print(f"Kelime kaydedildi: {kelime_str}")
            self.kelime = []
    
    def kelimeyi_sil(self):
        self.kelime = []
        self.son_harf = None
        self.son_harf_zamani = None
        print("Kelime silindi")

# Kelime kayıt nesnesini oluştur
kelime_kayit = KelimeKayit()

# Ana döngü
while True:
    success, img = cap.read()
    if not success:
        print("Kamera goruntusu alinamiyor!")
        break
        
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)
    
    # Baslik
    metni_ortala(img, "Isaret Dili Tercumani", 40, 1.5, (0, 0, 0), 3)
    
    # Cikis bilgisi
    cv2.putText(img, "Q: Cikis | S: Kaydet | C: Sil", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    # Harflerin listesi (sag taraf)
    y_pos = 60
    for harf, aciklama in isaret_sozlugu.items():
        text = f"{harf}: {aciklama}"
        cv2.putText(img, text, (img.shape[1] - 500, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)  # Font büyütüldü ve renk siyah yapıldı
        y_pos += 30  # Satır aralığı artırıldı
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # El isaretlerini ciz
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Landmark koordinatlarini al
            h, w, c = img.shape
            landmarks = []
            for lm in hand_landmarks.landmark:
                cx, cy = int(lm.x * w), int(lm.y * h)
                landmarks.append([cx, cy])
            
            # Parmak durumlarini kontrol et
            parmak_durumu = hesapla_parmak_acilari(landmarks)
            
            # Harfi tani
            harf = tani_harf(parmak_durumu)
            
            # Harfi kelimeye ekle
            kelime_kayit.harf_ekle(harf)
            
            # Taninan harfi ortada goster
            metni_ortala(img, f"Taninan Harf: {harf}", h - 150, 2, (0, 0, 0), 3)
            
            # Olusturulan kelimeyi goster
            kelime_str = ''.join(kelime_kayit.kelime) if kelime_kayit.kelime else ""
            metni_ortala(img, f"Olusturulan Kelime: {kelime_str}", h - 200, 1.2, (0, 0, 0), 2)
            
            # Harfin aciklamasini goster
            if harf in isaret_sozlugu:
                aciklama = isaret_sozlugu[harf]
                metni_ortala(img, f"Yapilis: {aciklama}", h - 100, 1, (0, 0, 0), 2)
            
            # Parmak durumunu goster
            parmak_text = f"Parmak Durumu: {''.join(['1' if x else '0' for x in parmak_durumu])}"
            metni_ortala(img, parmak_text, h - 50, 0.8, (0, 0, 0), 2)
    
    # Pencereyi göster
    cv2.namedWindow("Isaret Dili Tercumani", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Isaret Dili Tercumani", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow("Isaret Dili Tercumani", img)
    
    # Tuş kontrolleri
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s'):
        kelime_kayit.kelimeyi_kaydet()
    elif key == ord('c'):
        kelime_kayit.kelimeyi_sil()

# Program sonlandırma
cap.release()
cv2.destroyAllWindows() 