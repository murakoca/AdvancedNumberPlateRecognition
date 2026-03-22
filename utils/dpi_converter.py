"""
300 DPI Dönüştürücü
"""
import cv2
import numpy as np
from config.settings import SPEED_CONFIG

class DPI300Converter:
    def __init__(self):
        self.target_size = SPEED_CONFIG['DPI_OUTPUT_SIZE']
    
    def convert_plate_to_300dpi(self, plate_img):
        if plate_img is None or plate_img.size == 0:
            return plate_img
        
        try:
            h, w = plate_img.shape[:2]
            target_w, target_h = self.target_size
            
            aspect = w / h
            if aspect > 3:
                new_w = target_w
                new_h = int(target_w / aspect)
            else:
                new_h = target_h
                new_w = int(target_h * aspect)
            
            resized = cv2.resize(plate_img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            sharpened = cv2.filter2D(resized, -1, kernel)
            
            return sharpened
        except Exception as e:
            return plate_img