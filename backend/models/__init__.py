"""
AI Models Package Initialization
"""
from .yolov8_detector import YOLOv8Detector
from .temporal_analyzer import TemporalAnalyzer
from .camera_config import CameraConfig
from .schemas import (
    DetectionResult, TrackedObject, 
    AccidentPrediction, ModelConfig
)

__all__ = [
    'YOLOv8Detector',
    'TemporalAnalyzer',
    'CameraConfig',
    'DetectionResult',
    'TrackedObject',
    'AccidentPrediction',
    'ModelConfig'
]