"""
Loglama İşlemleri
"""
import json
from datetime import datetime

def log_to_text_file(message, filename="detection_log.txt"):
    with open(filename, "a", encoding='utf-8') as f:
        f.write(f"{datetime.now()}: {message}\n")

def log_to_json_file(data, filename="detections.json"):
    with open(filename, "a", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=True)
        f.write("\n")

class Logger:
    def __init__(self, log_signal=None):
        self.log_signal = log_signal
    
    def log(self, message):
        if self.log_signal:
            self.log_signal.emit(message)
        log_to_text_file(message)
    
    def log_detection(self, plate_text, display_plate, detection_time):
        message = f"Tespit: {plate_text} ({display_plate}) at {detection_time}"
        self.log(message)