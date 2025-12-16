"""
Accident detection service.
Combines YOLOv8 object detection, simple tracking and temporal analysis to detect accidents.
"""
import time
import threading
from typing import Callable, List, Optional
import numpy as np
from ..models.yolov8_detector import YOLOv8Detector
from ..models.temporal_analyzer import TemporalAnalyzer
from ..models.schemas import DetectionResult, AccidentPrediction
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AccidentDetector:
    """High-level detector orchestrating per-frame detection and temporal analysis."""

    def __init__(self, device: str = 'cpu'):
        self.detector = YOLOv8Detector(device=device)
        self.temporal = TemporalAnalyzer(device=device)
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Simple tracker state
        self._next_track_id = 0
        self._tracks = {}  # track_id -> last center

    def _assign_tracking_ids(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Assign simple tracking ids by nearest-center matching."""
        updated = []
        for det in detections:
            x, y, w, h = det.bbox
            center = (x + w // 2, y + h // 2)

            best_id = None
            best_dist = float('inf')

            for tid, pos in self._tracks.items():
                dist = (pos[0] - center[0])**2 + (pos[1] - center[1])**2
                if dist < best_dist and dist < 2500:  # 50 px threshold
                    best_dist = dist
                    best_id = tid

            if best_id is None:
                tid = self._next_track_id
                self._next_track_id += 1
            else:
                tid = best_id

            self._tracks[tid] = center
            det.tracking_id = tid
            updated.append(det)

        return updated

    def process_frame(self, frame: np.ndarray) -> Optional[AccidentPrediction]:
        """Process a single frame and return an AccidentPrediction if available."""
        try:
            detections = self.detector.detect(frame)
            detections = self._assign_tracking_ids(detections)

            # Add to temporal analyzer
            self.temporal.add_frame(frame, detections)

            if self.temporal.get_buffer_status().get('buffer_full'):
                prediction = self.temporal.analyze_sequence()
                # Optionally clear buffer to avoid duplicate alerts
                self.temporal.clear_buffer()
                if prediction.is_accident:
                    logger.info(f"Accident detected: {prediction}")
                return prediction

            return None

        except Exception as e:
            logger.error(f"Frame processing failed: {e}")
            return None

    def start_stream(self, frame_iterator: Callable[[], List[np.ndarray]], fps: int = 1, callback: Optional[Callable] = None):
        """Start processing frames from a callable that yields frames.

        Args:
            frame_iterator: function returning an iterator/generator of frames
            fps: processing fps
            callback: optional function called with (prediction, frame)
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

                    pred = self.process_frame(frame)
                    if pred and callback:
                        try:
                            callback(pred, frame)
                        except Exception as cb_e:
                            logger.error(f"Callback error: {cb_e}")

                    time.sleep(1.0 / max(1, fps))
            except Exception as e:
                logger.error(f"Stream processing error: {e}")
            finally:
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def model_loaded(self) -> bool:
        """Return whether the underlying model is loaded and ready."""
        try:
            return self.detector is not None and getattr(self.detector, 'model', None) is not None
        except Exception:
            return False
