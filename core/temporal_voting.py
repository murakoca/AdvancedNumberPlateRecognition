"""
Temporal Voting Buffer - Frame'ler arası oylama
"""
import threading
from collections import Counter, deque

class TemporalVotingBuffer:
    def __init__(self, window_size=7, min_votes=4):
        self.window_size = window_size
        self.min_votes = min_votes
        self.buffer = deque(maxlen=window_size)
        self.lock = threading.RLock()
    
    def add_result(self, plate_text):
        with self.lock:
            self.buffer.append(plate_text)
    
    def get_voted_result(self):
        with self.lock:
            if len(self.buffer) < self.min_votes:
                return None, 0
            
            counter = Counter(self.buffer)
            most_common, count = counter.most_common(1)[0]
            
            if count >= self.min_votes:
                return most_common, count
            return None, 0
    
    def clear(self):
        with self.lock:
            self.buffer.clear()