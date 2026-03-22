"""
Core modülü - Ana iş mantığı
"""
from .plate_validator import TRPlateValidator, is_valid_tr_plate, format_tr_plate
from .duplicate_checker import AdvancedDuplicateChecker
from .temporal_voting import TemporalVotingBuffer
from .stitching_manager import StitchingManager, PlateObservation, StitchedPlate
from .ocr_processor import ProductionOCRProcessor

__all__ = [
    'TRPlateValidator',
    'is_valid_tr_plate',
    'format_tr_plate',
    'AdvancedDuplicateChecker',
    'TemporalVotingBuffer',
    'StitchingManager',
    'PlateObservation',
    'StitchedPlate',
    'ProductionOCRProcessor'
]