"""
Speed and Trajectory Analyzer
Analyzes vehicle movements for anomaly detection
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque
import math

from ..utils.logger import setup_logger
from .schemas import TrackedObject, TrajectoryAnalysis

logger = setup_logger(__name__)


class TrajectoryAnalyzer:
    """
    Analyzes vehicle trajectories and speeds for accident indicators
    """
    
    def __init__(
        self,
        fps: float = 30.0,
        pixels_per_meter: float = 10.0,
        sudden_stop_threshold: float = 15.0,  # m/s² deceleration
        collision_distance: float = 50.0,  # pixels
        abnormal_angle_threshold: float = 45.0,  # degrees
        speed_anomaly_threshold: float = 2.0  # standard deviations
    ):
        """
        Initialize trajectory analyzer
        
        Args:
            fps: Video frame rate
            pixels_per_meter: Conversion factor (estimated)
            sudden_stop_threshold: Deceleration threshold for sudden stop (m/s²)
            collision_distance: Distance threshold for collision detection (pixels)
            abnormal_angle_threshold: Angle change threshold for abnormal movement
            speed_anomaly_threshold: Standard deviations for speed anomaly
        """
        self.fps = fps
        self.pixels_per_meter = pixels_per_meter
        self.sudden_stop_threshold = sudden_stop_threshold
        self.collision_distance = collision_distance
        self.abnormal_angle_threshold = abnormal_angle_threshold
        self.speed_anomaly_threshold = speed_anomaly_threshold
        
        # Historical speed data for anomaly detection
        self.speed_history = deque(maxlen=1000)

    def analyze_tracks(self, tracks: Dict[int, TrackedObject]) -> Dict[int, TrajectoryAnalysis]:
        """
        Analyze all tracks for accident indicators
        
        Args:
            tracks: Dictionary of track_id -> TrackedObject
            
        Returns:
            Dictionary of track_id -> TrajectoryAnalysis
        """
        analyses = {}
        
        for track_id, track in tracks.items():
            if len(track.positions) < 3:
                continue
            
            analysis = self._analyze_single_track(track)
            analyses[track_id] = analysis
        
        # Check for potential collisions between tracks
        collision_pairs = self._detect_collisions(tracks)
        
        # Update analyses with collision info
        for track1_id, track2_id in collision_pairs:
            if track1_id in analyses:
                analyses[track1_id].potential_collision = True
                analyses[track1_id].collision_partner_id = track2_id
            if track2_id in analyses:
                analyses[track2_id].potential_collision = True
                analyses[track2_id].collision_partner_id = track1_id
        
        return analyses

    def _analyze_single_track(self, track: TrackedObject) -> TrajectoryAnalysis:
        """Analyze a single track for anomalies"""
        positions = np.array(track.positions)
        
        # Calculate speeds (pixels/frame)
        speeds = []
        for i in range(1, len(positions)):
            dist = np.linalg.norm(positions[i] - positions[i-1])
            speeds.append(dist)
        
        speeds = np.array(speeds) if speeds else np.array([0])
        
        # Convert to m/s (approximate)
        speeds_ms = speeds * self.fps / self.pixels_per_meter
        
        # Calculate accelerations
        accelerations = np.diff(speeds_ms) * self.fps if len(speeds_ms) > 1 else np.array([0])
        
        # Calculate direction changes
        directions = []
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            angle = math.degrees(math.atan2(dy, dx))
            directions.append(angle)
        
        direction_changes = np.abs(np.diff(directions)) if len(directions) > 1 else np.array([0])
        # Normalize angle changes to [-180, 180]
        direction_changes = np.where(direction_changes > 180, 360 - direction_changes, direction_changes)
        
        # Detect anomalies
        sudden_stop = np.any(accelerations < -self.sudden_stop_threshold)
        sudden_acceleration = np.any(accelerations > self.sudden_stop_threshold)
        abnormal_direction = np.any(direction_changes > self.abnormal_angle_threshold)
        
        # Speed anomaly detection
        current_speed = speeds_ms[-1] if len(speeds_ms) > 0 else 0
        self.speed_history.append(current_speed)
        
        if len(self.speed_history) > 100:
            mean_speed = np.mean(list(self.speed_history))
            std_speed = np.std(list(self.speed_history))
            speed_anomaly = abs(current_speed - mean_speed) > self.speed_anomaly_threshold * std_speed
        else:
            speed_anomaly = False
        
        # Calculate trajectory smoothness (lower = more erratic)
        if len(direction_changes) > 2:
            smoothness = 1.0 / (1.0 + np.std(direction_changes))
        else:
            smoothness = 1.0
        
        # Anomaly score (0-100)
        anomaly_score = 0
        if sudden_stop:
            anomaly_score += 40
        if sudden_acceleration:
            anomaly_score += 20
        if abnormal_direction:
            anomaly_score += 25
        if speed_anomaly:
            anomaly_score += 15
        
        anomaly_score = min(100, anomaly_score)
        
        return TrajectoryAnalysis(
            track_id=track.track_id,
            avg_speed=float(np.mean(speeds_ms)),
            max_speed=float(np.max(speeds_ms)) if len(speeds_ms) > 0 else 0,
            current_speed=float(current_speed),
            max_acceleration=float(np.max(np.abs(accelerations))) if len(accelerations) > 0 else 0,
            sudden_stop=sudden_stop,
            sudden_acceleration=sudden_acceleration,
            abnormal_direction_change=abnormal_direction,
            max_direction_change=float(np.max(direction_changes)) if len(direction_changes) > 0 else 0,
            trajectory_smoothness=float(smoothness),
            speed_anomaly=speed_anomaly,
            anomaly_score=anomaly_score,
            potential_collision=False,
            collision_partner_id=None
        )

    def _detect_collisions(self, tracks: Dict[int, TrackedObject]) -> List[Tuple[int, int]]:
        """Detect potential collisions between tracks"""
        collision_pairs = []
        track_ids = list(tracks.keys())
        
        for i in range(len(track_ids)):
            for j in range(i + 1, len(track_ids)):
                track1 = tracks[track_ids[i]]
                track2 = tracks[track_ids[j]]
                
                if not track1.positions or not track2.positions:
                    continue
                
                # Get current positions
                pos1 = np.array(track1.positions[-1])
                pos2 = np.array(track2.positions[-1])
                
                # Calculate distance
                distance = np.linalg.norm(pos1 - pos2)
                
                if distance < self.collision_distance:
                    # Check if tracks are converging
                    if len(track1.positions) >= 2 and len(track2.positions) >= 2:
                        prev_pos1 = np.array(track1.positions[-2])
                        prev_pos2 = np.array(track2.positions[-2])
                        prev_distance = np.linalg.norm(prev_pos1 - prev_pos2)
                        
                        if distance < prev_distance:  # Converging
                            collision_pairs.append((track_ids[i], track_ids[j]))
                    else:
                        collision_pairs.append((track_ids[i], track_ids[j]))
        
        return collision_pairs

    def predict_collision(self, track1: TrackedObject, track2: TrackedObject, frames_ahead: int = 10) -> Optional[Tuple[float, float]]:
        """
        Predict if two tracks will collide
        
        Args:
            track1: First tracked object
            track2: Second tracked object
            frames_ahead: Number of frames to predict ahead
            
        Returns:
            Predicted collision point (x, y) or None
        """
        if len(track1.positions) < 2 or len(track2.positions) < 2:
            return None
        
        # Get current velocities
        vel1 = np.array(track1.positions[-1]) - np.array(track1.positions[-2])
        vel2 = np.array(track2.positions[-1]) - np.array(track2.positions[-2])
        
        pos1 = np.array(track1.positions[-1])
        pos2 = np.array(track2.positions[-1])
        
        # Predict positions
        for t in range(1, frames_ahead + 1):
            future_pos1 = pos1 + vel1 * t
            future_pos2 = pos2 + vel2 * t
            
            distance = np.linalg.norm(future_pos1 - future_pos2)
            
            if distance < self.collision_distance:
                collision_point = (future_pos1 + future_pos2) / 2
                return tuple(collision_point)
        
        return None

    def calculate_time_to_collision(self, track1: TrackedObject, track2: TrackedObject) -> Optional[float]:
        """
        Calculate estimated time to collision between two tracks
        
        Returns:
            Time to collision in seconds, or None if no collision predicted
        """
        if len(track1.positions) < 2 or len(track2.positions) < 2:
            return None
        
        pos1 = np.array(track1.positions[-1])
        pos2 = np.array(track2.positions[-1])
        vel1 = np.array(track1.positions[-1]) - np.array(track1.positions[-2])
        vel2 = np.array(track2.positions[-1]) - np.array(track2.positions[-2])
        
        # Relative position and velocity
        rel_pos = pos2 - pos1
        rel_vel = vel2 - vel1
        
        # Time to closest approach
        rel_vel_squared = np.dot(rel_vel, rel_vel)
        if rel_vel_squared < 1e-6:
            return None
        
        ttc = -np.dot(rel_pos, rel_vel) / rel_vel_squared
        
        if ttc < 0:
            return None  # Moving apart
        
        # Check if they'll actually get close enough
        closest_dist = np.linalg.norm(rel_pos + rel_vel * ttc)
        
        if closest_dist < self.collision_distance:
            return ttc / self.fps  # Convert to seconds
        
        return None

