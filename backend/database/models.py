"""
Database Models and Schemas
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class AlertStatus(str, Enum):
    """Alert status enumeration"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"

class AlertType(str, Enum):
    """Alert type enumeration"""
    VOICE = "voice"
    TTS = "tts"
    SMS = "sms"
    TEST = "test"

class DetectionSeverity(str, Enum):
    """Detection severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ========== BASE MODELS ==========

class Location(BaseModel):
    """Geographic location model"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    address: Optional[str] = Field(None, description="Human-readable address")
    accuracy: Optional[float] = Field(None, ge=0, description="Location accuracy in meters")
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

class BoundingBox(BaseModel):
    """Bounding box coordinates"""
    x: int = Field(..., ge=0, description="X coordinate of top-left corner")
    y: int = Field(..., ge=0, description="Y coordinate of top-left corner")
    width: int = Field(..., ge=0, description="Width of bounding box")
    height: int = Field(..., ge=0, description="Height of bounding box")
    
    @property
    def area(self) -> int:
        """Calculate area of bounding box"""
        return self.width * self.height
    
    @property
    def center(self) -> tuple:
        """Calculate center point of bounding box"""
        return (self.x + self.width // 2, self.y + self.height // 2)

class VehicleInfo(BaseModel):
    """Vehicle information in detection"""
    type: str = Field(..., description="Type of vehicle (car, truck, bus, etc.)")
    track_id: Optional[int] = Field(None, description="Tracking ID for the vehicle")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    bbox: BoundingBox
    velocity: Optional[float] = Field(None, ge=0, description="Velocity in pixels/second")
    trajectory: Optional[List[tuple]] = Field(None, description="Recent trajectory points")

# ========== DATABASE DOCUMENT MODELS ==========

class CameraDocument(BaseModel):
    """Camera document model for MongoDB"""
    camera_id: str = Field(..., description="Unique camera identifier")
    name: str = Field(..., description="Camera name/label")
    stream_url: str = Field(..., description="RTSP/HTTP stream URL")
    
    location: Optional[Location] = Field(None, description="Camera location")
    direction: Optional[float] = Field(None, ge=0, lt=360, description="Camera direction in degrees")
    
    status: str = Field("active", description="Camera status (active, inactive, maintenance)")
    resolution: Optional[str] = Field(None, description="Camera resolution (e.g., 1920x1080)")
    fps: Optional[int] = Field(None, ge=1, le=60, description="Frames per second")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "camera_id": "cam_001",
                "name": "Highway Entrance Camera",
                "stream_url": "rtsp://admin:password@192.168.1.100:554/stream1",
                "location": {
                    "latitude": 28.6139,
                    "longitude": 77.2090,
                    "address": "New Delhi, India"
                },
                "status": "active",
                "resolution": "1920x1080",
                "fps": 25
            }
        }

class DetectionDocument(BaseModel):
    """Detection document model for MongoDB"""
    detection_id: str = Field(..., description="Unique detection identifier")
    camera_id: str = Field(..., description="Camera that captured the detection")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Detection information
    confidence: float = Field(..., ge=0, le=1, description="Overall detection confidence")
    is_accident: bool = Field(..., description="Whether this is an accident detection")
    severity: DetectionSeverity = Field(DetectionSeverity.MEDIUM, description="Severity level")
    
    # Location
    location: Optional[Location] = Field(None, description="Accident location")
    
    # Objects involved
    vehicles_involved: List[VehicleInfo] = Field(default_factory=list, description="Vehicles involved")
    pedestrians_involved: Optional[int] = Field(0, ge=0, description="Number of pedestrians involved")
    
    # Bounding box
    bbox: Optional[BoundingBox] = Field(None, description="Accident bounding box")
    
    # Video information
    video_path: Optional[str] = Field(None, description="Path to video file")
    frame_number: Optional[int] = Field(None, ge=0, description="Frame number in video")
    stream_url: Optional[str] = Field(None, description="Stream URL if live")
    
    # Processing information
    processing_time_ms: Optional[float] = Field(None, ge=0, description="Processing time in milliseconds")
    model_version: Optional[str] = Field(None, description="AI model version used")
    
    # Status flags
    verified: bool = Field(False, description="Whether detection has been verified")
    archived: bool = Field(False, description="Whether detection is archived")
    alert_sent: bool = Field(False, description="Whether alert was sent")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "detection_id": "det_001",
                "camera_id": "cam_001",
                "timestamp": "2024-01-15T14:30:00Z",
                "confidence": 0.85,
                "is_accident": True,
                "severity": "high",
                "location": {
                    "latitude": 28.6140,
                    "longitude": 77.2091,
                    "address": "Near Connaught Place, New Delhi"
                },
                "vehicles_involved": [
                    {
                        "type": "car",
                        "confidence": 0.9,
                        "bbox": {"x": 100, "y": 150, "width": 80, "height": 60}
                    }
                ]
            }
        }

