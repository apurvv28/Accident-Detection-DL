"""
Accident Decision Logic
Combines all detection modules to make final accident determination
"""
import os
import cv2
import uuid
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import deque
import threading
import time

from ..utils.logger import setup_logger
from .schemas import (
    DetectionResult, TrackedObject, TrajectoryAnalysis,
    OpticalFlowResult, AccidentPrediction, AccidentEvent
)
from .yolov11_detector import YOLOv11Detector
from .deepsort_tracker import DeepSORTTracker
from .trajectory_analyzer import TrajectoryAnalyzer
from .optical_flow import OpticalFlowValidator

logger = setup_logger(__name__)


class AccidentDetector:
    """
    Main accident detection pipeline:
    CCTV Video → YOLOv11 → DeepSORT → Trajectory Analysis → Optical Flow → Decision
    """
    
    # Severity thresholds
    SEVERITY_THRESHOLDS = {
        'critical': 90,
        'high': 70,
        'medium': 50,
        'low': 30
    }
    
    def __init__(
        self,
        model_path: str = None,
        device: str = 'auto',
        fps: float = 30.0,
        save_clips: bool = True,
        clips_dir: str = None,
        auto_alert_threshold: float = 90.0
    ):
        """
        Initialize accident detector
        
        Args:
            model_path: Path to YOLOv11 model
            device: 'cpu', 'cuda', or 'auto'
            fps: Video frame rate
            save_clips: Whether to save accident video clips
            clips_dir: Directory to save clips
            auto_alert_threshold: Severity threshold for automatic alerts
        """
        self.fps = fps
        self.save_clips = save_clips
        self.clips_dir = clips_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'accidents'
        )
        self.auto_alert_threshold = auto_alert_threshold
        
        # Create clips directory
        os.makedirs(self.clips_dir, exist_ok=True)
        
        # Initialize detection modules
        logger.info("Initializing YOLOv11 detector...")
        self.detector = YOLOv11Detector(model_path=model_path, device=device)
        
        logger.info("Initializing DeepSORT tracker...")
        self.tracker = DeepSORTTracker()
        
        logger.info("Initializing trajectory analyzer...")
        self.trajectory_analyzer = TrajectoryAnalyzer(fps=fps)
        
        logger.info("Initializing optical flow validator...")
        self.optical_flow = OpticalFlowValidator()
        
        # Frame buffer for clip saving
        self.frame_buffer = deque(maxlen=int(fps * 10))  # 10 seconds buffer
        self.frame_count = 0
        
        # Accident tracking
        self.active_accidents: Dict[str, AccidentEvent] = {}
        self.accident_cooldown = {}  # Prevent duplicate detections
        self.cooldown_frames = int(fps * 5)  # 5 second cooldown
        
        # Callbacks
        self.on_accident_detected = None
        self.on_alert_sent = None
        
        logger.info("Accident detector initialized successfully")

    def process_frame(self, frame: np.ndarray, camera_id: str = None) -> Dict:
        """
        Process a single frame through the detection pipeline
        
        Args:
            frame: Input frame (BGR)
            camera_id: Camera identifier
            
        Returns:
            Dictionary with detection results
        """
        self.frame_count += 1
        
        # Store frame in buffer
        if self.save_clips:
            self.frame_buffer.append(frame.copy())
        
        # Step 1: YOLOv11 Vehicle Detection
        detections = self.detector.detect(frame)
        
        # Step 2: DeepSORT Tracking
        tracked_detections = self.tracker.update(detections, frame)
        
        # Step 3: Trajectory Analysis
        tracks = self.tracker.get_all_tracks()
        trajectory_analyses = self.trajectory_analyzer.analyze_tracks(tracks)
        
        # Step 4: Optical Flow Validation
        flow_result = self.optical_flow.compute_flow(frame)
        
        # Step 5: Accident Decision Logic
        accident_prediction = self._make_decision(
            tracked_detections, trajectory_analyses, flow_result
        )
        
        # Handle accident detection
        if accident_prediction.is_accident:
            self._handle_accident(
                accident_prediction, frame, camera_id, tracked_detections
            )
        
        return {
            'frame_number': self.frame_count,
            'detections': [d.dict() for d in tracked_detections],
            'trajectory_analyses': {k: v.dict() for k, v in trajectory_analyses.items()},
            'optical_flow': flow_result.dict() if flow_result else None,
            'accident_prediction': accident_prediction.dict(),
            'active_accidents': len(self.active_accidents)
        }

    def _make_decision(
        self,
        detections: List[DetectionResult],
        trajectories: Dict[int, TrajectoryAnalysis],
        flow: Optional[OpticalFlowResult]
    ) -> AccidentPrediction:
        """
        Make accident decision based on all inputs
        
        Decision factors:
        1. Trajectory anomalies (sudden stops, collisions)
        2. Optical flow anomalies (impacts, chaotic motion)
        3. Multiple vehicle involvement
        4. Combined evidence weighting
        """
        scores = {
            'trajectory_score': 0.0,
            'collision_score': 0.0,
            'flow_score': 0.0,
            'multi_vehicle_score': 0.0
        }
        
        involved_tracks = []
        accident_type = None
        description_parts = []
        location = None
        
        # Factor 1: Trajectory Analysis
        max_trajectory_score = 0
        for track_id, analysis in trajectories.items():
            if analysis.anomaly_score > max_trajectory_score:
                max_trajectory_score = analysis.anomaly_score
            
            if analysis.anomaly_score > 30:
                involved_tracks.append(track_id)
                
                if analysis.sudden_stop:
                    description_parts.append(f"Vehicle {track_id}: sudden stop detected")
                    accident_type = accident_type or "sudden_stop"
                    
                if analysis.potential_collision:
                    description_parts.append(
                        f"Vehicle {track_id}: collision with vehicle {analysis.collision_partner_id}"
                    )
                    accident_type = "collision"
                    scores['collision_score'] = max(scores['collision_score'], 50)
        
        scores['trajectory_score'] = max_trajectory_score
        
        # Factor 2: Optical Flow
        if flow:
            scores['flow_score'] = flow.anomaly_score
            
            if flow.impact_detected:
                description_parts.append("High-impact event detected via optical flow")
                location = flow.impact_location
                accident_type = accident_type or "impact"
                
            if flow.chaotic_flow:
                description_parts.append("Chaotic motion pattern detected")
        
        # Factor 3: Multi-vehicle involvement
        if len(involved_tracks) >= 2:
            scores['multi_vehicle_score'] = 30
            accident_type = "multi_vehicle_collision"
        
        # Calculate final severity score
        # Weighted combination
        severity = (
            scores['trajectory_score'] * 0.35 +
            scores['collision_score'] * 0.30 +
            scores['flow_score'] * 0.25 +
            scores['multi_vehicle_score'] * 0.10
        )
        
        # Determine if accident occurred
        is_accident = severity >= self.SEVERITY_THRESHOLDS['low']
        
        # Determine severity level
        severity_level = "low"
        for level, threshold in self.SEVERITY_THRESHOLDS.items():
            if severity >= threshold:
                severity_level = level
        
        # Calculate confidence
        confidence = min(1.0, severity / 100)
        
        # Build description
        if description_parts:
            description = "; ".join(description_parts)
        else:
            description = "No anomalies detected" if not is_accident else "Potential accident detected"
        
        return AccidentPrediction(
            is_accident=is_accident,
            confidence=confidence,
            severity=severity,
            severity_level=severity_level,
            accident_type=accident_type,
            description=description,
            location=location,
            involved_tracks=involved_tracks,
            features={
                'num_vehicles': len(detections),
                'num_tracks': len(trajectories),
            },
            rule_scores=scores
        )

    def _handle_accident(
        self,
        prediction: AccidentPrediction,
        frame: np.ndarray,
        camera_id: str,
        detections: List[DetectionResult]
    ):
        """Handle detected accident"""
        
        # Check cooldown to prevent duplicate detections
        cooldown_key = f"{camera_id}_{','.join(map(str, prediction.involved_tracks))}"
        if cooldown_key in self.accident_cooldown:
            if self.frame_count - self.accident_cooldown[cooldown_key] < self.cooldown_frames:
                return
        
        self.accident_cooldown[cooldown_key] = self.frame_count
        
        # Generate event ID
        event_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow()
        
        # Save video clip
        clip_path = None
        thumbnail_path = None
        
        if self.save_clips and len(self.frame_buffer) > 0:
            clip_path, thumbnail_path = self._save_accident_clip(
                event_id, frame, timestamp
            )
        
        # Create accident event
        event = AccidentEvent(
            event_id=event_id,
            timestamp=timestamp,
            camera_id=camera_id,
            clip_path=clip_path,
            thumbnail_path=thumbnail_path,
            severity=prediction.severity,
            severity_level=prediction.severity_level,
            accident_type=prediction.accident_type,
            description=prediction.description,
            location={'pixel': prediction.location} if prediction.location else None,
            involved_vehicles=len(prediction.involved_tracks),
            confidence=prediction.confidence,
            auto_alerted=prediction.severity >= self.auto_alert_threshold
        )
        
        # Store active accident
        self.active_accidents[event_id] = event
        
        logger.warning(
            f"ACCIDENT DETECTED: {event_id} | "
            f"Severity: {prediction.severity:.1f}% ({prediction.severity_level}) | "
            f"Type: {prediction.accident_type} | "
            f"Camera: {camera_id}"
        )
        
        # Trigger callback
        if self.on_accident_detected:
            self.on_accident_detected(event)
        
        # Auto-alert if severity > threshold
        if event.auto_alerted and self.on_alert_sent:
            self.on_alert_sent(event, auto=True)

    def _save_accident_clip(
        self,
        event_id: str,
        current_frame: np.ndarray,
        timestamp: datetime
    ) -> Tuple[Optional[str], Optional[str]]:
        """Save accident video clip and thumbnail"""
        try:
            # Create filename
            date_str = timestamp.strftime("%Y%m%d_%H%M%S")
            clip_filename = f"accident_{event_id}_{date_str}.mp4"
            thumb_filename = f"thumb_{event_id}_{date_str}.jpg"
            
            clip_path = os.path.join(self.clips_dir, clip_filename)
            thumb_path = os.path.join(self.clips_dir, thumb_filename)
            
            # Save thumbnail
            cv2.imwrite(thumb_path, current_frame)
            
            # Save video clip from buffer
            if len(self.frame_buffer) > 0:
                frames = list(self.frame_buffer)
                height, width = frames[0].shape[:2]
                
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(clip_path, fourcc, self.fps, (width, height))
                
                for f in frames:
                    writer.write(f)
                
                writer.release()
                
                logger.info(f"Saved accident clip: {clip_path} ({len(frames)} frames)")
            
            return clip_path, thumb_path
            
        except Exception as e:
            logger.error(f"Failed to save accident clip: {e}")
            return None, None

    def get_active_accidents(self) -> List[AccidentEvent]:
        """Get all active accident events"""
        return list(self.active_accidents.values())

    def get_accident(self, event_id: str) -> Optional[AccidentEvent]:
        """Get specific accident by ID"""
        return self.active_accidents.get(event_id)

    def update_accident_status(self, event_id: str, status: str) -> bool:
        """Update accident status"""
        if event_id in self.active_accidents:
            self.active_accidents[event_id].status = status
            return True
        return False

    def mark_alert_sent(self, event_id: str, recipients: List[str]):
        """Mark that alerts were sent for an accident"""
        if event_id in self.active_accidents:
            self.active_accidents[event_id].alert_sent = True
            self.active_accidents[event_id].alert_recipients = recipients

    def reset(self):
        """Reset detector state"""
        self.tracker.reset()
        self.optical_flow.reset()
        self.frame_buffer.clear()
        self.frame_count = 0
        self.accident_cooldown.clear()

    def visualize_frame(self, frame: np.ndarray, result: Dict) -> np.ndarray:
        """
        Visualize detection results on frame
        
        Args:
            frame: Input frame
            result: Result from process_frame
            
        Returns:
            Annotated frame
        """
        vis = frame.copy()
        
        # Draw detections
        for det in result['detections']:
            x, y, w, h = det['bbox']
            track_id = det.get('tracking_id', '?')
            class_name = det['class_name']
            conf = det['confidence']
            
            # Color based on class
            colors = {
                'car': (0, 255, 0),
                'truck': (255, 165, 0),
                'bus': (255, 0, 255),
                'motorcycle': (0, 255, 255),
                'bicycle': (255, 255, 0)
            }
            color = colors.get(class_name, (0, 255, 0))
            
            # Draw box
            cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"ID:{track_id} {class_name} {conf:.2f}"
            cv2.putText(vis, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw trajectory
            track = self.tracker.get_track(track_id)
            if track and len(track.positions) > 1:
                pts = np.array(track.positions[-30:], np.int32)
                cv2.polylines(vis, [pts], False, color, 2)
        
        # Draw accident warning
        accident = result['accident_prediction']
        if accident['is_accident']:
            severity = accident['severity']
            severity_level = accident['severity_level']
            
            # Warning banner
            overlay = vis.copy()
            cv2.rectangle(overlay, (0, 0), (vis.shape[1], 80), (0, 0, 255), -1)
            vis = cv2.addWeighted(overlay, 0.5, vis, 0.5, 0)
            
            # Warning text
            warning = f"ACCIDENT DETECTED - Severity: {severity:.1f}% ({severity_level.upper()})"
            cv2.putText(vis, warning, (20, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            desc = accident.get('description', '')[:80]
            cv2.putText(vis, desc, (20, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Frame info
        info = f"Frame: {result['frame_number']} | Vehicles: {len(result['detections'])}"
        cv2.putText(vis, info, (10, vis.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return vis

