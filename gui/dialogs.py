"""
Dialog Pencereleri
"""
import os
from PyQt5 import QtWidgets, QtGui, QtCore

class ZoomedCarImageDialog(QtWidgets.QDialog):
    """Büyütülmüş araç görüntüsü diyaloğu"""
    def __init__(self, car_images, ocr_results):
        super().__init__()
        self.car_images = car_images
        self.ocr_results = ocr_results
        self.current_index = 0
        self.initUI()

    def initUI(self):
        self.setWindowTitle("🔍 Büyütülmüş Araç Görüntüsü")
        self.setMinimumSize(700, 550)
        self.setStyleSheet("""
            QDialog { background-color: #2e2e2e; }
            QLabel { color: #d3d3d3; }
            QPushButton { background-color: #444; color: #d3d3d3; border: 1px solid #555; padding: 8px; font-size: 12pt; }
            QPushButton:hover { background-color: #555; }
            QPushButton:disabled { background-color: #333; color: #777; }
        """)
        
        layout = QtWidgets.QVBoxLayout()

        # Görüntü etiketi
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumHeight(400)
        self.image_label.setStyleSheet("border: 2px solid #555; background-color: #1e1e1e;")
        layout.addWidget(self.image_label)

        # OCR sonucu etiketi
        self.ocr_label = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.ocr_label.setFont(font)
        self.ocr_label.setWordWrap(True)
        self.ocr_label.setAlignment(QtCore.Qt.AlignCenter)
        self.ocr_label.setStyleSheet("color: #ffaa00; padding: 10px;")
        layout.addWidget(self.ocr_label)

        # Butonlar
        button_layout = QtWidgets.QHBoxLayout()
        
        self.back_button = QtWidgets.QPushButton("◀ Önceki")
        self.back_button.clicked.connect(self.show_previous_image)
        button_layout.addWidget(self.back_button)

        self.counter_label = QtWidgets.QLabel()
        self.counter_label.setAlignment(QtCore.Qt.AlignCenter)
        self.counter_label.setStyleSheet("color: #d3d3d3; font-size: 12pt;")
        button_layout.addWidget(self.counter_label)

        self.next_button = QtWidgets.QPushButton("Sonraki ▶")
        self.next_button.clicked.connect(self.show_next_image)
        button_layout.addWidget(self.next_button)

        layout.addLayout(button_layout)
        
        # Kapat butonu
        close_button = QtWidgets.QPushButton("✖ Kapat")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("background-color: #6a2a2a;")
        layout.addWidget(close_button)
        
        self.setLayout(layout)
        self.update_image()

    def update_image(self):
        if not self.car_images or self.current_index >= len(self.car_images):
            return

        image_path = self.car_images[self.current_index]
        if os.path.exists(image_path):
            pixmap = QtGui.QPixmap(image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(650, 450, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)

        # OCR sonucunu göster
        if self.current_index < len(self.ocr_results):
            ocr_text = self.ocr_results[self.current_index][:50] if self.ocr_results[self.current_index] else "OCR sonucu yok"
            self.ocr_label.setText(f"📝 OCR: {ocr_text}")
        
        # Sayacı güncelle
        self.counter_label.setText(f"{self.current_index + 1} / {len(self.car_images)}")
        
        # Buton durumlarını güncelle
        self.back_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.car_images) - 1)
        
        # Pencere başlığını güncelle
        self.setWindowTitle(f"🔍 Araç Görüntüsü ({self.current_index + 1}/{len(self.car_images)})")

    def show_next_image(self):
        if self.current_index < len(self.car_images) - 1:
            self.current_index += 1
            self.update_image()

    def show_previous_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_image()