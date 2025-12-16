"""
Video processing service: frame extraction, buffering and preprocessing for inference
"""
import time
from typing import Callable, Iterator, Optional
import threading
import numpy as np
from ..utils.video_utils import extract_frames, preprocess_frame, convert_to_mp4
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def frame_generator_from_file(path: str, fps: int = 1) -> Iterator[np.ndarray]:
	"""Yield frames from a video file at approximately the requested fps."""
	try:
		for frame in extract_frames(path, fps=fps):
			yield frame
	except Exception as e:
		logger.error(f"frame_generator_from_file error: {e}")
		return


class VideoStreamProcessor:
	"""Process a video stream in a background thread and call a callback for each frame."""

	def __init__(self, frame_callback: Callable[[np.ndarray], None], fps: int = 1):
		self.frame_callback = frame_callback
		self.fps = fps
		self._running = False
		self._thread: Optional[threading.Thread] = None

	def process_file(self, file_path: str):
		def _run():
			try:
				for frame in frame_generator_from_file(file_path, fps=self.fps):
					if not self._running:
						break
					try:
						self.frame_callback(frame)
					except Exception as e:
						logger.error(f"Frame callback failed: {e}")
					time.sleep(1.0 / max(1, self.fps))
			except Exception as e:
				logger.error(f"Processing failed: {e}")
			finally:
				self._running = False

		if self._running:
			logger.warning("Processor already running")
			return

		self._running = True
		self._thread = threading.Thread(target=_run, daemon=True)
		self._thread.start()

	def stop(self):
		self._running = False
		if self._thread:
			self._thread.join(timeout=2.0)

