"""
Görüntü işleme yardımcı fonksiyonları
"""
import cv2
import numpy as np

class ImageUtils:
    """Görüntü işleme yardımcı sınıfı"""
    
    @staticmethod
    def resize_aspect(image, width=None, height=None, inter=cv2.INTER_AREA):
        """En-boy oranını koruyarak yeniden boyutlandır"""
        dim = None
        h, w = image.shape[:2]
        
        if width is None and height is None:
            return image
        
        if width is None:
            ratio = height / float(h)
            dim = (int(w * ratio), height)
        else:
            ratio = width / float(w)
            dim = (width, int(h * ratio))
        
        return cv2.resize(image, dim, interpolation=inter)
    
    @staticmethod
    def add_text_background(image, text, position, font_scale=0.7, 
                            thickness=2, text_color=(0, 255, 0), 
                            bg_color=(0, 0, 0), padding=5):
        """Arka planlı metin ekle"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        x, y = position
        cv2.rectangle(image, 
                     (x - padding, y - text_height - padding),
                     (x + text_width + padding, y + padding),
                     bg_color, -1)
        
        cv2.putText(image, text, (x, y), font, font_scale, text_color, thickness)
        
        return image
    
    @staticmethod
    def enhance_plate(image):
        """Plaka görüntüsünü iyileştir"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Histogram eşitleme
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Bilateral filtre (gürültü azaltma)
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # Keskinleştirme
        kernel = np.array([[-1, -1, -1],
                          [-1, 9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        return sharpened