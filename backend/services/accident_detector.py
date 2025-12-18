"""
Accident detection service.
Pipeline: YOLOv11 → DeepSORT → Trajectory Analysis → Optical Flow → Decision Logic
"""
import os
import time
import uuid
import threading
import cv2
import numpy as np
from typing import Callable, List, Optional, Dict
from collections import deque
from datetime import datetime

from ..models.yolov11_detector import YOLOv11Detector
from ..models.deepsort_tracker import DeepSORTTracker
from ..models.trajectory_analyzer import TrajectoryAnalyzer
from ..models.optical_flow import OpticalFlowValidator
from ..models.schemas import DetectionResult, AccidentPrediction, TrackedObject
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AccidentDetector:
    """
    Comprehensive accident detection pipeline:
    CCTV Video → YOLOv11 (vehicles) → DeepSORT → Trajectory Analysis → Optical Flow → Decision
    """
    
    SEVERITY_THRESHOLDS = {
        'critical': 90,
        'high': 70,
        'medium': 50,
        'low': 30
    }

    def __init__(self, device: str = 'auto', fps: float = 30.0, save_clips: bool = True):
        """
        Initialize accident detector with full pipeline.
        
        Args:
            device: 'cpu', 'cuda', or 'auto'
            fps: Video frame rate for calculations
            save_clips: Whether to save accident video clips
        """
        self.fps = fps
        self.save_clips = save_clips
        self.clips_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'accidents')
        os.makedirs(self.clips_dir, exist_ok=True)
        
        # Initialize pipeline components
        logger.info("Initializing YOLOv11 vehicle detector...")
        self.detector = YOLOv11Detector(device=device)
        
        logger.info("Initializing DeepSORT tracker...")
        self.tracker = DeepSORTTracker()
        
        logger.info("Initializing trajectory analyzer...")
        self.trajectory_analyzer = TrajectoryAnalyzer(fps=fps)
        
        logger.info("Initializing optical flow validator...")
        self.optical_flow = OpticalFlowValidator()
        
        # Frame buffer for clip saving
        self.frame_buffer = deque(maxlen=int(fps * 10))  # 10 seconds
        self.frame_count = 0
        
        # Accident tracking
        self.accident_cooldown: Dict[str, int] = {}
        self.cooldown_frames = int(fps * 5)  # 5 second cooldown
        
        # Stream control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        logger.info("Accident detector pipeline initialized successfully")

    def process_frame(self, frame: np.ndarray, camera_id: str = None) -> Optional[AccidentPrediction]:
        """
        Process single frame through the full pipeline.
        
        Args:
            frame: BGR frame
            camera_id: Camera identifier
            
        Returns:
            AccidentPrediction if accident detected, None otherwise
        """
        self.frame_count += 1
        
        # Store frame in buffer for clip saving
        if self.save_clips:
            self.frame_buffer.append(frame.copy())
        
        try:
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
            prediction = self._make_decision(
                tracked_detections, trajectory_analyses, flow_result, camera_id
            )
            
            # Check cooldown
            if prediction.is_accident:
                cooldown_key = f"{camera_id}_{','.join(map(str, prediction.involved_tracks))}"
                if cooldown_key in self.accident_cooldown:
                    if self.frame_count - self.accident_cooldown[cooldown_key] < self.cooldown_frames:
                        return None
                self.accident_cooldown[cooldown_key] = self.frame_count
                
                # Attach frame buffer for clip saving
                if self.save_clips:
                    if not prediction.features:
                        prediction.features = {}
                    prediction.features['sequence_frames'] = list(self.frame_buffer)
                    prediction.features['trajectories'] = {
                        k: v.dict() if hasattr(v, 'dict') else str(v) 
                        for k, v in trajectory_analyses.items()
                    }
                
                return prediction
            
            return None
            
        except Exception as e:
            logger.error(f"Frame processing failed: {e}")
            return None

    def _make_decision(
        self,
        detections: List[DetectionResult],
        trajectories: Dict[int, any],
        flow: Optional[any],
        camera_id: str = None
    ) -> AccidentPrediction:
        """
        Make accident decision based on all inputs.
        
        Decision factors:
        1. Trajectory anomalies (sudden stops, collisions)
        2. Optical flow anomalies (impacts, chaotic motion)
        3. Multiple vehicle involvement
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
            score = getattr(analysis, 'anomaly_score', 0)
            if score > max_trajectory_score:
                max_trajectory_score = score
            
            if score > 30:
                involved_tracks.append(track_id)
                
                if getattr(analysis, 'sudden_stop', False):
                    description_parts.append(f"Vehicle {track_id}: sudden stop detected")
                    accident_type = accident_type or "sudden_stop"
                    
                if getattr(analysis, 'potential_collision', False):
                    partner = getattr(analysis, 'collision_partner_id', 'unknown')
                    description_parts.append(f"Vehicle {track_id}: collision with {partner}")
                    accident_type = "collision"
                    scores['collision_score'] = max(scores['collision_score'], 50)
        
        scores['trajectory_score'] = max_trajectory_score
        
        # Factor 2: Optical Flow
        if flow:
            scores['flow_score'] = getattr(flow, 'anomaly_score', 0)
            
            if getattr(flow, 'impact_detected', False):
                description_parts.append("High-impact event via optical flow")
                location = getattr(flow, 'impact_location', None)
                accident_type = accident_type or "impact"
                
            if getattr(flow, 'chaotic_flow', False):
                description_parts.append("Chaotic motion pattern detected")
        
        # Factor 3: Multi-vehicle involvement
        if len(involved_tracks) >= 2:
            scores['multi_vehicle_score'] = 30
            accident_type = "multi_vehicle_collision"
        
        # Calculate final severity
        severity = (
            scores['trajectory_score'] * 0.35 +
            scores['collision_score'] * 0.30 +
            scores['flow_score'] * 0.25 +
            scores['multi_vehicle_score'] * 0.10
        )
        
        is_accident = severity >= self.SEVERITY_THRESHOLDS['low']
        
        # Determine severity level
        severity_level = "low"
        for level, threshold in self.SEVERITY_THRESHOLDS.items():
            if severity >= threshold:
                severity_level = level
        
        confidence = min(1.0, severity / 100)
        
        description = "; ".join(description_parts) if description_parts else (
            "Potential accident detected" if is_accident else "No anomalies"
        )
        
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

    def save_accident_clip(
        self,
        event_id: str,
        frames: List[np.ndarray],
        timestamp: datetime = None
    ) -> Optional[str]:
        """Save accident video clip."""
        try:
            timestamp = timestamp or datetime.utcnow()
            date_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"accident_{event_id}_{date_str}.mp4"
            filepath = os.path.join(self.clips_dir, filename)
            
            if not frames:
                return None
            
            height, width = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(filepath, fourcc, self.fps, (width, height))
            
            for frame in frames:
                writer.write(frame)
            
            writer.release()
            logger.info(f"Saved accident clip: {filepath} ({len(frames)} frames)")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save clip: {e}")
            return None

    def start_stream(
        self,
        frame_iterator: Callable,
        fps: int = 1,
        callback: Optional[Callable] = None,
        camera_id: str = None
    ):
        """
        Start processing frames from a stream.
        
        Args:
            frame_iterator: Function returning iterator of frames
            fps: Processing FPS
            callback: Called with (prediction, frame) on detection
            camera_id: Camera identifier
        """
        if self._running:
            logger.warning("Detector already running")
            return
        
        self._running = True
        
        def _run():
            try:
                for frame in frame_iterator():
                    if not self._running:
                        break
                    
                    pred = self.process_frame(frame, camera_id)
                    
                    if pred and pred.is_accident and callback:
                        try:
                            callback(pred, frame)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                    
                    time.sleep(1.0 / max(1, fps))
                    
            except Exception as e:
                logger.error(f"Stream error: {e}")
            finally:
                self._running = False
        
        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop stream processing."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def reset(self):
        """Reset detector state."""
        self.tracker.reset()
        self.optical_flow.reset()
        self.frame_buffer.clear()
        self.frame_count = 0
        self.accident_cooldown.clear()

    def model_loaded(self) -> bool:
        """Check if detector is ready."""
        return self.detector is not None and self.detector.is_model_loaded()

    def get_pipeline_status(self) -> Dict:
        """Get status of all pipeline components."""
        return {
            'detector_loaded': self.detector.is_model_loaded() if self.detector else False,
            'tracker_active': self.tracker is not None,
            'trajectory_analyzer': self.trajectory_analyzer is not None,
            'optical_flow': self.optical_flow is not None,
            'frame_count': self.frame_count,
            'active_tracks': len(self.tracker.get_active_tracks()) if self.tracker else 0
        }
