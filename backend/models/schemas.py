("""
Schema definitions for detections, tracked objects and accident predictions.
Uses Pydantic for validation and easy serialization.
""")
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DetectionResult(BaseModel):
	bbox: Tuple[int, int, int, int] = Field(..., description="x,y,w,h")
	confidence: float = Field(..., ge=0.0, le=1.0)
	class_name: str
	class_id: int
	tracking_id: Optional[int] = None
	is_vehicle: bool = False
	inference_time_ms: Optional[float] = None


class TrackedObject(BaseModel):
	track_id: int
	class_name: str
	positions: List[Tuple[int, int]] = []
	areas: List[int] = []
	last_seen: int = 0


class AccidentPrediction(BaseModel):
	is_accident: bool
	confidence: float = Field(..., ge=0.0, le=1.0)
	accident_type: Optional[str] = None
	severity: Optional[str] = None
	description: Optional[str] = None
	timestamp: datetime = Field(default_factory=datetime.utcnow)
	features: Optional[Dict[str, Any]] = None
	rule_scores: Optional[Dict[str, float]] = None


class ModelConfig(BaseModel):
	yolov8_path: Optional[str] = None
	temporal_model_path: Optional[str] = None
	device: str = 'cpu'

