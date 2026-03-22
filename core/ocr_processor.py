"""
OCR Pipeline - Production seviyesinde görüntü işleme
"""
import cv2
import numpy as np
from config.settings import SPEED_CONFIG

class ProductionOCRProcessor:
    """Production seviyesinde OCR pipeline"""
    
    @staticmethod
    def add_bbox_padding(box, frame_shape, pad=15):
        x1, y1, x2, y2 = box
        h, w = frame_shape[:2]
        
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad)
        y2 = min(h, y2 + pad)
        
        return x1, y1, x2, y2
    
    @staticmethod
    def resize_for_ocr(plate_img, factor=1.0):
        return plate_img
    
    @staticmethod
    def enhance_contrast(plate_img):
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img.copy()
        
        clahe = cv2.createCLAHE(
            clipLimit=SPEED_CONFIG['CLAHE_CLIP_LIMIT'],
            tileGridSize=SPEED_CONFIG['CLAHE_GRID_SIZE']
        )
        enhanced = clahe.apply(gray)
        
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    
    @staticmethod
    def full_pipeline(plate_img):
        if plate_img is None or plate_img.size == 0:
            return None
        
        try:
            enhanced = ProductionOCRProcessor.enhance_contrast(plate_img)
            return enhanced
        except Exception as e:
            print(f"❌ OCR Pipeline hatası: {e}")
            return plate_img