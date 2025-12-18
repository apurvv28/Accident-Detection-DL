"""
Schema definitions for detections, tracked objects and accident predictions.
Uses Pydantic for validation and easy serialization.
"""
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import numpy as np


class DetectionResult(BaseModel):
    bbox: Tuple[int, int, int, int] = Field(..., description="x,y,w,h")
    confidence: float = Field(..., ge=0.0, le=1.0)
    class_name: str
    class_id: int
    tracking_id: Optional[int] = None
    is_vehicle: bool = False
    inference_time_ms: Optional[float] = None
    center: Optional[Tuple[int, int]] = None

    class Config:
        arbitrary_types_allowed = True


class TrackedObject(BaseModel):
    track_id: int
    class_name: str
    positions: List[Tuple[int, int]] = []
    timestamps: List[float] = []
    velocities: List[float] = []
    accelerations: List[float] = []
    bbox_history: List[Tuple[int, int, int, int]] = []
    confidence_history: List[float] = []
    last_seen: int = 0
    areas: List[int] = []

    class Config:
        arbitrary_types_allowed = True


class TrajectoryAnalysis(BaseModel):
    track_id: int
    avg_speed: float = 0.0
    max_speed: float = 0.0
    current_speed: float = 0.0
    max_acceleration: float = 0.0
    sudden_stop: bool = False
    sudden_acceleration: bool = False
    abnormal_direction_change: bool = False
    max_direction_change: float = 0.0
    trajectory_smoothness: float = 1.0
    speed_anomaly: bool = False
    anomaly_score: float = 0.0
    potential_collision: bool = False
    collision_partner_id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True


class OpticalFlowResult(BaseModel):
    avg_magnitude: float = 0.0
    max_magnitude: float = 0.0
    direction_consistency: float = 1.0
    sudden_change: bool = False
    impact_detected: bool = False
    impact_location: Optional[Tuple[int, int]] = None
    chaotic_flow: bool = False
    anomaly_score: float = 0.0
    flow_field: Optional[Any] = None  # numpy array

    class Config:
        arbitrary_types_allowed = True


class AccidentPrediction(BaseModel):
    is_accident: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: float = Field(default=0.0, ge=0.0, le=100.0)  # 0-100 percentage
    severity_level: Optional[str] = None  # 'low', 'medium', 'high', 'critical'
    accident_type: Optional[str] = None
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    location: Optional[Tuple[int, int]] = None  # pixel coordinates
    involved_tracks: List[int] = []
    features: Optional[Dict[str, Any]] = None
    rule_scores: Optional[Dict[str, float]] = None

    class Config:
        arbitrary_types_allowed = True


class AccidentEvent(BaseModel):
    """Full accident event record for database storage"""
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    camera_id: Optional[str] = None
    video_path: Optional[str] = None
    clip_path: Optional[str] = None  # Saved video clip of accident
    thumbnail_path: Optional[str] = None
    severity: float = 0.0
    severity_level: str = "low"
    accident_type: Optional[str] = None
    description: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    involved_vehicles: int = 0
    confidence: float = 0.0
    alert_sent: bool = False
    alert_recipients: List[str] = []
    auto_alerted: bool = False  # If severity > 90%
    status: str = "detected"  # detected, verified, false_alarm, resolved

    class Config:
        arbitrary_types_allowed = True


class AlertPayload(BaseModel):
    """Alert payload for WebSocket notifications"""
    event_id: str
    type: str = "accident"
    severity: float = 0.0
    severity_level: str = "low"
    message: str = ""
    camera_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requires_action: bool = False
    auto_alerted: bool = False
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class ModelConfig(BaseModel):
    yolov11_path: Optional[str] = None
    yolov8_path: Optional[str] = None  # Legacy support
    temporal_model_path: Optional[str] = None
    device: str = 'cpu'
