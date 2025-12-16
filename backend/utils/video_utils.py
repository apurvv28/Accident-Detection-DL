"""
Video utilities: frame extraction, format conversion, basic preprocessing
"""
import os
import cv2
import tempfile
import numpy as np
from typing import Iterator, Tuple, Optional
from moviepy import VideoFileClip
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def extract_frames(video_path: str, fps: int = 1) -> Iterator[np.ndarray]:
	"""Yield frames from video at approx. the requested fps.

	Args:
		video_path: path to input video file
		fps: frames per second to sample
	"""
	try:
		cap = cv2.VideoCapture(video_path)
		if not cap.isOpened():
			logger.error(f"Cannot open video: {video_path}")
			return

		video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
		step = max(1, int(round(video_fps / max(1, fps))))
		idx = 0

		while True:
			ret, frame = cap.read()
			if not ret:
				break

			if idx % step == 0:
				yield frame

			idx += 1

	finally:
		try:
			cap.release()
		except Exception:
			pass


def convert_to_mp4(input_path: str, output_path: Optional[str] = None) -> str:
	"""Convert video to MP4 using moviepy (FFmpeg).

	Returns output path.
	"""
	output_path = output_path or os.path.splitext(input_path)[0] + "_converted.mp4"

	try:
		clip = VideoFileClip(input_path)
		clip.write_videofile(output_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
		clip.close()
		logger.info(f"Converted {input_path} -> {output_path}")
		return output_path
	except Exception as e:
		logger.error(f"Video conversion failed: {e}")
		return input_path


def preprocess_frame(frame: np.ndarray, target_size: Tuple[int, int] = (640, 360)) -> np.ndarray:
	"""Resize and normalize a frame for model consumption."""
	resized = cv2.resize(frame, target_size)
	# Convert BGR -> RGB
	rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
	normalized = rgb.astype('float32') / 255.0
	return normalized

