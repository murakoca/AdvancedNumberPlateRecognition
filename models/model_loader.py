"""
Model Yükleme ve Yönetimi
"""
import sys
import torch
from config.settings import SPEED_CONFIG

try:
    from ultralytics import YOLO
except Exception as e:
    print(f"❌ Ultralytics hatası: {e}")
    sys.exit(1)

try:
    from paddleocr import PaddleOCR
except Exception as e:
    print(f"❌ PaddleOCR hatası: {e}")
    sys.exit(1)

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

def load_optimized_models(plate_model_path, car_model_path):
    """Modelleri yükle"""
    print("🔄 Modeller yükleniyor...")
    
    try:
        plate_model = YOLO(plate_model_path)
        car_model = YOLO(car_model_path)
        
        if DEVICE == 'cuda':
            plate_model.to(DEVICE)
            car_model.to(DEVICE)
        
        print("✅ Modeller yüklendi")
        return plate_model, car_model
        
    except Exception as e:
        print(f"❌ Model yükleme hatası: {e}")
        sys.exit(1)

def create_optimized_ocr():
    """PaddleOCR oluştur"""
    return PaddleOCR(
        use_angle_cls=True,
        use_gpu=True if DEVICE == 'cuda' else False,
        lang='en',
        enable_mkldnn=False,
        show_log=False,
        rec_algorithm='SVTR_LCNet',
        det_db_thresh=0.3,
        det_db_box_thresh=0.5,
        drop_score=0.5,
        cpu_threads=1,
        use_mp=True,
        total_process_num=1,
    )

def get_device():
    return DEVICE