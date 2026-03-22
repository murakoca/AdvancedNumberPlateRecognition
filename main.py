"""
ANPR Sistemi - Ana Giriş Noktası
"""
import sys
import os
from datetime import datetime

from config.settings import SPEED_CONFIG
from models.model_loader import load_optimized_models, create_optimized_ocr, get_device
from gui.main_window import LicensePlateApp

from PyQt5 import QtWidgets

def main():
    # Klasörleri oluştur
    if not os.path.exists("plates"):
        os.makedirs("plates")
    
    # Modelleri yükle
    plate_model_path = r"e:\lpd\Computervisionprojects\ANPR_YOLOv10\weights\best.pt"
    car_model_path = r"e:\lpd\Computervisionprojects\ANPR_YOLOv10\weights\yolov8n.pt"
    
    plate_model, car_model = load_optimized_models(plate_model_path, car_model_path)
    ocr = create_optimized_ocr()
    device = get_device()
    
    # Uygulamayı başlat
    app = QtWidgets.QApplication(sys.argv)
    window = LicensePlateApp(plate_model, car_model, ocr, device)
    window.show()
    
    # Başlangıç logları
    window.log_message("="*70)
    window.log_message("TÜRKİYE PLAKA TANIMA SİSTEMİ - GELİŞMİŞ TEKRAR KONTROLÜ")
    window.log_message("="*70)
    window.log_message(f"Cihaz: {device.upper()}")
    window.log_message(f"Plaka Formatı: 2 Rakam (01-81) + 1-3 Harf + 2-4 Rakam")
    window.log_message(f"Geçersiz Harfler: Ç,Ğ,İ,Ö,Ü,Ş")
    window.log_message("-"*70)
    window.log_message(f"GÖSTERİM ÇÖZÜNÜRLÜĞÜ: {SPEED_CONFIG['DISPLAY_WIDTH']}x{SPEED_CONFIG['DISPLAY_HEIGHT']}")
    window.log_message(f"İŞLEME ÇÖZÜNÜRLÜĞÜ: {SPEED_CONFIG['PROCESS_WIDTH']}x{SPEED_CONFIG['PROCESS_HEIGHT']}")
    window.log_message(f"TEKRAR KONTROLÜ: OCR Karışım Matrisi + Levenshtein")
    window.log_message(f"Birincil Eşik: {SPEED_CONFIG['DUPLICATE_PRIMARY_THRESHOLD']}")
    window.log_message(f"İkincil Eşik: {SPEED_CONFIG['DUPLICATE_SECONDARY_THRESHOLD']}")
    window.log_message(f"Zaman Penceresi: {SPEED_CONFIG['DUPLICATE_TIME_WINDOW']} saniye")
    window.log_message(f"BBox Padding: {SPEED_CONFIG['BBOX_PADDING']}px")
    window.log_message(f"Temporal Voting: {SPEED_CONFIG['TEMPORAL_VOTING_WINDOW']} frame")
    window.log_message("="*70)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()