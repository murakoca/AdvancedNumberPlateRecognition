"""
Ana Uygulama Penceresi
"""
import os
from datetime import datetime

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt  # Bu satır KESİNLİKLE olmalı

from config.settings import SPEED_CONFIG
from gui.video_thread import VideoThread
from gui.dialogs import ZoomedCarImageDialog
from core.plate_validator import format_tr_plate
from utils.logger import log_to_text_file

import cv2

class LicensePlateApp(QtWidgets.QWidget):
    def __init__(self, plate_model, car_model, ocr, device):
        super().__init__()
        self.plate_model = plate_model
        self.car_model = car_model
        self.ocr = ocr
        self.device = device
        
        self.brightness_sliders = []
        self.conf_sliders = []
        self.iou_sliders = []
        self.nms_sliders = []
        self.pause_buttons = []
        
        self.initUI()
        self.video_threads = [None, None]
        self.video_paths = [None, None]

    def initUI(self):
        self.setWindowTitle('GELİŞMİŞ TEKRAR KONTROLLÜ ANPR (2 KAMERA)')
        self.setGeometry(100, 100, 1800, 900)
        self.setStyleSheet("""
            QWidget { background-color: #2e2e2e; color: #d3d3d3; }
            QLabel { color: #d3d3d3; }
            QPushButton { background-color: #444; color: #d3d3d3; border: 1px solid #555; padding: 6px; }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #666; }
            QPushButton:disabled { background-color: #333; color: #777; }
            QSlider::groove:horizontal { background: #444; height: 6px; }
            QSlider::handle:horizontal { background: #888; width: 10px; margin: -5px 0; }
            QTextEdit { background-color: #333; color: #d3d3d3; }
            QLineEdit { background-color: #333; color: #d3d3d3; border: 1px solid #555; padding: 5px; }
            QListWidget { background-color: #333; color: #d3d3d3; border: 1px solid #555; }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #555; }
        """)

        main_layout = QtWidgets.QHBoxLayout(self)

        # Sol Panel - Kamera Kontrolleri
        left_panel = QtWidgets.QVBoxLayout()
        self.setup_video_controls(left_panel, 0, "KAMERA 1")
        self.setup_video_controls(left_panel, 1, "KAMERA 2")
        main_layout.addLayout(left_panel)

        # Orta Panel - Video Gösterimi
        video_layout = QtWidgets.QVBoxLayout()
        self.video_labels = [QtWidgets.QLabel(self), QtWidgets.QLabel(self)]
        for label in self.video_labels:
            label.setFixedSize(640, 480)
            label.setStyleSheet("border: 2px solid #555; background-color: #1e1e1e;")
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setText("Video Bekleniyor...")
            video_layout.addWidget(label)
        main_layout.addLayout(video_layout)

        # Sağ Panel - Detaylar
        right_panel = QtWidgets.QVBoxLayout()
        
        # Plaka format bilgisi
        info_text = QtWidgets.QLabel(
            f"🏁 TR Plaka Formatı: 34 ABC 123 | 06 A 1234 | 35 AB 12\n"
            f"📊 Tekrar Eşik: {SPEED_CONFIG['DUPLICATE_PRIMARY_THRESHOLD']} | "
            f"⏱️ Zaman: {SPEED_CONFIG['DUPLICATE_TIME_WINDOW']}sn"
        )
        info_text.setStyleSheet("color: #ffaa00; font-weight: bold; background-color: #3a3a3a; padding: 5px; border-radius: 5px;")
        info_text.setWordWrap(True)
        right_panel.addWidget(info_text)
        
        # Arama kutusu
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("🔍 Ara:")
        search_label.setStyleSheet("color: #ffaa00;")
        self.search_box = QtWidgets.QLineEdit(self)
        self.search_box.setPlaceholderText("Plaka ara (örn: 34ABC123)...")
        self.search_box.textChanged.connect(self.filter_detections)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        right_panel.addLayout(search_layout)

        # Tespit listesi
        self.detections_list = QtWidgets.QListWidget()
        self.detections_list.setViewMode(QtWidgets.QListWidget.IconMode)
        self.detections_list.setIconSize(QtCore.QSize(150, 75))
        self.detections_list.setSpacing(10)
        self.detections_list.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.detections_list.itemClicked.connect(self.on_detection_item_clicked)
        right_panel.addWidget(self.detections_list)

        # Log paneli
        log_label = QtWidgets.QLabel("📋 SİSTEM LOGLARI")
        log_label.setStyleSheet("color: #ffaa00; font-weight: bold; margin-top: 10px;")
        right_panel.addWidget(log_label)
        
        self.log_text_edit = QtWidgets.QTextEdit(self)
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMaximumHeight(200)
        self.log_text_edit.setStyleSheet("font-family: monospace; font-size: 10pt;")
        right_panel.addWidget(self.log_text_edit)
        
        # Temizle butonu
        clear_btn = QtWidgets.QPushButton("🗑️ Logları Temizle")
        clear_btn.clicked.connect(self.clear_logs)
        right_panel.addWidget(clear_btn)

        main_layout.addLayout(right_panel)
        
        # Layout oranlarını ayarla
        main_layout.setStretch(0, 1)  # Sol panel
        main_layout.setStretch(1, 2)  # Video panel
        main_layout.setStretch(2, 1)  # Sağ panel
        
        self.setLayout(main_layout)

    def setup_video_controls(self, layout, index, label_text):
        """Kamera kontrol panelini oluştur"""
        # Kamera başlığı
        camera_frame = QtWidgets.QFrame()
        camera_frame.setStyleSheet("QFrame { border: 2px solid #555; border-radius: 5px; margin: 5px; padding: 5px; }")
        camera_layout = QtWidgets.QVBoxLayout(camera_frame)
        
        title_label = QtWidgets.QLabel(label_text)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #ffaa00;")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        camera_layout.addWidget(title_label)

        # Sliders widget
        sliders_widget = QtWidgets.QWidget(self)
        sliders_layout = QtWidgets.QVBoxLayout(sliders_widget)

        # Parlaklık - Qt.Horizontal yerine 1 kullanıyoruz
        brightness_slider = QtWidgets.QSlider(1, self)  # 1 = Horizontal
        brightness_slider.setMinimum(0)
        brightness_slider.setMaximum(100)
        brightness_slider.setValue(50)
        brightness_slider.valueChanged.connect(lambda: self.change_brightness(index, brightness_slider))
        sliders_layout.addWidget(QtWidgets.QLabel('☀️ Parlaklık'))
        sliders_layout.addWidget(brightness_slider)

        # Güven eşiği
        conf_slider = QtWidgets.QSlider(1, self)  # 1 = Horizontal
        conf_slider.setMinimum(30)
        conf_slider.setMaximum(100)
        conf_slider.setValue(45)
        conf_slider.valueChanged.connect(lambda: self.change_confidence(index, conf_slider))
        conf_value_label = QtWidgets.QLabel(f"Güven Eşiği: {conf_slider.value()/100:.2f}")
        sliders_layout.addWidget(QtWidgets.QLabel('🎯 Güven Eşiği'))
        sliders_layout.addWidget(conf_slider)
        sliders_layout.addWidget(conf_value_label)
        conf_slider.valueChanged.connect(lambda v: conf_value_label.setText(f"Güven Eşiği: {v/100:.2f}"))

        # IoU eşiği
        iou_slider = QtWidgets.QSlider(1, self)  # 1 = Horizontal
        iou_slider.setMinimum(30)
        iou_slider.setMaximum(100)
        iou_slider.setValue(50)
        iou_slider.valueChanged.connect(lambda: self.change_iou(index, iou_slider))
        iou_value_label = QtWidgets.QLabel(f"IoU Eşiği: {iou_slider.value()/100:.2f}")
        sliders_layout.addWidget(QtWidgets.QLabel('📐 IoU Eşiği'))
        sliders_layout.addWidget(iou_slider)
        sliders_layout.addWidget(iou_value_label)
        iou_slider.valueChanged.connect(lambda v: iou_value_label.setText(f"IoU Eşiği: {v/100:.2f}"))

        # NMS eşiği
        nms_slider = QtWidgets.QSlider(1, self)  # 1 = Horizontal
        nms_slider.setMinimum(10)
        nms_slider.setMaximum(100)
        nms_slider.setValue(50)
        nms_slider.valueChanged.connect(lambda: self.change_nms(index, nms_slider))
        nms_value_label = QtWidgets.QLabel(f"NMS Eşiği: {nms_slider.value()/100:.2f}")
        sliders_layout.addWidget(QtWidgets.QLabel('🔄 NMS Eşiği'))
        sliders_layout.addWidget(nms_slider)
        sliders_layout.addWidget(nms_value_label)
        nms_slider.valueChanged.connect(lambda v: nms_value_label.setText(f"NMS Eşiği: {v/100:.2f}"))

        self.brightness_sliders.append(brightness_slider)
        self.conf_sliders.append(conf_slider)
        self.iou_sliders.append(iou_slider)
        self.nms_sliders.append(nms_slider)
        camera_layout.addWidget(sliders_widget)
        sliders_widget.hide()

        # Slider göster/gizle butonu
        btn_toggle_sliders = QtWidgets.QPushButton('⚙️ Ayarları Göster', self)
        btn_toggle_sliders.clicked.connect(lambda: self.toggle_sliders(sliders_widget, btn_toggle_sliders))
        camera_layout.addWidget(btn_toggle_sliders)

        # Kontrol butonları
        control_buttons_layout = QtWidgets.QHBoxLayout()
        
        btn_select_video = QtWidgets.QPushButton(f'📁 Video Seç', self)
        btn_select_video.clicked.connect(lambda: self.open_file_dialog(index))
        control_buttons_layout.addWidget(btn_select_video)

        btn_live_view = QtWidgets.QPushButton(f'📹 Canlı Görüntü', self)
        btn_live_view.clicked.connect(lambda: self.start_live_view(index))
        control_buttons_layout.addWidget(btn_live_view)

        btn_start = QtWidgets.QPushButton(f'▶️ Başlat', self)
        btn_start.setStyleSheet("background-color: #2a6b2a;")
        btn_start.clicked.connect(lambda: self.start_detection(index))
        control_buttons_layout.addWidget(btn_start)
        
        camera_layout.addLayout(control_buttons_layout)
        
        # Duraklatma butonları
        pause_buttons_layout = QtWidgets.QHBoxLayout()
        
        pause_button = QtWidgets.QPushButton(f'⏸️ Durdur', self)
        pause_button.clicked.connect(lambda: self.pause_detection(index))
        pause_button.setEnabled(False)
        pause_buttons_layout.addWidget(pause_button)
        
        resume_button = QtWidgets.QPushButton(f'▶️ Devam', self)
        resume_button.clicked.connect(lambda: self.resume_detection(index))
        resume_button.setEnabled(False)
        pause_buttons_layout.addWidget(resume_button)
        
        self.pause_buttons.append((pause_button, resume_button))
        camera_layout.addLayout(pause_buttons_layout)

        # Logo
        logo_label = QtWidgets.QLabel(self)
        logo_label.setText("🚗 ADVANCED ANPR")
        logo_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #ffaa00;")
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        camera_layout.addWidget(logo_label)
        
        layout.addWidget(camera_frame)

    def toggle_sliders(self, sliders_widget, button):
        if sliders_widget.isVisible():
            sliders_widget.hide()
            button.setText("⚙️ Ayarları Göster")
        else:
            sliders_widget.show()
            button.setText("⚙️ Ayarları Gizle")

    def open_file_dialog(self, index):
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setNameFilter("Videolar (*.mp4 *.avi *.mov *.mkv *.flv)")
        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
            self.video_paths[index] = selected_file
            self.log_message(f"📁 Video {index+1}: {os.path.basename(selected_file)}")

    def start_detection(self, index):
        if self.video_threads[index] and self.video_threads[index].isRunning():
            self.video_threads[index].stop()
            self.video_threads[index].wait()

        if not self.video_paths[index]:
            self.log_message(f"⚠️ Hata: Video {index + 1} için dosya seçilmedi.")
            return

        self.log_message(f"🎬 Video {index+1} başlatılıyor: {os.path.basename(self.video_paths[index])}")
        
        self.video_threads[index] = VideoThread(
            self.video_paths[index],
            self.plate_model,
            self.car_model,
            self.ocr,
            self.device,
            brightness=self.brightness_sliders[index].value() / 50,
            conf_threshold=self.conf_sliders[index].value() / 100,
            iou_threshold=self.iou_sliders[index].value() / 100,
            nms_threshold=self.nms_sliders[index].value() / 100,
            camera_id=index
        )
        
        self.video_threads[index].change_pixmap_signal.connect(
            lambda frame, idx=index: self.update_video_frame(frame, idx)
        )
        self.video_threads[index].add_detection_signal.connect(self.update_detections)
        self.video_threads[index].log_signal.connect(self.log_message)
        self.video_threads[index].video_ended_signal.connect(lambda: self.on_video_ended(index))
        self.video_threads[index].start()
        
        pause_button, resume_button = self.pause_buttons[index]
        pause_button.setEnabled(True)
        resume_button.setEnabled(False)

    def start_live_view(self, index):
        if self.video_threads[index] and self.video_threads[index].isRunning():
            self.video_threads[index].stop()
            self.video_threads[index].wait()

        camera_index = index
        self.log_message(f"📹 Kamera {index+1} canlı görüntü başlatılıyor...")
        
        self.video_threads[index] = VideoThread(
            video_path=camera_index,
            plate_model=self.plate_model,
            car_model=self.car_model,
            ocr=self.ocr,
            device=self.device,
            brightness=self.brightness_sliders[index].value() / 50,
            conf_threshold=self.conf_sliders[index].value() / 100,
            iou_threshold=self.iou_sliders[index].value() / 100,
            nms_threshold=self.nms_sliders[index].value() / 100,
            camera_id=index
        )
        
        self.video_threads[index].change_pixmap_signal.connect(
            lambda frame, idx=index: self.update_video_frame(frame, idx)
        )
        self.video_threads[index].add_detection_signal.connect(self.update_detections)
        self.video_threads[index].log_signal.connect(self.log_message)
        self.video_threads[index].video_ended_signal.connect(lambda: self.on_video_ended(index))
        self.video_threads[index].start()
        
        pause_button, resume_button = self.pause_buttons[index]
        pause_button.setEnabled(True)
        resume_button.setEnabled(False)

    def pause_detection(self, index):
        if self.video_threads[index] and self.video_threads[index].isRunning():
            self.video_threads[index].pause()
            self.log_message(f"⏸️ Kamera {index + 1}: Algılama durduruldu")
            pause_button, resume_button = self.pause_buttons[index]
            pause_button.setEnabled(False)
            resume_button.setEnabled(True)

    def resume_detection(self, index):
        if self.video_threads[index] and self.video_threads[index].isRunning():
            self.video_threads[index].resume()
            self.log_message(f"▶️ Kamera {index + 1}: Algılama devam ediyor")
            pause_button, resume_button = self.pause_buttons[index]
            pause_button.setEnabled(True)
            resume_button.setEnabled(False)

    def on_video_ended(self, index):
        pause_button, resume_button = self.pause_buttons[index]
        pause_button.setEnabled(False)
        resume_button.setEnabled(False)
        self.log_message(f"🏁 Kamera {index + 1}: Video sonlandı")

    def update_video_frame(self, frame, index):
        if frame is None or frame.size == 0:
            return
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qimg = QtGui.QImage(rgb_frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        self.video_labels[index].setPixmap(pixmap.scaled(
            self.video_labels[index].size(), 
            QtCore.Qt.KeepAspectRatio, 
            QtCore.Qt.SmoothTransformation
        ))

    def update_detections(self, plate_image_path, car_image_path, ocr_text, formatted_plate_text, detection_time):
        """Yeni tespit eklendiğinde"""
        list_item = QtWidgets.QListWidgetItem()
        
        # Plaka görselini yükle
        if os.path.exists(car_image_path):
            icon = QtGui.QIcon(car_image_path)
            list_item.setIcon(icon)
        
        # Formatlı gösterim
        display_plate = format_tr_plate(formatted_plate_text)
        list_item.setText(f"🚗 {display_plate}\n⏱️ {detection_time.split()[1] if ' ' in detection_time else detection_time}\n📝 {ocr_text[:20]}")
        
        # Verileri sakla
        list_item.setData(QtCore.Qt.UserRole, car_image_path)
        list_item.setData(QtCore.Qt.UserRole + 1, ocr_text)
        list_item.setData(QtCore.Qt.UserRole + 2, plate_image_path)
        
        self.detections_list.insertItem(0, list_item)
        
        # Log dosyasına yaz
        log_to_text_file(f"Tespit: {formatted_plate_text} ({display_plate}) at {detection_time}")
        
        # Liste çok büyürse temizle
        if self.detections_list.count() > 500:
            for i in range(self.detections_list.count() - 1, 499, -1):
                self.detections_list.takeItem(i)

    def on_detection_item_clicked(self, item):
        """Tespit listesindeki bir öğeye tıklandığında"""
        item_index = self.detections_list.row(item)

        car_images = []
        ocr_results = []

        for i in range(self.detections_list.count()):
            list_item = self.detections_list.item(i)
            car_image_path = list_item.data(QtCore.Qt.UserRole)
            ocr_text = list_item.data(QtCore.Qt.UserRole + 1)
            
            if car_image_path and os.path.exists(car_image_path):
                car_images.append(car_image_path)
                ocr_results.append(ocr_text)

        if car_images:
            dialog = ZoomedCarImageDialog(car_images, ocr_results)
            dialog.current_index = item_index
            dialog.update_image()
            dialog.exec_()
        else:
            QtWidgets.QMessageBox.warning(self, "Hata", "Gösterilecek görüntü yok.")

    def log_message(self, message):
        """Log mesajı ekle"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text_edit.append(f"[{timestamp}] {message}")
        # Otomatik scroll aşağı
        scrollbar = self.log_text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        log_to_text_file(message)

    def clear_logs(self):
        """Logları temizle"""
        self.log_text_edit.clear()
        self.log_message("Loglar temizlendi")

    def filter_detections(self, text):
        """Arama filtresi"""
        search_text = text.upper().replace(" ", "").replace("-", "")
        for i in range(self.detections_list.count()):
            item = self.detections_list.item(i)
            item_text = item.text().upper()
            item.setHidden(search_text not in item_text)

    def change_brightness(self, index, slider):
        if self.video_threads[index]:
            self.video_threads[index].brightness = slider.value() / 50

    def change_confidence(self, index, slider):
        if self.video_threads[index]:
            self.video_threads[index].conf_threshold = slider.value() / 100

    def change_iou(self, index, slider):
        if self.video_threads[index]:
            self.video_threads[index].iou_threshold = slider.value() / 100

    def change_nms(self, index, slider):
        if self.video_threads[index]:
            self.video_threads[index].nms_threshold = slider.value() / 100
            self.log_message(f"🔧 Kamera {index + 1}: NMS = {slider.value()/100:.2f}")