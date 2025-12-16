"""
YOLOv8 Object Detector for Vehicle and Pedestrian Detection
"""
import os
import time
import numpy as np
from typing import List, Dict, Tuple, Optional
import cv2

# Try to import ultralytics and torch, provide fallback
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False
    print("⚠️ Warning: ultralytics not installed. Using dummy detector.")

# Optional: torch for device selection and tensor ops
try:
    import torch
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


from ..utils.logger import setup_logger
from .schemas import DetectionResult, TrackedObject

logger = setup_logger(__name__)

class YOLOv8Detector:
    """
    YOLOv8-based object detector for traffic surveillance
    """
    
    # COCO class names relevant for traffic surveillance
    COCO_CLASSES = {
        0: 'person',
        1: 'bicycle',
        2: 'car',
        3: 'motorcycle',
        5: 'bus',
        7: 'truck'
    }
    
    # Vehicle classes (for accident detection)
    VEHICLE_CLASSES = ['car', 'bus', 'truck', 'motorcycle', 'bicycle']
    PERSON_CLASS = 'person'
    
    def __init__(self, model_path: str = None, device: str = 'auto'):
        """
        Initialize YOLOv8 detector
        
        Args:
            model_path: Path to YOLOv8 model file (.pt) or model name like 'yolov8n.pt'
            device: 'cpu', 'cuda', or 'auto' (auto chooses CUDA if available)
        """
        self.model_path = model_path or os.getenv('YOLO_MODEL_PATH', 'yolov8n.pt')
        # Determine default device
        if device == 'auto':
            if TORCH_AVAILABLE and torch.cuda.is_available():
                self.device = 'cuda'
            else:
                self.device = 'cpu'
        else:
            self.device = device

        self.model = None
        self.class_names = []
        self.confidence_threshold = float(os.getenv('DETECTION_CONFIDENCE', 0.5))
        self.iou_threshold = float(os.getenv('IOU_THRESHOLD', 0.45))
        
        self.load_model()

    
    def load_model(self):
        """Load YOLOv8 model"""
        try:
            if not YOLO_AVAILABLE:
                logger.warning("ultralytics not available. Using dummy detector.")
                self.model = None
                self.class_names = list(self.COCO_CLASSES.values())
                return

            try:
                logger.info(f"Loading YOLOv8 model: {self.model_path} (device={self.device})")
                # YOLO() accepts a model name like 'yolov8n.pt' and will auto-download if needed
                self.model = YOLO(self.model_path)

                # Move model to device if supported
                try:
                    if TORCH_AVAILABLE and hasattr(self.model, 'model'):
                        # ultralytics exposes a .model which is a torch Module
                        self.model.model.to(self.device)
                except Exception:
                    # Not critical; continue
                    logger.debug("Could not move model to device, continuing")

                # Get class names
                if hasattr(self.model, 'names') and self.model.names:
                    self.class_names = self.model.names
                else:
                    self.class_names = list(self.COCO_CLASSES.values())

                logger.info(f"YOLOv8 model loaded successfully on {self.device}")
                logger.debug(f"Available classes: {self.class_names}")

                # Warm up the model with a dummy input to reduce first inference latency
                self._warmup()

            except FileNotFoundError:
                logger.error(f"Model file not found: {self.model_path}. Attempting to use 'yolov8n.pt' from ultralytics hub")
                try:
                    self.model = YOLO('yolov8n.pt')
                    if hasattr(self.model, 'names') and self.model.names:
                        self.class_names = self.model.names
                    self._warmup()
                except Exception as e:
                    logger.error(f"Fallback load failed: {e}")
                    self.model = None
                    self.class_names = list(self.COCO_CLASSES.values())

        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model: {e}")
            self.model = None
            self.class_names = list(self.COCO_CLASSES.values())
    
    def _download_model(self):
        """Download YOLOv8 model if not available"""
        try:
            if YOLO_AVAILABLE:
                from ultralytics import YOLO
                # Download YOLOv8 nano (smallest model)
                self.model = YOLO('yolov8n.pt')
                # Save to specified path
                import torch
                torch.save(self.model.model.state_dict(), self.model_path)
                logger.info(f"Model downloaded and saved to: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to download model: {e}")

    def _warmup(self):
        """Optionally run a quick inference to warm up the model (no-op on failures)."""
        try:
            if self.model is None:
                return
            import numpy as np
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            try:
                # Some ultralytics models accept a numpy array for a quick run
                _ = self.model(dummy)
            except Exception:
                # Swallow any exception during warmup – not critical
                pass
        except Exception:
            pass
    
    def detect(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Detect objects in a single frame
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of DetectionResult objects
        """
        if self.model is None:
            return self._dummy_detection(frame)
        
        try:
            start_time = time.time()
            
            # Run inference
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False
            )
            
            inference_time = (time.time() - start_time) * 1000  # ms
            
            detections = []
            
            for result in results:
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    for i, (box, conf, cls_id) in enumerate(zip(boxes, confidences, class_ids)):
                        # Get class name
                        if cls_id in self.COCO_CLASSES:
                            class_name = self.COCO_CLASSES[cls_id]
                        elif self.class_names and cls_id < len(self.class_names):
                            class_name = self.class_names[cls_id]
                        else:
                            class_name = f"class_{cls_id}"
                        
                        # Filter for relevant classes (vehicles and persons)
                        if class_name not in self.VEHICLE_CLASSES + [self.PERSON_CLASS]:
                            continue
                        
                        # Convert box coordinates to integers
                        x1, y1, x2, y2 = map(int, box)
                        
                        detection = DetectionResult(
                            bbox=(x1, y1, x2 - x1, y2 - y1),
                            confidence=float(conf),
                            class_name=class_name,
                            class_id=int(cls_id),
                            tracking_id=None,  # Will be assigned by tracker
                            is_vehicle=class_name in self.VEHICLE_CLASSES,
                            inference_time_ms=inference_time
                        )
                        
                        detections.append(detection)
            
            logger.debug(f"Detected {len(detections)} objects in {inference_time:.2f}ms")
            return detections
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return []
    
    def detect_batch(self, frames: List[np.ndarray]) -> List[List[DetectionResult]]:
        """
        Detect objects in multiple frames (batch processing)
        
        Args:
            frames: List of input frames
            
        Returns:
            List of detection results for each frame
        """
        if not frames:
            return []
        
        all_detections = []
        
        if self.model is None:
            # Process frames sequentially with dummy detector
            for frame in frames:
                all_detections.append(self._dummy_detection(frame))
            return all_detections
        
        try:
            start_time = time.time()
            
            # Batch inference
            results = self.model(
                frames,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False
            )
            
            batch_time = (time.time() - start_time) * 1000  # ms
            
            for result in results:
                frame_detections = []
                
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    for i, (box, conf, cls_id) in enumerate(zip(boxes, confidences, class_ids)):
                        # Get class name
                        if cls_id in self.COCO_CLASSES:
                            class_name = self.COCO_CLASSES[cls_id]
                        elif self.class_names and cls_id < len(self.class_names):
                            class_name = self.class_names[cls_id]
                        else:
                            class_name = f"class_{cls_id}"
                        
                        # Filter for relevant classes
                        if class_name not in self.VEHICLE_CLASSES + [self.PERSON_CLASS]:
                            continue
                        
                        # Convert box coordinates
                        x1, y1, x2, y2 = map(int, box)
                        
                        detection = DetectionResult(
                            bbox=(x1, y1, x2 - x1, y2 - y1),
                            confidence=float(conf),
                            class_name=class_name,
                            class_id=int(cls_id),
                            tracking_id=None,
                            is_vehicle=class_name in self.VEHICLE_CLASSES,
                            inference_time_ms=batch_time / len(frames)
                        )
                        
                        frame_detections.append(detection)
                
                all_detections.append(frame_detections)
            
            logger.debug(f"Batch detection: {len(frames)} frames in {batch_time:.2f}ms")
            return all_detections
            
        except Exception as e:
            logger.error(f"Batch detection failed: {e}")
            # Fallback to sequential detection
            all_detections = []
            for frame in frames:
                all_detections.append(self.detect(frame))
            return all_detections
    
    def _dummy_detection(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        Generate dummy detections for testing when model is not available
        
        Args:
            frame: Input frame
            
        Returns:
            List of dummy DetectionResult objects
        """
        height, width = frame.shape[:2]
        detections = []
        
        # Generate 2-5 random detections
        import random
        num_detections = random.randint(2, 5)
        
        for i in range(num_detections):
            # Random bounding box
            w = random.randint(50, 150)
            h = random.randint(50, 150)
            x = random.randint(0, width - w - 1)
            y = random.randint(0, height - h - 1)
            
            # Random class
            class_name = random.choice(self.VEHICLE_CLASSES + [self.PERSON_CLASS])
            
            # Random confidence
            confidence = random.uniform(0.6, 0.95)
            
            detection = DetectionResult(
                bbox=(x, y, w, h),
                confidence=confidence,
                class_name=class_name,
                class_id=self.VEHICLE_CLASSES.index(class_name) if class_name in self.VEHICLE_CLASSES else 0,
                tracking_id=i,
                is_vehicle=class_name in self.VEHICLE_CLASSES,
                inference_time_ms=10.0
            )
            
            detections.append(detection)
        
        return detections
    
    def visualize_detections(self, frame: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """
        Draw detection bounding boxes on frame
        
        Args:
            frame: Input frame
            detections: List of DetectionResult objects
            
        Returns:
            Frame with drawn bounding boxes
        """
        frame_copy = frame.copy()
        
        for detection in detections:
            x, y, w, h = detection.bbox
            
            # Color based on class
            if detection.class_name == 'person':
                color = (0, 255, 0)  # Green for person
            elif detection.is_vehicle:
                color = (0, 0, 255)  # Red for vehicles
            else:
                color = (255, 255, 0)  # Cyan for others
            
            # Draw bounding box
            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"{detection.class_name} {detection.confidence:.2f}"
            if detection.tracking_id is not None:
                label = f"ID:{detection.tracking_id} {label}"
            
            # Label background
            label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame_copy, (x, y - label_size[1] - 5), 
                         (x + label_size[0], y), color, -1)
            
            # Label text
            cv2.putText(frame_copy, label, (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame_copy
    
    def extract_roi(self, frame: np.ndarray, detection: DetectionResult) -> np.ndarray:
        """
        Extract region of interest from frame
        
        Args:
            frame: Input frame
            detection: DetectionResult object
            
        Returns:
            Extracted ROI
        """
        x, y, w, h = detection.bbox
        
        # Add padding
        padding = 10
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(frame.shape[1], x + w + padding)
        y2 = min(frame.shape[0], y + h + padding)
        
        return frame[y1:y2, x1:x2]
    
    def filter_by_class(self, detections: List[DetectionResult], class_names: List[str]) -> List[DetectionResult]:
        """
        Filter detections by class names
        
        Args:
            detections: List of DetectionResult objects
            class_names: List of class names to keep
            
        Returns:
            Filtered detections
        """
        return [d for d in detections if d.class_name in class_names]
    
    def filter_by_confidence(self, detections: List[DetectionResult], min_confidence: float) -> List[DetectionResult]:
        """
        Filter detections by confidence threshold
        
        Args:
            detections: List of DetectionResult objects
            min_confidence: Minimum confidence threshold
            
        Returns:
            Filtered detections
        """
        return [d for d in detections if d.confidence >= min_confidence]
    
    def get_detection_statistics(self, detections: List[DetectionResult]) -> Dict:
        """
        Get statistics about detections
        
        Args:
            detections: List of DetectionResult objects
            
        Returns:
            Dictionary of statistics
        """
        stats = {
            'total_detections': len(detections),
            'vehicle_count': sum(1 for d in detections if d.is_vehicle),
            'person_count': sum(1 for d in detections if d.class_name == 'person'),
            'avg_confidence': np.mean([d.confidence for d in detections]) if detections else 0,
            'class_distribution': {}
        }
        
        # Count by class
        for detection in detections:
            class_name = detection.class_name
            if class_name not in stats['class_distribution']:
                stats['class_distribution'][class_name] = 0
            stats['class_distribution'][class_name] += 1
        
        return stats
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded successfully"""
        return self.model is not None and YOLO_AVAILABLE


if __name__ == '__main__':
    # Quick smoke test when running this module directly
    import numpy as np
    import cv2

    logger.info("Running YOLOv8Detector smoke test...")
    det = YOLOv8Detector()
    logger.info(f"Model loaded: {det.is_model_loaded()}, device: {det.device}")

    # Create a blank image with a simple rectangle (simulate a vehicle)
    img = np.zeros((640, 480, 3), dtype=np.uint8)
    cv2.rectangle(img, (200, 200), (350, 300), (255, 255, 255), -1)

    try:
        results = det.detect(img)
        logger.info(f"Smoke test detections: {len(results)} objects")
        for r in results[:5]:
            logger.info(r.dict())
    except Exception as e:
        logger.error(f"Smoke test failed: {e}")
