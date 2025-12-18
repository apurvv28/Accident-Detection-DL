"""
AI Models Package Initialization
"""
from .yolov8_detector import YOLOv8Detector
from .yolov11_detector import YOLOv11Detector
from .temporal_analyzer import TemporalAnalyzer
from .deepsort_tracker import DeepSORTTracker
from .trajectory_analyzer import TrajectoryAnalyzer
from .optical_flow import OpticalFlowValidator
from .camera_config import CameraConfig
from .schemas import (
    DetectionResult, TrackedObject, TrajectoryAnalysis,
    OpticalFlowResult, AccidentPrediction, AccidentEvent,
    AlertPayload, ModelConfig
)

__all__ = [
    'YOLOv8Detector',
    'YOLOv11Detector',
    'TemporalAnalyzer',
    'DeepSORTTracker',
    'TrajectoryAnalyzer',
    'OpticalFlowValidator',
    'CameraConfig',
    'DetectionResult',
    'TrackedObject',
    'TrajectoryAnalysis',
    'OpticalFlowResult',
    'AccidentPrediction',
    'AccidentEvent',
    'AlertPayload',
    'ModelConfig'
]