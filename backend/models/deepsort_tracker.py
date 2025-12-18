"""
DeepSORT Multi-Object Tracker
Tracks vehicles across frames for trajectory analysis
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import time

from ..utils.logger import setup_logger
from .schemas import DetectionResult, TrackedObject

logger = setup_logger(__name__)

# Try to import deep_sort_realtime
try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
    DEEPSORT_AVAILABLE = True
except ImportError:
    DEEPSORT_AVAILABLE = False
    logger.warning("deep_sort_realtime not installed. Using simple tracker.")


class DeepSORTTracker:
    """
    DeepSORT-based multi-object tracker for vehicles
    Maintains track history for trajectory and speed analysis
    """
    
    def __init__(self, max_age: int = 30, n_init: int = 3, max_iou_distance: float = 0.7):
        """
        Initialize DeepSORT tracker
        
        Args:
            max_age: Maximum frames to keep alive a track without matching
            n_init: Number of consecutive detections before a track is confirmed
            max_iou_distance: Maximum IOU distance threshold
        """
        self.max_age = max_age
        self.n_init = n_init
        self.max_iou_distance = max_iou_distance
        
        # Initialize DeepSORT if available
        if DEEPSORT_AVAILABLE:
            self.tracker = DeepSort(
                max_age=max_age,
                n_init=n_init,
                max_iou_distance=max_iou_distance,
                max_cosine_distance=0.2,
                nn_budget=100,
                embedder="mobilenet",
                half=True,
                bgr=True
            )
        else:
            self.tracker = None
        
        # Track history storage
        self.track_history: Dict[int, TrackedObject] = {}
        self.frame_count = 0
        
        # Next track ID for simple tracker
        self._next_id = 0

    def update(self, detections: List[DetectionResult], frame: np.ndarray) -> List[DetectionResult]:
        """
        Update tracker with new detections
        
        Args:
            detections: List of DetectionResult from detector
            frame: Current frame for feature extraction
            
        Returns:
            List of DetectionResult with tracking IDs assigned
        """
        self.frame_count += 1
        
        if not detections:
            return []
        
        if DEEPSORT_AVAILABLE and self.tracker:
            return self._update_deepsort(detections, frame)
        else:
            return self._update_simple(detections, frame)

    def _update_deepsort(self, detections: List[DetectionResult], frame: np.ndarray) -> List[DetectionResult]:
        """Update using DeepSORT tracker"""
        try:
            # Prepare detections for DeepSORT
            # Format: [[x1, y1, x2, y2, confidence, class_id], ...]
            bbs = []
            for det in detections:
                x, y, w, h = det.bbox
                bbs.append(([x, y, w, h], det.confidence, det.class_name))
            
            # Update tracker
            tracks = self.tracker.update_tracks(bbs, frame=frame)
            
            # Match tracks to detections
            tracked_detections = []
            
            for track in tracks:
                if not track.is_confirmed():
                    continue
                
                track_id = track.track_id
                ltrb = track.to_ltrb()
                x1, y1, x2, y2 = map(int, ltrb)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                
                # Find matching detection
                best_det = None
                best_iou = 0
                for det in detections:
                    iou = self._calculate_iou(det.bbox, (x1, y1, x2 - x1, y2 - y1))
                    if iou > best_iou:
                        best_iou = iou
                        best_det = det
                
                if best_det:
                    best_det.tracking_id = track_id
                    best_det.center = (cx, cy)
                    tracked_detections.append(best_det)
                    
                    # Update track history
                    self._update_track_history(track_id, best_det, (cx, cy))
            
            return tracked_detections
            
        except Exception as e:
            logger.error(f"DeepSORT update failed: {e}")
            return self._update_simple(detections, frame)

    def _update_simple(self, detections: List[DetectionResult], frame: np.ndarray) -> List[DetectionResult]:
        """Simple IOU-based tracking fallback"""
        tracked_detections = []
        
        for det in detections:
            x, y, w, h = det.bbox
            cx, cy = x + w // 2, y + h // 2
            
            # Find closest existing track
            best_track_id = None
            best_dist = float('inf')
            
            for track_id, track_obj in self.track_history.items():
                if self.frame_count - track_obj.last_seen > self.max_age:
                    continue
                
                last_pos = track_obj.positions[-1] if track_obj.positions else (0, 0)
                dist = np.sqrt((cx - last_pos[0])**2 + (cy - last_pos[1])**2)
                
                if dist < 100 and dist < best_dist:  # 100 pixel threshold
                    best_dist = dist
                    best_track_id = track_id
            
            # Assign track ID
            if best_track_id is None:
                best_track_id = self._next_id
                self._next_id += 1
            
            det.tracking_id = best_track_id
            det.center = (cx, cy)
            tracked_detections.append(det)
            
            # Update track history
            self._update_track_history(best_track_id, det, (cx, cy))
        
        return tracked_detections

    def _update_track_history(self, track_id: int, detection: DetectionResult, center: Tuple[int, int]):
        """Update track history for trajectory analysis"""
        current_time = time.time()
        
        if track_id not in self.track_history:
            self.track_history[track_id] = TrackedObject(
                track_id=track_id,
                class_name=detection.class_name,
                positions=[center],
                timestamps=[current_time],
                velocities=[],
                accelerations=[],
                bbox_history=[detection.bbox],
                confidence_history=[detection.confidence],
                last_seen=self.frame_count
            )
        else:
            track = self.track_history[track_id]
            track.positions.append(center)
            track.timestamps.append(current_time)
            track.bbox_history.append(detection.bbox)
            track.confidence_history.append(detection.confidence)
            track.last_seen = self.frame_count
            
            # Calculate velocity if we have enough positions
            if len(track.positions) >= 2:
                dt = track.timestamps[-1] - track.timestamps[-2]
                if dt > 0:
                    dx = track.positions[-1][0] - track.positions[-2][0]
                    dy = track.positions[-1][1] - track.positions[-2][1]
                    velocity = np.sqrt(dx**2 + dy**2) / dt
                    track.velocities.append(velocity)
                    
                    # Calculate acceleration
                    if len(track.velocities) >= 2:
                        dv = track.velocities[-1] - track.velocities[-2]
                        acceleration = dv / dt
                        track.accelerations.append(acceleration)
            
            # Keep only last 60 frames of history
            max_history = 60
            if len(track.positions) > max_history:
                track.positions = track.positions[-max_history:]
                track.timestamps = track.timestamps[-max_history:]
                track.bbox_history = track.bbox_history[-max_history:]
                track.confidence_history = track.confidence_history[-max_history:]
                track.velocities = track.velocities[-max_history:]
                track.accelerations = track.accelerations[-max_history:]

    def _calculate_iou(self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
        """Calculate Intersection over Union"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Convert to x1, y1, x2, y2 format
        box1 = [x1, y1, x1 + w1, y1 + h1]
        box2 = [x2, y2, x2 + w2, y2 + h2]
        
        # Calculate intersection
        xi1 = max(box1[0], box2[0])
        yi1 = max(box1[1], box2[1])
        xi2 = min(box1[2], box2[2])
        yi2 = min(box1[3], box2[3])
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        # Calculate union
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area
        
        if union_area == 0:
            return 0
        
        return inter_area / union_area

    def get_track(self, track_id: int) -> Optional[TrackedObject]:
        """Get track history by ID"""
        return self.track_history.get(track_id)

    def get_all_tracks(self) -> Dict[int, TrackedObject]:
        """Get all track histories"""
        return self.track_history

    def get_active_tracks(self) -> List[TrackedObject]:
        """Get tracks that are still active (seen recently)"""
        active = []
        for track_id, track in self.track_history.items():
            if self.frame_count - track.last_seen <= self.max_age:
                active.append(track)
        return active

    def clear_old_tracks(self):
        """Remove tracks that haven't been seen for a while"""
        to_remove = []
        for track_id, track in self.track_history.items():
            if self.frame_count - track.last_seen > self.max_age * 2:
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.track_history[track_id]

    def reset(self):
        """Reset tracker state"""
        if DEEPSORT_AVAILABLE and self.tracker:
            self.tracker = DeepSort(
                max_age=self.max_age,
                n_init=self.n_init,
                max_iou_distance=self.max_iou_distance
            )
        self.track_history.clear()
        self.frame_count = 0
        self._next_id = 0

