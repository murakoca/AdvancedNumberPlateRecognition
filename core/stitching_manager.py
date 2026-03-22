"""
Stitching Manager - Plaka gözlemlerini birleştirir
"""
import threading
from collections import Counter
from datetime import datetime
from config.settings import SPEED_CONFIG

class PlateObservation:
    def __init__(self, plate_text, confidence, timestamp, frame_number, plate_path):
        self.plate_text = plate_text
        self.confidence = confidence
        self.timestamp = timestamp
        self.frame_number = frame_number
        self.plate_path = plate_path

class StitchedPlate:
    def __init__(self, plate_text, confidence, observations, camera_id):
        self.plate_text = plate_text
        self.confidence = confidence
        self.observations = observations
        self.camera_id = camera_id
        self.first_seen = min([obs.timestamp for obs in observations])
        self.last_seen = max([obs.timestamp for obs in observations])
        self.frame_count = len(observations)

class StitchingManager:
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.observations = {}
        self.stitched_results = {}
        self.lock = threading.RLock()
    
    def add_observation(self, plate_text, confidence, plate_path, frame_number):
        with self.lock:
            timestamp = datetime.now()
            obs = PlateObservation(plate_text, confidence, timestamp, frame_number, plate_path)
            
            if plate_text not in self.observations:
                self.observations[plate_text] = []
            
            self.observations[plate_text].append(obs)
            
            if len(self.observations[plate_text]) > SPEED_CONFIG['STITCHING_WINDOW']:
                self.observations[plate_text] = self.observations[plate_text][-SPEED_CONFIG['STITCHING_WINDOW']:]
            
            if len(self.observations[plate_text]) >= SPEED_CONFIG['STITCHING_MIN_OBSERVATIONS']:
                return self._stitch_plate(plate_text)
            
            return None
    
    def _stitch_plate(self, plate_text):
        obs_list = self.observations[plate_text]
        plate_length = len(plate_text)
        position_votes = [[] for _ in range(plate_length)]
        
        for obs in obs_list:
            text = obs.plate_text
            if len(text) == plate_length:
                for i, char in enumerate(text):
                    position_votes[i].append(char)
        
        stitched_chars = []
        confidences = []
        
        for i, votes in enumerate(position_votes):
            if votes:
                counter = Counter(votes)
                most_common, count = counter.most_common(1)[0]
                ratio = count / len(votes)
                
                if ratio >= SPEED_CONFIG['STITCHING_MAJORITY_RATIO']:
                    stitched_chars.append(most_common)
                    confidences.append(ratio)
                else:
                    stitched_chars.append(plate_text[i])
                    confidences.append(0.5)
            else:
                stitched_chars.append(plate_text[i])
                confidences.append(0.3)
        
        stitched_text = ''.join(stitched_chars)
        avg_confidence = sum(confidences) / plate_length
        boosted_confidence = min(1.0, avg_confidence * SPEED_CONFIG['STITCHING_CONFIDENCE_BOOST'])
        
        stitched = StitchedPlate(stitched_text, boosted_confidence, obs_list, self.camera_id)
        self.stitched_results[stitched_text] = stitched
        
        return stitched