class AlertDocument(BaseModel):
    """Alert document model for MongoDB"""
    alert_id: str = Field(..., description="Unique alert identifier")
    type: AlertType = Field(..., description="Type of alert")
    status: AlertStatus = Field(AlertStatus.PENDING, description="Alert status")
    
    # Related detection
    detection_id: Optional[str] = Field(None, description="Related detection ID")
    camera_id: Optional[str] = Field(None, description="Related camera ID")
    
    # Alert content
    message: str = Field(..., description="Alert message content")
    tts_audio_path: Optional[str] = Field(None, description="Path to TTS audio file")
    
    # Recipients
    recipients: Dict[str, List[str]] = Field(default_factory=dict, description="Recipient information (phone_numbers only)")
    
    # Delivery information
    delivery_attempts: int = Field(0, ge=0, description="Number of delivery attempts")
    last_attempt: Optional[datetime] = Field(None, description="Last delivery attempt time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # External service IDs
    twilio_call_sid: Optional[str] = Field(None, description="Twilio Call SID for voice calls")
    twilio_message_sid: Optional[str] = Field(None, description="Twilio Message SID for SMS")
    
    timestamp: datetime = Field(default_factory=datetime.now)
    sent_at: Optional[datetime] = Field(None, description="When alert was successfully sent")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "alert_id": "alert_001",
                "type": "voice",
                "status": "sent",
                "detection_id": "det_001",
                "camera_id": "cam_001",
                "message": "Accident detected at latitude 28.6140, longitude 77.2091",
                "recipients": {
                    "phone_numbers": ["+919876543210"]
                },
                "delivery_attempts": 1,
                "twilio_call_sid": "CA1234567890abcdef"
            }
        }

class SystemLogDocument(BaseModel):
    """System log document model for MongoDB"""
    timestamp: datetime = Field(default_factory=datetime.now)
    level: str = Field("INFO", description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    component: str = Field(..., description="Component that generated the log")
    message: str = Field(..., description="Log message")
    
    # Context information
    camera_id: Optional[str] = Field(None, description="Related camera ID")
    detection_id: Optional[str] = Field(None, description="Related detection ID")
    alert_id: Optional[str] = Field(None, description="Related alert ID")
    
    # Additional data
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional log data")
    
    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2024-01-15T14:30:00Z",
                "level": "INFO",
                "component": "inference_service",
                "message": "Accident detected with confidence 0.85",
                "camera_id": "cam_001",
                "detection_id": "det_001"
            }
        }

# ========== RESPONSE MODELS ==========

class DetectionResponse(BaseModel):
    """API response model for detections"""
    detection_id: str
    camera_id: str
    timestamp: datetime
    confidence: float
    is_accident: bool
    severity: DetectionSeverity
    location: Optional[Location]
    vehicles_involved: List[VehicleInfo]
    bbox: Optional[BoundingBox]
    
    @classmethod
    def from_document(cls, doc: Dict) -> 'DetectionResponse':
        """Create response from database document"""
        return cls(**doc)

class CameraResponse(BaseModel):
    """API response model for cameras"""
    camera_id: str
    name: str
    stream_url: str
    location: Optional[Location]
    status: str
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_document(cls, doc: Dict) -> 'CameraResponse':
        """Create response from database document"""
        return cls(**doc)

class AlertResponse(BaseModel):
    """API response model for alerts"""
    alert_id: str
    type: AlertType
    status: AlertStatus
    detection_id: Optional[str]
    camera_id: Optional[str]
    message: str
    timestamp: datetime
    sent_at: Optional[datetime]
    
    @classmethod
    def from_document(cls, doc: Dict) -> 'AlertResponse':
        """Create response from database document"""
        return cls(**doc)

# ========== DATABASE MODELS CLASS ==========

class DatabaseModels:
    """Database models manager"""
    
    @staticmethod
    def validate_camera(data: Dict) -> CameraDocument:
        """Validate camera data against schema"""
        return CameraDocument(**data)
    
    @staticmethod
    def validate_detection(data: Dict) -> DetectionDocument:
        """Validate detection data against schema"""
        return DetectionDocument(**data)
    
    @staticmethod
    def validate_alert(data: Dict) -> AlertDocument:
        """Validate alert data against schema"""
        return AlertDocument(**data)
    
    @staticmethod
    def validate_log(data: Dict) -> SystemLogDocument:
        """Validate log data against schema"""
        return SystemLogDocument(**data)
    
    @staticmethod
    def prepare_for_insert(document: BaseModel) -> Dict:
        """
        Prepare document for MongoDB insertion
        Converts Pydantic model to dict and handles ObjectId
        """
        data = document.dict(exclude_none=True)
        
        # Convert datetime to ISO string for MongoDB
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value
        
        return data
    
    @staticmethod
    def prepare_for_response(document_dict: Dict) -> Dict:
        """
        Prepare document for API response
        Converts MongoDB document to API-friendly format
        """
        response = document_dict.copy()
        
        # Convert ObjectId to string
        if '_id' in response:
            response['id'] = str(response['_id'])
            del response['_id']
        
        # Convert datetime to ISO string
        for key, value in response.items():
            if isinstance(value, datetime):
                response[key] = value.isoformat()
        
        return response