"""
Video utilities: frame extraction, format conversion, basic preprocessing
"""
import os
import cv2
import tempfile
import time
import numpy as np
from typing import Iterator, Tuple, Optional, List
from collections import deque

# moviepy v2 may not expose `editor` as a top-level module; import directly with a fallback
try:
	from moviepy.editor import VideoFileClip
except Exception:
	from moviepy.video.io.VideoFileClip import VideoFileClip

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


def save_frames_as_video(frames: List[np.ndarray], output_path: str, fps: int = 30) -> Optional[str]:
    """
    Save a list of frames as a video file.
    
    Args:
        frames: List of numpy arrays (BGR format)
        output_path: Output video file path
        fps: Frames per second for output video
        
    Returns:
        str: Path to saved video file or None if failed
    """
    if not frames:
        logger.warning("No frames to save")
        return None
        
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Get frame dimensions
        height, width = frames[0].shape[:2]
        
        # Initialize video writer (try browser-friendly codecs first)
        writer = None
        for fourcc_str in ('avc1', 'H264', 'X264', 'mp4v'):
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                candidate = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                if candidate.isOpened():
                    writer = candidate
                    break
                candidate.release()
            except Exception:
                try:
                    candidate.release()
                except Exception:
                    pass
                continue
        
        if writer is None or not writer.isOpened():
            logger.error(f"Could not open video writer for {output_path}")
            return None
            
        # Write frames
        for frame in frames:
            writer.write(frame)
            
        writer.release()
        logger.info(f"Saved {len(frames)} frames to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error saving video: {e}")
        return None

def save_annotated_clip(frames: list, detections_per_frame: Optional[list] = None, output_path: str = None, fps: int = 5) -> Optional[str]:
	"""Save a short MP4 clip with bounding boxes/labels drawn on frames.

	Args:
		frames: list of np.ndarray frames (BGR)
		detections_per_frame: optional list where each element is a list of detections for corresponding frame
		output_path: path to write .mp4
		fps: frames per second for output

	Returns: output_path or None on failure
	"""
	if not frames:
		return None

	output_path = output_path or os.path.join(os.getcwd(), 'uploads', 'processed', 'accidents', f"clip_{int(time.time())}.mp4")
	# ensure dir exists
	dirname = os.path.dirname(output_path)
	os.makedirs(dirname, exist_ok=True)

	height, width = frames[0].shape[:2]
	fourcc = cv2.VideoWriter_fourcc(*'mp4v')
	writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

	for idx, frame in enumerate(frames):
		out = frame.copy()
		# Draw detections for this frame if provided
		if detections_per_frame and idx < len(detections_per_frame):
			for det in detections_per_frame[idx] if detections_per_frame[idx] else []:
				try:
					x, y, w, h = det.bbox
					cls = getattr(det, 'class_name', getattr(det, 'class', 'object'))
					conf = getattr(det, 'confidence', getattr(det, 'score', None))
					label = f"{cls} {conf:.2f}" if conf is not None else f"{cls}"
					# Draw box
					pt1 = (int(x), int(y))
					pt2 = (int(x + w), int(y + h))
					cv2.rectangle(out, pt1, pt2, (0, 0, 255), 2)
					# Put label
					cv2.putText(out, label, (pt1[0], max(15, pt1[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1, cv2.LINE_AA)
				except Exception:
					continue

		# Write frame
		writer.write(out)

	writer.release()
	logger.info(f"Saved annotated clip: {output_path}")
	return output_path

