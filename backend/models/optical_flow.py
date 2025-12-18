"""
Optical Flow Validation
Uses optical flow to validate sudden motion changes and collision detection
"""
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from collections import deque

from ..utils.logger import setup_logger
from .schemas import OpticalFlowResult

logger = setup_logger(__name__)


class OpticalFlowValidator:
    """
    Uses optical flow to validate accident detection
    Detects sudden motion changes, impacts, and abnormal movements
    """
    
    def __init__(
        self,
        flow_threshold: float = 2.0,
        impact_threshold: float = 10.0,
        history_size: int = 10
    ):
        """
        Initialize optical flow validator
        
        Args:
            flow_threshold: Minimum flow magnitude to consider
            impact_threshold: Flow magnitude indicating potential impact
            history_size: Number of frames to keep in history
        """
        self.flow_threshold = flow_threshold
        self.impact_threshold = impact_threshold
        self.history_size = history_size
        
        # Frame history
        self.prev_gray = None
        self.flow_history = deque(maxlen=history_size)
        self.magnitude_history = deque(maxlen=history_size)
        
        # Farneback optical flow parameters
        self.farneback_params = dict(
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )

    def compute_flow(self, frame: np.ndarray) -> Optional[OpticalFlowResult]:
        """
        Compute optical flow between current and previous frame
        
        Args:
            frame: Current frame (BGR format)
            
        Returns:
            OpticalFlowResult or None if not enough frames
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return None
        
        try:
            # Compute dense optical flow using Farneback method
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None, **self.farneback_params
            )
            
            # Calculate magnitude and angle
            magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            
            # Store in history
            self.flow_history.append(flow)
            self.magnitude_history.append(magnitude)
            
            # Analyze flow
            result = self._analyze_flow(flow, magnitude, angle)
            
            # Update previous frame
            self.prev_gray = gray
            
            return result
            
        except Exception as e:
            logger.error(f"Optical flow computation failed: {e}")
            self.prev_gray = gray
            return None

    def _analyze_flow(self, flow: np.ndarray, magnitude: np.ndarray, angle: np.ndarray) -> OpticalFlowResult:
        """Analyze optical flow for anomalies"""
        
        # Calculate statistics
        avg_magnitude = np.mean(magnitude)
        max_magnitude = np.max(magnitude)
        
        # Find regions with significant flow
        significant_mask = magnitude > self.flow_threshold
        significant_flow = magnitude[significant_mask]
        
        # Calculate flow direction consistency
        if np.sum(significant_mask) > 0:
            significant_angles = angle[significant_mask]
            angle_variance = np.var(significant_angles)
            direction_consistency = 1.0 / (1.0 + angle_variance)
        else:
            direction_consistency = 1.0
        
        # Detect sudden changes
        sudden_change = False
        if len(self.magnitude_history) >= 2:
            prev_avg = np.mean(self.magnitude_history[-2])
            change_ratio = avg_magnitude / (prev_avg + 1e-6)
            sudden_change = change_ratio > 3.0 or change_ratio < 0.3
        
        # Detect potential impact (very high localized flow)
        impact_detected = False
        impact_location = None
        if max_magnitude > self.impact_threshold:
            impact_detected = True
            # Find impact location
            impact_y, impact_x = np.unravel_index(np.argmax(magnitude), magnitude.shape)
            impact_location = (int(impact_x), int(impact_y))
        
        # Detect chaotic flow (multiple directions in small area)
        chaotic_flow = direction_consistency < 0.3 and avg_magnitude > self.flow_threshold
        
        # Calculate anomaly score based on flow analysis
        anomaly_score = 0
        if impact_detected:
            anomaly_score += 50
        if sudden_change:
            anomaly_score += 30
        if chaotic_flow:
            anomaly_score += 20
        
        anomaly_score = min(100, anomaly_score)
        
        return OpticalFlowResult(
            avg_magnitude=float(avg_magnitude),
            max_magnitude=float(max_magnitude),
            direction_consistency=float(direction_consistency),
            sudden_change=sudden_change,
            impact_detected=impact_detected,
            impact_location=impact_location,
            chaotic_flow=chaotic_flow,
            anomaly_score=anomaly_score,
            flow_field=flow
        )

    def validate_collision(
        self,
        bbox1: Tuple[int, int, int, int],
        bbox2: Tuple[int, int, int, int]
    ) -> Tuple[bool, float]:
        """
        Validate potential collision using optical flow in the region between two bboxes
        
        Args:
            bbox1: First bounding box (x, y, w, h)
            bbox2: Second bounding box (x, y, w, h)
            
        Returns:
            Tuple of (is_collision, confidence)
        """
        if len(self.flow_history) < 1:
            return False, 0.0
        
        flow = self.flow_history[-1]
        magnitude = self.magnitude_history[-1]
        
        # Get region between bboxes
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate overlap/between region
        cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2
        cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2
        
        # ROI around the midpoint between centers
        mid_x = (cx1 + cx2) // 2
        mid_y = (cy1 + cy2) // 2
        roi_size = max(w1, h1, w2, h2)
        
        # Extract ROI from magnitude
        y_start = max(0, mid_y - roi_size // 2)
        y_end = min(magnitude.shape[0], mid_y + roi_size // 2)
        x_start = max(0, mid_x - roi_size // 2)
        x_end = min(magnitude.shape[1], mid_x + roi_size // 2)
        
        if y_start >= y_end or x_start >= x_end:
            return False, 0.0
        
        roi_magnitude = magnitude[y_start:y_end, x_start:x_end]
        
        # Check for high flow in collision region
        avg_roi_magnitude = np.mean(roi_magnitude)
        max_roi_magnitude = np.max(roi_magnitude)
        
        is_collision = max_roi_magnitude > self.impact_threshold
        confidence = min(1.0, max_roi_magnitude / (self.impact_threshold * 2))
        
        return is_collision, float(confidence)

    def get_motion_regions(self, frame: np.ndarray, threshold: float = None) -> List[Tuple[int, int, int, int]]:
        """
        Get bounding boxes of regions with significant motion
        
        Args:
            frame: Current frame
            threshold: Flow magnitude threshold
            
        Returns:
            List of bounding boxes (x, y, w, h)
        """
        result = self.compute_flow(frame)
        
        if result is None or len(self.magnitude_history) < 1:
            return []
        
        threshold = threshold or self.flow_threshold
        magnitude = self.magnitude_history[-1]
        
        # Threshold the magnitude
        _, binary = cv2.threshold(
            (magnitude * 255 / magnitude.max()).astype(np.uint8),
            int(threshold * 255 / magnitude.max()),
            255,
            cv2.THRESH_BINARY
        )
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Get bounding boxes
        regions = []
        min_area = 500  # Minimum area to consider
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                regions.append((x, y, w, h))
        
        return regions

    def visualize_flow(self, frame: np.ndarray, scale: float = 3.0) -> np.ndarray:
        """
        Visualize optical flow on frame
        
        Args:
            frame: Input frame
            scale: Arrow scale factor
            
        Returns:
            Frame with flow visualization
        """
        if len(self.flow_history) < 1:
            return frame.copy()
        
        flow = self.flow_history[-1]
        vis = frame.copy()
        
        # Draw flow vectors
        step = 16
        h, w = flow.shape[:2]
        
        for y in range(0, h, step):
            for x in range(0, w, step):
                fx, fy = flow[y, x]
                magnitude = np.sqrt(fx**2 + fy**2)
                
                if magnitude > self.flow_threshold:
                    end_x = int(x + fx * scale)
                    end_y = int(y + fy * scale)
                    
                    # Color based on magnitude
                    color_intensity = min(255, int(magnitude * 25))
                    color = (0, color_intensity, 255 - color_intensity)
                    
                    cv2.arrowedLine(vis, (x, y), (end_x, end_y), color, 1, tipLength=0.3)
        
        return vis

    def reset(self):
        """Reset optical flow state"""
        self.prev_gray = None
        self.flow_history.clear()
        self.magnitude_history.clear()

