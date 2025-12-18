"""
YOLOv11 Object Detector - Vehicle Detection Only
Optimized for accident detection in CCTV footage
"""
import os
import time
import numpy as np
from typing import List, Dict, Tuple, Optional
import cv2

# Try to import ultralytics and torch
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not installed. Using dummy detector.")

try:
    import torch
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

from ..utils.logger import setup_logger
from .schemas import DetectionResult

logger = setup_logger(__name__)


class YOLOv11Detector:
    """
    YOLOv11-based vehicle detector for traffic surveillance
    Only detects vehicles (car, bus, truck, motorcycle, bicycle)
    """
    
    # COCO class IDs for vehicles only
    VEHICLE_CLASS_IDS = {
        2: 'car',
        3: 'motorcycle',
        5: 'bus',
        7: 'truck',
        1: 'bicycle'
    }
    
    def __init__(self, model_path: str = None, device: str = 'auto', conf_threshold: float = 0.5):
        """
        Initialize YOLOv11 detector
        
        Args:
            model_path: Path to YOLOv11 model file (.pt)
            device: 'cpu', 'cuda', or 'auto'
            conf_threshold: Confidence threshold for detections
        """
        self.model_path = model_path or os.getenv('YOLO_MODEL_PATH', 'yolo11n.pt')
        
        # Determine device
        if device == 'auto':
            if TORCH_AVAILABLE and torch.cuda.is_available():
                self.device = 'cuda'
            else:
                self.device = 'cpu'
        else:
            self.device = device

        self.model = None
        self.confidence_threshold = conf_threshold
        self.iou_threshold = float(os.getenv('IOU_THRESHOLD', 0.45))
        
        self.load_model()

    def load_model(self):
        """Load YOLOv11 model"""
        try:
            if not YOLO_AVAILABLE:
                logger.warning("ultralytics not available. Using dummy detector.")
                self.model = None
                return

            logger.info(f"Loading YOLOv11 model: {self.model_path} (device={self.device})")
            
            # Try to load YOLO11 model
            try:
                self.model = YOLO(self.model_path)
            except Exception:
                # Fallback to yolo11n if specified model not found
                logger.warning(f"Model {self.model_path} not found, downloading yolo11n.pt")
                self.model = YOLO('yolo11n.pt')
            
            # Move to device
            if TORCH_AVAILABLE and hasattr(self.model, 'model'):
                try:
                    self.model.model.to(self.device)
                except Exception:
                    pass

            logger.info(f"YOLOv11 model loaded successfully on {self.device}")
            self._warmup()

        except Exception as e:
            logger.error(f"Failed to load YOLOv11 model: {e}")
            self.model = None

    def _warmup(self):
        """Warm up model with dummy inference"""
        try:
            if self.model is None:
                return
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(dummy, verbose=False)
        except Exception:
            pass

    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Detect vehicles in a single frame
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of DetectionResult objects (vehicles only)
        """
        if self.model is None:
            return self._dummy_detection(frame)
        
        try:
            start_time = time.time()
            
            # Run inference with vehicle class filter
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                classes=list(self.VEHICLE_CLASS_IDS.keys()),  # Only vehicle classes
                verbose=False
            )
            
            inference_time = (time.time() - start_time) * 1000
            
            detections = []
            
            for result in results:
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    for box, conf, cls_id in zip(boxes, confidences, class_ids):
                        if cls_id not in self.VEHICLE_CLASS_IDS:
                            continue
                        
                        class_name = self.VEHICLE_CLASS_IDS[cls_id]
                        x1, y1, x2, y2 = map(int, box)
                        
                        # Calculate center point for tracking
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2
                        
                        detection = DetectionResult(
                            bbox=(x1, y1, x2 - x1, y2 - y1),
                            confidence=float(conf),
                            class_name=class_name,
                            class_id=int(cls_id),
                            tracking_id=None,
                            is_vehicle=True,
                            inference_time_ms=inference_time,
                            center=(cx, cy)
                        )
                        
                        detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []

    def _dummy_detection(self, frame: np.ndarray) -> List[DetectionResult]:
        """Generate dummy detections for testing"""
        import random
        height, width = frame.shape[:2]
        detections = []
        
        for i in range(random.randint(1, 4)):
            w = random.randint(80, 200)
            h = random.randint(60, 150)
            x = random.randint(0, max(1, width - w - 1))
            y = random.randint(0, max(1, height - h - 1))
            
            class_name = random.choice(list(self.VEHICLE_CLASS_IDS.values()))
            
            detection = DetectionResult(
                bbox=(x, y, w, h),
                confidence=random.uniform(0.6, 0.95),
                class_name=class_name,
                class_id=list(self.VEHICLE_CLASS_IDS.keys())[list(self.VEHICLE_CLASS_IDS.values()).index(class_name)],
                tracking_id=i,
                is_vehicle=True,
                inference_time_ms=10.0,
                center=(x + w // 2, y + h // 2)
            )
            detections.append(detection)
        
        return detections

    def is_model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None and YOLO_AVAILABLE

