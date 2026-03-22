"""
Video İşleme Thread'i
"""
import os
import cv2
import numpy as np
from datetime import datetime
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import SPEED_CONFIG
from core.plate_validator import is_valid_tr_plate, format_tr_plate
from core.duplicate_checker import AdvancedDuplicateChecker
from core.temporal_voting import TemporalVotingBuffer
from core.stitching_manager import StitchingManager
from core.ocr_processor import ProductionOCRProcessor
from utils.dpi_converter import DPI300Converter

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    add_detection_signal = pyqtSignal(str, str, str, str, str)
    log_signal = pyqtSignal(str)
    video_ended_signal = pyqtSignal()

    def __init__(self, video_path, plate_model, car_model, ocr, device, 
                 brightness=1.0, conf_threshold=0.45, iou_threshold=0.45, 
                 nms_threshold=0.5, camera_id=0):
        super().__init__()
        self.video_path = video_path
        self.plate_model = plate_model
        self.car_model = car_model
        self.ocr = ocr
        self.device = device
        self.brightness = brightness
        self.conf_threshold = max(conf_threshold, SPEED_CONFIG['MIN_DETECTION_CONFIDENCE'])
        self.iou_threshold = iou_threshold
        self.nms_threshold = nms_threshold
        self.camera_id = camera_id
        self._run_flag = True
        self.detected_plate_count = 0
        self.cooldown_seconds = SPEED_CONFIG['PLATE_COOLDOWN']
        self.unique_plates = set()
        
        # Optimizasyon
        self.frame_counter = 0
        self.frame_skip = SPEED_CONFIG['FRAME_SKIP']
        self.paused = False
        self.last_frame_time = datetime.now()
        
        # STITCHING
        self.stitching_manager = StitchingManager(camera_id=camera_id)
        
        # TEKRAR KONTROLÜ
        self.duplicate_checker = AdvancedDuplicateChecker(
            time_window=SPEED_CONFIG['DUPLICATE_TIME_WINDOW'],
            primary_threshold=SPEED_CONFIG['DUPLICATE_PRIMARY_THRESHOLD'],
            secondary_threshold=SPEED_CONFIG['DUPLICATE_SECONDARY_THRESHOLD'],
            strict_mode=SPEED_CONFIG['DUPLICATE_STRICT_MODE']
        )
        
        # TEMPORAL VOTING
        self.temporal_voting = TemporalVotingBuffer(
            window_size=SPEED_CONFIG['TEMPORAL_VOTING_WINDOW'],
            min_votes=SPEED_CONFIG['TEMPORAL_VOTING_MIN_VOTES']
        )
        
        # 300 DPI
        self.dpi_converter = DPI300Converter()
        
        # OCR Pipeline
        self.ocr_pipeline = ProductionOCRProcessor()
        
        # Session klasörü
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_folder = f"plates/session_{session_id}"
        os.makedirs(self.session_folder, exist_ok=True)
        os.makedirs(f"{self.session_folder}/cars", exist_ok=True)
        os.makedirs(f"{self.session_folder}/plates", exist_ok=True)
        os.makedirs(f"{self.session_folder}/plates_300dpi", exist_ok=True)

    def run(self):
        self.duplicate_checker.set_log_signal(self.log_signal)
        
        if isinstance(self.video_path, str) and not os.path.exists(self.video_path):
            self.log_signal.emit(f"Error: Video dosyası bulunamadı: {self.video_path}")
            return

        cap = cv2.VideoCapture(self.video_path)
        if isinstance(self.video_path, int):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, SPEED_CONFIG['PROCESS_WIDTH'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SPEED_CONFIG['PROCESS_HEIGHT'])
        
        target_frame_time = 1.0 / SPEED_CONFIG['TARGET_FPS']
        
        while self._run_flag and cap.isOpened():
            if self.paused:
                self.msleep(100)
                continue
            
            self.frame_counter += 1
            if self.frame_counter % self.frame_skip != 0:
                cap.grab()
                continue
            
            ret, frame = cap.read()
            if not ret:
                if isinstance(self.video_path, int):
                    self.msleep(100)
                    continue
                else:
                    self.video_ended_signal.emit()
                    break
            
            # İşleme boyutunda frame
            process_frame = cv2.resize(frame, (SPEED_CONFIG['PROCESS_WIDTH'], SPEED_CONFIG['PROCESS_HEIGHT']))
            
            if self.brightness != 1.0:
                process_frame = cv2.convertScaleAbs(process_frame, alpha=self.brightness, beta=0)
            
            # Araç tespiti
            car_results = self.detect_cars(process_frame)
            
            # Gösterim için frame
            display_frame = cv2.resize(process_frame, (SPEED_CONFIG['DISPLAY_WIDTH'], SPEED_CONFIG['DISPLAY_HEIGHT']))
            
            for car_result in car_results:
                car_boxes = car_result.boxes
                if car_boxes is None:
                    continue
                    
                for car_box in car_boxes:
                    if car_box.conf[0] < self.conf_threshold:
                        continue
                    
                    cx1, cy1, cx2, cy2 = map(int, car_box.xyxy[0])
                    
                    car_area = (cx2 - cx1) * (cy2 - cy1)
                    if SPEED_CONFIG['SKIP_SMALL_CARS'] and car_area < SPEED_CONFIG['MIN_CAR_SIZE']:
                        continue
                    
                    car_image = process_frame[cy1:cy2, cx1:cx2]
                    if car_image.size == 0:
                        continue
                    
                    detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Araç görüntüsünü kaydet
                    car_image_small = cv2.resize(car_image, (SPEED_CONFIG['DISPLAY_WIDTH'], SPEED_CONFIG['DISPLAY_HEIGHT']))
                    car_image_path = f"{self.session_folder}/cars/car_{self.detected_plate_count}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
                    cv2.imwrite(car_image_path, car_image_small)
                    
                    # Plaka tespiti
                    try:
                        plate_results = self.plate_model.predict(
                            car_image,
                            conf=self.conf_threshold,
                            iou=self.nms_threshold,
                            device=self.device,
                            verbose=False,
                            max_det=SPEED_CONFIG['MAX_PLATES_PER_CAR']
                        )
                    except Exception as e:
                        self.log_signal.emit(f"Plate prediction error: {str(e)}")
                        plate_results = []
                    
                    for plate_result in plate_results:
                        plate_boxes = plate_result.boxes
                        if plate_boxes is None:
                            continue
                            
                        for plate_box in plate_boxes:
                            if plate_box.conf[0] < self.conf_threshold:
                                continue
                                
                            px1, py1, px2, py2 = map(int, plate_box.xyxy[0])
                            
                            # Bounding box padding
                            pad = SPEED_CONFIG['BBOX_PADDING']
                            px1_pad = max(0, px1 - pad)
                            py1_pad = max(0, py1 - pad)
                            px2_pad = min(car_image.shape[1], px2 + pad)
                            py2_pad = min(car_image.shape[0], py2 + pad)
                            
                            if px2_pad > px1_pad and py2_pad > py1_pad:
                                plate_image = car_image[py1_pad:py2_pad, px1_pad:px2_pad]
                                
                                if plate_image.size > 0:
                                    # Gösterim koordinatları
                                    scale_x = SPEED_CONFIG['DISPLAY_WIDTH'] / SPEED_CONFIG['PROCESS_WIDTH']
                                    scale_y = SPEED_CONFIG['DISPLAY_HEIGHT'] / SPEED_CONFIG['PROCESS_HEIGHT']
                                    
                                    d_cx1 = int(cx1 * scale_x)
                                    d_cy1 = int(cy1 * scale_y)
                                    d_cx2 = int(cx2 * scale_x)
                                    d_cy2 = int(cy2 * scale_y)
                                    
                                    d_px1 = int(px1_pad * scale_x)
                                    d_py1 = int(py1_pad * scale_y)
                                    d_px2 = int(px2_pad * scale_x)
                                    d_py2 = int(py2_pad * scale_y)
                                    
                                    # Dikdörtgen çiz
                                    cv2.rectangle(display_frame, 
                                                (d_cx1 + d_px1, d_cy1 + d_py1), 
                                                (d_cx1 + d_px2, d_cy1 + d_py2), 
                                                (0, 255, 0), 2)
                                    
                                    # OCR Pipeline
                                    processed_plate = self.ocr_pipeline.full_pipeline(plate_image)
                                    
                                    if processed_plate is not None:
                                        try:
                                            ocr_result = self.ocr.ocr(processed_plate, rec=True, cls=True)
                                            ocr_text = " ".join(
                                                [item[1][0] for line in ocr_result if line is not None 
                                                 for item in line if item is not None]
                                            ) if ocr_result else ""
                                        except Exception as e:
                                            self.log_signal.emit(f"OCR Error: {e}")
                                            ocr_text = ""
                                        
                                        raw_plate = ocr_text.replace(" ", "").upper()
                                        
                                        if raw_plate and is_valid_tr_plate(raw_plate):
                                            formatted_plate = format_tr_plate(raw_plate)
                                            
                                            # Temporal Voting
                                            self.temporal_voting.add_result(raw_plate)
                                            voted_plate, vote_count = self.temporal_voting.get_voted_result()
                                            
                                            if voted_plate:
                                                final_plate = voted_plate
                                            else:
                                                final_plate = raw_plate
                                            
                                            # Tekrar kontrolü
                                            is_dup, existing, similarity, reason = self.duplicate_checker.is_duplicate(
                                                final_plate, 
                                                self.camera_id,
                                                plate_box.conf[0].item()
                                            )
                                            
                                            if is_dup:
                                                self.log_signal.emit(f"⏭️ TEKRAR: {final_plate} -> {existing} (benzerlik: {similarity:.2f})")
                                                continue
                                            
                                            self.log_signal.emit(f"🆕 YENİ PLAKA: {final_plate}")
                                            
                                            # Plaka kaydet
                                            plate_image_path = f"{self.session_folder}/plates/plate_{self.detected_plate_count}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
                                            cv2.imwrite(plate_image_path, plate_image)
                                            
                                            # 300 DPI kaydet
                                            if SPEED_CONFIG['ENABLE_300DPI']:
                                                plate_300dpi = self.dpi_converter.convert_plate_to_300dpi(plate_image)
                                                plate_300_path = f"{self.session_folder}/plates_300dpi/plate_300dpi_{self.detected_plate_count}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
                                                cv2.imwrite(plate_300_path, plate_300dpi)
                                            
                                            self.duplicate_checker.add_plate(final_plate, self.camera_id, plate_box.conf[0].item())
                                            
                                            # Stitching
                                            if SPEED_CONFIG['STITCHING_ENABLED']:
                                                stitched = self.stitching_manager.add_observation(
                                                    final_plate,
                                                    plate_box.conf[0].item(),
                                                    plate_image_path,
                                                    self.frame_counter
                                                )
                                                
                                                if stitched:
                                                    self.log_signal.emit(f"🧵 STITCHING: {final_plate} -> {stitched.plate_text}")
                                                    final_plate = stitched.plate_text
                                            
                                            self.unique_plates.add(final_plate)
                                            self.detected_plate_count += 1
                                            
                                            self.add_detection_signal.emit(
                                                plate_image_path,
                                                car_image_path,
                                                ocr_text,
                                                final_plate,
                                                detection_time
                                            )
                                            
                                            cv2.putText(display_frame, final_plate, 
                                                       (d_cx1 + d_px1, d_cy1 + d_py1 - 10),
                                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            self.change_pixmap_signal.emit(display_frame)
            
            # FPS kontrolü
            elapsed = (datetime.now() - self.last_frame_time).total_seconds()
            if elapsed < target_frame_time:
                sleep_ms = int((target_frame_time - elapsed) * 1000)
                self.msleep(max(1, sleep_ms))
            
            self.last_frame_time = datetime.now()
        
        cap.release()

    def detect_cars(self, frame):
        try:
            results = self.car_model.predict(
                frame,
                conf=self.conf_threshold,
                iou=self.nms_threshold,
                device=self.device,
                verbose=False,
                max_det=SPEED_CONFIG['MAX_CARS_PER_FRAME'],
                classes=[2, 3, 5, 7]  # Araç sınıfları
            )
            return results
        except Exception as e:
            self.log_signal.emit(f"Detection error: {str(e)}")
            return []

    def stop(self):
        self._run_flag = False
        self.wait()

    def pause(self):
        self.paused = True
        self.log_signal.emit("⏸️ Duraklatıldı")

    def resume(self):
        self.paused = False
        self.log_signal.emit("▶️ Devam")