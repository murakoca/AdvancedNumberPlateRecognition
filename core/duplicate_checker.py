"""
Gelişmiş Tekrar Kontrol Sistemi
"""
import threading
from datetime import datetime, timedelta
from collections import Counter

class AdvancedDuplicateChecker:
    """OCR Karışım Matrisi ile Gelişmiş Tekrar Kontrolü"""
    
    OCR_CONFUSION_MATRIX = {
        '0': ['O', 'Q', 'D'], 'O': ['0', 'Q'],
        '1': ['I', 'L', 'T'], 'I': ['1', 'L'],
        '2': ['Z', 'N'], 'Z': ['2', 'N'],
        '5': ['S', 'B'], 'S': ['5', 'B'],
        '8': ['B', '3', 'S'], 'B': ['8', '3', '5'],
        '6': ['G', 'C'], 'G': ['6', 'C'],
        '9': ['g', 'q', 'G'], 'C': ['G', '6'],
        'D': ['O', '0'], 'U': ['V', 'W'],
        'V': ['U', 'W'], 'M': ['N', 'W'],
        'N': ['M', 'W', '2'], 'T': ['7', '1', 'I'],
        '7': ['T', '1'], 'A': ['4', 'H'],
        'H': ['A', 'K'], 'K': ['H', 'X'],
        'P': ['R', 'F'], 'R': ['P', 'F'],
    }
    
    def __init__(self, time_window=30, primary_threshold=0.95, 
                 secondary_threshold=0.85, strict_mode=False):
        self.time_window = time_window
        self.primary_threshold = primary_threshold
        self.secondary_threshold = secondary_threshold
        self.strict_mode = strict_mode
        self.recent_plates = []
        self.plate_groups = {}
        self.lock = threading.RLock()
        self.log_signal = None
    
    def set_log_signal(self, log_signal):
        self.log_signal = log_signal
    
    def _log(self, message):
        if self.log_signal:
            self.log_signal.emit(message)
    
    def _ocr_similarity(self, s1, s2):
        if not s1 or not s2:
            return 0.0
        
        if abs(len(s1) - len(s2)) > 2:
            return 0.0
        
        max_len = max(len(s1), len(s2))
        s1_pad = s1.ljust(max_len, ' ')
        s2_pad = s2.ljust(max_len, ' ')
        
        matches = 0
        for i in range(max_len):
            c1 = s1_pad[i]
            c2 = s2_pad[i]
            
            if c1 == c2:
                matches += 1.0
            elif c2 in self.OCR_CONFUSION_MATRIX.get(c1, []):
                matches += 0.9
            elif c1 in self.OCR_CONFUSION_MATRIX.get(c2, []):
                matches += 0.9
            elif c1.isdigit() and c2.isdigit():
                if abs(int(c1) - int(c2)) <= 1:
                    matches += 0.7
                else:
                    matches += 0.3
            elif c1.isalpha() and c2.isalpha():
                if abs(ord(c1) - ord(c2)) <= 2:
                    matches += 0.6
                else:
                    matches += 0.2
            else:
                matches += 0.1
        
        return matches / max_len
    
    def _levenshtein_similarity(self, s1, s2):
        if not s1 or not s2:
            return 0.0
        
        if abs(len(s1) - len(s2)) > 2:
            return 0.0
        
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        max_len = max(len(s1), len(s2))
        return 1 - (dp[m][n] / max_len) if max_len > 0 else 0
    
    def _normalize_plate(self, plate_text):
        if not plate_text or len(plate_text) < 7:
            return plate_text
        
        normalized = plate_text.upper()
        
        if normalized[:2].isdigit():
            remaining = normalized[2:]
            letters = ""
            numbers = ""
            
            for char in remaining:
                if char.isalpha():
                    letters += char
                elif char.isdigit():
                    numbers += char
            
            replacements = {
                '0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B',
                'O': '0', 'I': '1', 'Z': '2', 'S': '5', 'B': '8',
            }
            
            corrected_letters = ""
            for char in letters:
                if char.isdigit() and char in replacements:
                    corrected_letters += replacements[char]
                else:
                    corrected_letters += char
            
            normalized = normalized[:2] + corrected_letters + numbers
        
        return normalized
    
    def is_duplicate(self, plate_text, camera_id, confidence=0.5):
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.time_window)
            self.recent_plates = [p for p in self.recent_plates if p[1] > cutoff]
            
            normalized_plate = self._normalize_plate(plate_text)
            
            best_match = None
            best_similarity = 0
            best_plate = None
            best_reason = "YENİ PLAKA"
            
            for existing_plate, timestamp, cam_id, conf in self.recent_plates:
                if cam_id != camera_id:
                    continue
                
                ocr_sim = self._ocr_similarity(plate_text, existing_plate)
                lev_sim = self._levenshtein_similarity(plate_text, existing_plate)
                norm_sim = self._levenshtein_similarity(
                    self._normalize_plate(plate_text),
                    self._normalize_plate(existing_plate)
                )
                
                confidence_weight = min(conf, 0.9) / 0.9
                
                if self.strict_mode:
                    combined_sim = (ocr_sim * 0.6 + lev_sim * 0.2 + norm_sim * 0.2) * confidence_weight
                else:
                    combined_sim = (ocr_sim * 0.5 + lev_sim * 0.3 + norm_sim * 0.2) * confidence_weight
                
                if combined_sim >= 0.95:
                    reason = "TAM EŞLEŞME"
                elif combined_sim >= 0.90:
                    reason = "ÇOK YÜKSEK BENZERLİK"
                elif combined_sim >= 0.85:
                    reason = "OCR KARIŞIM"
                elif combined_sim >= 0.80:
                    reason = "YÜKSEK BENZERLİK"
                else:
                    reason = "DÜŞÜK BENZERLİK"
                
                if combined_sim > best_similarity:
                    best_similarity = combined_sim
                    best_match = existing_plate
                    best_plate = existing_plate
                    best_reason = reason
            
            if best_similarity >= self.primary_threshold:
                return True, best_plate, best_similarity, f"{best_reason} (P)"
            elif best_similarity >= self.secondary_threshold:
                return True, best_plate, best_similarity, f"{best_reason} (S)"
            
            return False, None, best_similarity, best_reason
    
    def add_plate(self, plate_text, camera_id, confidence=0.5):
        with self.lock:
            self.recent_plates.append((plate_text, datetime.now(), camera_id, confidence))
            normalized = self._normalize_plate(plate_text)
            if normalized not in self.plate_groups:
                self.plate_groups[normalized] = set()
            self.plate_groups[normalized].add(plate_text)