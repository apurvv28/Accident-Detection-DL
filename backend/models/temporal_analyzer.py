"""
Temporal Accident Analyzer using ConvLSTM
Analyzes sequences of frames to detect accidents
"""
import os
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque
import time
import cv2

# Try to import torch, provide fallback
try:
	import torch
	import torch.nn as nn
	import torch.nn.functional as F
	TORCH_AVAILABLE = True
except Exception:
	TORCH_AVAILABLE = False
	print("Warning: PyTorch not installed. Using dummy temporal analyzer.")

from ..utils.logger import setup_logger
from .schemas import TrackedObject, AccidentPrediction
from .yolov8_detector import YOLOv8Detector

# Optional X3D integration (pytorchvideo)
try:
	from .x3d_accident import X3DAccidentModel
	PYTORCHVIDEO_AVAILABLE = True
except Exception:
	X3DAccidentModel = None
	PYTORCHVIDEO_AVAILABLE = False

logger = setup_logger(__name__)


# Only define PyTorch classes when PyTorch is available
if TORCH_AVAILABLE:
	class ConvLSTM(nn.Module):
		"""
		ConvLSTM layer for spatiotemporal feature extraction
		"""
		def __init__(self, input_dim, hidden_dim, kernel_size, bias=True):
			super(ConvLSTM, self).__init__()
			self.input_dim = input_dim
			self.hidden_dim = hidden_dim
			self.kernel_size = kernel_size
			self.padding = kernel_size // 2
			self.bias = bias

			# Convolutional layers for gates
			self.conv_i = nn.Conv2d(in_channels=input_dim + hidden_dim,
								   out_channels=hidden_dim,
								   kernel_size=kernel_size,
								   padding=self.padding,
								   bias=bias)

			self.conv_f = nn.Conv2d(in_channels=input_dim + hidden_dim,
								   out_channels=hidden_dim,
								   kernel_size=kernel_size,
								   padding=self.padding,
								   bias=bias)

			self.conv_c = nn.Conv2d(in_channels=input_dim + hidden_dim,
								   out_channels=hidden_dim,
								   kernel_size=kernel_size,
								   padding=self.padding,
								   bias=bias)

			self.conv_o = nn.Conv2d(in_channels=input_dim + hidden_dim,
								   out_channels=hidden_dim,
								   kernel_size=kernel_size,
								   padding=self.padding,
								   bias=bias)

		def forward(self, input_tensor, cur_state):
			h_cur, c_cur = cur_state

			combined = torch.cat([input_tensor, h_cur], dim=1)

			i = torch.sigmoid(self.conv_i(combined))
			f = torch.sigmoid(self.conv_f(combined))
			c = torch.tanh(self.conv_c(combined))
			o = torch.sigmoid(self.conv_o(combined))

			c_next = f * c_cur + i * c
			h_next = o * torch.tanh(c_next)

			return h_next, c_next

		def init_hidden(self, batch_size, image_size):
			height, width = image_size
			return (torch.zeros(batch_size, self.hidden_dim, height, width),
					torch.zeros(batch_size, self.hidden_dim, height, width))
else:
	ConvLSTM = None


class TemporalAnalyzer:
	"""
	Temporal analysis for accident detection using ConvLSTM
	"""

	def __init__(self, model_path: str = None, device: str = 'cpu'):
		"""
		Initialize temporal analyzer

		Args:
			model_path: Path to trained model
			device: 'cpu' or 'cuda'
		"""
		self.model_path = model_path or os.getenv('TEMPORAL_MODEL_PATH', 'static/models/temporal_accident.pth')
		self.device = device
		self.model = None

		# Configuration
		self.sequence_length = 8  # Number of frames to analyze
		self.frame_interval = 2   # Take every Nth frame

		# Buffer for recent frames and detections
		self.frame_buffer = deque(maxlen=self.sequence_length)
		self.detection_buffer = deque(maxlen=self.sequence_length)

		# Initialize YOLO detector
		self.detector = YOLOv8Detector(device=device)

		# Accident detection thresholds
		self.velocity_threshold = 10.0  # pixels/frame for sudden stop
		self.collision_iou_threshold = 0.3  # IOU for collision detection
		self.abnormal_angle_threshold = 45.0  # degrees for abnormal direction change

		self.load_model()

		logger.info("TemporalAnalyzer initialized")

	def load_model(self):
		"""Load temporal model"""
		if not TORCH_AVAILABLE:
			logger.warning("PyTorch not available. Using rule-based analysis.")
			return

		try:
			if os.path.exists(self.model_path):
				logger.info(f"Loading temporal model from: {self.model_path}")

				# Try to load as legacy ConvLSTM checkpoint first
				loaded = torch.load(self.model_path, map_location=self.device)
				# If checkpoint looks like PyTorchVideo format (has 'model_state'), prefer X3D
				if isinstance(loaded, dict) and 'model_state' in loaded and PYTORCHVIDEO_AVAILABLE:
					try:
						logger.info("Detected PyTorchVideo checkpoint — attempting to load X3D model")
						self.model = X3DAccidentModel(checkpoint_path=self.model_path, device=self.device)
						logger.info("X3D temporal model loaded successfully")
					except Exception as e:
						logger.error(f"Failed to load X3D model: {e}")
						self.model = None
				else:
					# Fallback to legacy ConvLSTM style model
					if not TORCH_AVAILABLE or AccidentConvLSTM is None:
						logger.warning("PyTorch not available. Cannot load ConvLSTM model.")
						self.model = None
					else:
						try:
							self.model = AccidentConvLSTM()
							self.model.load_state_dict(loaded)
							self.model.to(self.device)
							self.model.eval()
							logger.info("Temporal model loaded successfully")
						except Exception as e:
							logger.error(f"Failed to load temporal model: {e}")
							self.model = None
			else:
				logger.warning(f"Temporal model not found at {self.model_path}.")
				# If a model URL is provided via TEMPORAL_MODEL_URL, attempt download and load
				model_url = os.getenv('TEMPORAL_MODEL_URL')
				if model_url:
					try:
						logger.info(f"TEMPORAL_MODEL_URL set — attempting to download model from: {model_url}")
						# Ensure target directory exists
						dirpath = os.path.dirname(self.model_path)
						if dirpath and not os.path.exists(dirpath):
							os.makedirs(dirpath, exist_ok=True)
						# Download using requests if available, else urllib
						success = False
						# Prefer requests if installed
						try:
							import requests
							try:
								with requests.get(model_url, stream=True, timeout=30) as r:
									r.raise_for_status()
									with open(self.model_path, 'wb') as fh:
										for chunk in r.iter_content(chunk_size=8192):
											if chunk:
												fh.write(chunk)
									success = True
							except Exception:
								# requests download failed; fallback to urllib below
								pass
						except Exception:
							# requests not available, fall back
							pass
						if not success:
							try:
								from urllib.request import urlopen
								with urlopen(model_url, timeout=30) as r:
									with open(self.model_path, 'wb') as fh:
										fh.write(r.read())
								success = True
							except Exception as e:
								logger.error(f"Failed to download temporal model: {e}")
						if success:
							# Try to load model after download
							if not TORCH_AVAILABLE or AccidentConvLSTM is None:
								logger.warning("PyTorch not available. Cannot load ConvLSTM model.")
								self.model = None
							else:
								try:
									self.model = AccidentConvLSTM()
									self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
									self.model.to(self.device)
									self.model.eval()
									logger.info("Temporal model downloaded and loaded successfully")
								except Exception as e:
									logger.error(f"Failed to load downloaded temporal model: {e}")
									self.model = None
					except Exception as e:
						logger.error(f"Error while attempting to download temporal model: {e}")
						self.model = None
				else:
					logger.warning("Temporal model not provided and no TEMPORAL_MODEL_URL set — using rule-based analysis.")
					self.model = None
		except Exception as e:
			logger.error(f"Failed to load temporal model: {e}")
			self.model = None

	def add_frame(self, frame: np.ndarray, detections: List):
		"""
		Add frame and detections to buffer for temporal analysis

		Args:
			frame: Input frame
			detections: List of detections from YOLO
		"""
		self.frame_buffer.append(frame.copy())
		self.detection_buffer.append(detections.copy())

	def analyze_sequence(self) -> AccidentPrediction:
		"""
		Analyze recent sequence for accident patterns

		Returns:
			AccidentPrediction with results
		"""
		if len(self.frame_buffer) < self.sequence_length:
			return AccidentPrediction(
				is_accident=False,
				confidence=0.0,
				accident_type=None,
				severity='low',
				description="Insufficient frames for analysis"
			)

		# Extract sequence
		frames = list(self.frame_buffer)
		detections_list = list(self.detection_buffer)

		# Use model-based analysis if available
		if self.model is not None and TORCH_AVAILABLE:
			try:
				prediction = self._model_based_analysis(frames, detections_list)
			except Exception as e:
				logger.error(f"Model-based analysis failed: {e}")
				prediction = self._rule_based_analysis(frames, detections_list)
		else:
			# Fallback to rule-based analysis
			prediction = self._rule_based_analysis(frames, detections_list)

		return prediction

	def _model_based_analysis(self, frames: List[np.ndarray], 
							detections_list: List[List]) -> AccidentPrediction:
		"""
		Analyze sequence using loaded model (X3D wrapper or ConvLSTM)
		"""
		try:
			# Preprocess frames for model input (X3D expects (B, C, T, H, W))
			input_tensor = self._preprocess_frames_for_x3d(frames)

			with torch.no_grad():
				input_tensor = input_tensor.to(self.device)
				output = self.model(input_tensor)

				# If model returns logits shape (B,1) convert to probability
				if isinstance(output, torch.Tensor):
					prob = torch.sigmoid(output).item()
				else:
					prob = float(output)

				# Determine accident type using detections heuristics
				features = self._extract_temporal_features(detections_list)
				accident_type = self._classify_accident_type(features)

				confidence = float(prob)
				if confidence > 0.8:
					severity = 'high'
				elif confidence > 0.5:
					severity = 'medium'
				else:
					severity = 'low'

				return AccidentPrediction(
					is_accident=confidence > 0.5,
					confidence=confidence,
					accident_type=accident_type,
					severity=severity,
					description='Model-based temporal analysis result (X3D)'
				)

		except Exception as e:
			logger.error(f"Error in model-based analysis: {e}")
			return self._rule_based_analysis(frames, detections_list)

	def _preprocess_frames_for_x3d(self, frames: List[np.ndarray]) -> 'torch.Tensor':
		"""Convert list of frames (H,W,3) to (1,3,T,H,W) float tensor normalized to [0,1]"""
		import torch

		# Resize to 112x112 and stack
		processed = []
		for f in frames:
			# convert BGR->RGB
			img = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
			img = cv2.resize(img, (112, 112))
			img = img.astype('float32') / 255.0
			# HWC -> CHW
			img = img.transpose(2, 0, 1)
			processed.append(img)

		arr = np.stack(processed, axis=1)  # shape (C, T, H, W)
		arr = np.expand_dims(arr, axis=0)  # (1, C, T, H, W)
		return torch.from_numpy(arr)

	def _rule_based_analysis(self, frames: List[np.ndarray], 
						detections_list: List[List]) -> AccidentPrediction:
		"""
		Rule-based accident detection using multiple heuristics
		"""
		try:
			# Extract temporal features
			features = self._extract_temporal_features(detections_list)

			# Apply multiple heuristics
			scores = {
				'collision': self._detect_collision(features),
				'sudden_stop': self._detect_sudden_stop(features),
				'abnormal_movement': self._detect_abnormal_movement(features),
				'multiple_vehicles': self._detect_multiple_vehicles(features),
				'pedestrian_involvement': self._detect_pedestrian_involvement(features)
			}

			# Calculate overall confidence
			weights = {
				'collision': 0.4,
				'sudden_stop': 0.25,
				'abnormal_movement': 0.15,
				'multiple_vehicles': 0.1,
				'pedestrian_involvement': 0.1
			}

			total_score = sum(scores[rule] * weights[rule] for rule in scores)

			# Determine accident type
			accident_type = self._classify_accident_type(features)

			# Determine severity
			if total_score > 0.8:
				severity = 'high'
				is_accident = True
			elif total_score > 0.6:
				severity = 'medium'
				is_accident = True
			elif total_score > 0.4:
				severity = 'low'
				is_accident = False  # Warning level
			else:
				severity = 'low'
				is_accident = False

			description = f"Rule-based analysis: {accident_type}. Scores: {scores}"

			return AccidentPrediction(
				is_accident=is_accident,
				confidence=float(total_score),
				accident_type=accident_type if is_accident else None,
				severity=severity,
				description=description,
				features=features,
				rule_scores=scores
			)

		except Exception as e:
			logger.error(f"Rule-based analysis failed: {e}")
			return AccidentPrediction(
				is_accident=False,
				confidence=0.0,
				accident_type=None,
				severity='low',
				description=f"Analysis failed: {str(e)}"
			)

	def _extract_temporal_features(self, detections_list: List[List]) -> Dict:
		"""
		Extract temporal features from detection sequence
		"""
		if not detections_list:
			return {}

		features = {
			'vehicle_counts': [],
			'person_counts': [],
			'velocities': [],
			'trajectories': [],
			'bbox_areas': [],
			'collision_indicators': []
		}

		# Track objects across frames
		tracked_objects = self._track_objects(detections_list)

		for track_id, track in tracked_objects.items():
			if len(track['positions']) >= 2:
				# Calculate velocities
				velocities = []
				for i in range(1, len(track['positions'])):
					x1, y1 = track['positions'][i-1]
					x2, y2 = track['positions'][i]
					distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
					velocities.append(distance)

				features['velocities'].extend(velocities)
				features['trajectories'].append(track['positions'])
				features['bbox_areas'].extend(track['areas'])

				# Check for sudden velocity changes
				if len(velocities) >= 3:
					recent_avg = np.mean(velocities[-2:])
					prev_avg = np.mean(velocities[:-2])
					if prev_avg > self.velocity_threshold and recent_avg < self.velocity_threshold * 0.3:
						features['collision_indicators'].append('sudden_stop')

		# Count vehicles and persons per frame
		for detections in detections_list:
			vehicle_count = sum(1 for d in detections if getattr(d, 'is_vehicle', False))
			person_count = sum(1 for d in detections if getattr(d, 'class_name', '') == 'person')

			features['vehicle_counts'].append(vehicle_count)
			features['person_counts'].append(person_count)

		return features

	def _track_objects(self, detections_list: List[List]) -> Dict:
		"""
		Simple object tracking across frames
		"""
		tracks = {}
		next_track_id = 0

		for frame_idx, detections in enumerate(detections_list):
			for det in detections:
				# Get bounding box center
				if hasattr(det, 'bbox'):
					x, y, w, h = det.bbox
					center = (x + w // 2, y + h // 2)
					area = w * h
				else:
					center = (0, 0)
					area = 0

				# Find closest existing track
				matched_track_id = None
				min_distance = float('inf')

				for track_id, track in tracks.items():
					if frame_idx - track['last_seen'] > 3:  # Skip stale tracks
						continue

					if track['class_name'] != getattr(det, 'class_name', 'unknown'):
						continue

					last_pos = track['positions'][-1]
					distance = np.sqrt((center[0] - last_pos[0])**2 + 
									 (center[1] - last_pos[1])**2)

					if distance < 50 and distance < min_distance:  # Matching threshold
						min_distance = distance
						matched_track_id = track_id

				if matched_track_id is not None:
					# Update existing track
					tracks[matched_track_id]['positions'].append(center)
					tracks[matched_track_id]['areas'].append(area)
					tracks[matched_track_id]['last_seen'] = frame_idx
				else:
					# Create new track
					tracks[next_track_id] = {
						'positions': [center],
						'areas': [area],
						'class_name': getattr(det, 'class_name', 'unknown'),
						'last_seen': frame_idx
					}
					next_track_id += 1

		return tracks

	def _detect_collision(self, features: Dict) -> float:
		"""Detect vehicle collisions"""
		if 'collision_indicators' not in features:
			return 0.0

		collision_count = len([ind for ind in features['collision_indicators'] 
							 if 'sudden_stop' in ind])

		if collision_count > 0:
			return min(1.0, collision_count * 0.5)
		return 0.0

	def _detect_sudden_stop(self, features: Dict) -> float:
		"""Detect sudden stops"""
		if not features.get('velocities'):
			return 0.0

		velocities = features['velocities']
		if len(velocities) < 3:
			return 0.0

		recent_vel = np.mean(velocities[-2:]) if len(velocities) >= 2 else velocities[-1]
		avg_vel = np.mean(velocities)

		if avg_vel > self.velocity_threshold and recent_vel < avg_vel * 0.3:
			return 0.8
		elif avg_vel > self.velocity_threshold and recent_vel < avg_vel * 0.5:
			return 0.4

		return 0.0

	def _detect_abnormal_movement(self, features: Dict) -> float:
		"""Detect abnormal vehicle movement"""
		if not features.get('trajectories'):
			return 0.0

		abnormal_count = 0
		total_tracks = len(features['trajectories'])

		if total_tracks == 0:
			return 0.0

		for trajectory in features['trajectories']:
			if len(trajectory) >= 3:
				directions = []
				for i in range(1, len(trajectory)):
					x1, y1 = trajectory[i-1]
					x2, y2 = trajectory[i]
					angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
					directions.append(angle)

				for i in range(1, len(directions)):
					angle_change = abs(directions[i] - directions[i-1])
					if angle_change > self.abnormal_angle_threshold:
						abnormal_count += 1
						break

		return abnormal_count / total_tracks

	def _detect_multiple_vehicles(self, features: Dict) -> float:
		"""Detect multiple vehicles in close proximity"""
		if not features.get('vehicle_counts'):
			return 0.0

		recent_counts = features['vehicle_counts'][-3:] if len(features['vehicle_counts']) >= 3 else features['vehicle_counts']
		avg_recent = np.mean(recent_counts)

		if avg_recent >= 3:
			return 0.9
		elif avg_recent >= 2:
			return 0.6
		elif avg_recent >= 1:
			return 0.3

		return 0.0

	def _detect_pedestrian_involvement(self, features: Dict) -> float:
		"""Detect pedestrian involvement"""
		if not features.get('person_counts'):
			return 0.0

		recent_persons = features['person_counts'][-3:] if len(features['person_counts']) >= 3 else features['person_counts']
		recent_vehicles = features['vehicle_counts'][-3:] if len(features['vehicle_counts']) >= 3 else features['vehicle_counts']

		if any(p > 0 for p in recent_persons) and any(v > 0 for v in recent_vehicles):
			return 0.7

		return 0.0

	def _classify_accident_type(self, features: Dict) -> str:
		"""Classify the type of accident"""
		rule_scores = {}

		if self._detect_collision(features) > 0.5:
			rule_scores['collision'] = 1.0
		if self._detect_sudden_stop(features) > 0.5:
			rule_scores['sudden_stop'] = 1.0
		if self._detect_pedestrian_involvement(features) > 0.5:
			rule_scores['pedestrian'] = 1.0

		if 'pedestrian' in rule_scores:
			return 'pedestrian_accident'
		elif 'collision' in rule_scores:
			return 'vehicle_collision'
		elif 'sudden_stop' in rule_scores:
			return 'sudden_stop_incident'
		else:
			return 'traffic_incident'

	def _preprocess_frames(self, frames: List[np.ndarray]) -> 'torch.Tensor':
		"""
		Preprocess frames for model input
		"""
		if not TORCH_AVAILABLE:
			raise RuntimeError("PyTorch is required for model-based preprocessing")

		target_size = (64, 64)
		processed_frames = []

		for frame in frames:
			if len(frame.shape) == 3:
				gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
			else:
				gray = frame

			resized = cv2.resize(gray, target_size)
			normalized = resized.astype(np.float32) / 255.0
			processed_frames.append(normalized)

		tensor = torch.FloatTensor(processed_frames)
		tensor = tensor.unsqueeze(1)  # [seq_len, 1, H, W]
		tensor = tensor.unsqueeze(0)  # [1, seq_len, 1, H, W]
		return tensor

	def clear_buffer(self):
		"""Clear frame and detection buffers"""
		self.frame_buffer.clear()
		self.detection_buffer.clear()

	def get_buffer_status(self) -> Dict:
		"""Get buffer status"""
		return {
			'frame_buffer_size': len(self.frame_buffer),
			'detection_buffer_size': len(self.detection_buffer),
			'sequence_length': self.sequence_length,
			'buffer_full': len(self.frame_buffer) >= self.sequence_length
		}


if TORCH_AVAILABLE:
	class AccidentConvLSTM(nn.Module):
		"""
		ConvLSTM model for accident detection
		A compact architecture: per-frame encoder -> ConvLSTM -> global pool -> linear
		"""
		def __init__(self, input_channels: int = 1, hidden_dim: int = 16):
			super(AccidentConvLSTM, self).__init__()
			self.encoder = nn.Sequential(
				nn.Conv2d(input_channels, 8, kernel_size=3, padding=1),
				nn.ReLU(),
				nn.MaxPool2d(2),
				nn.Conv2d(8, 16, kernel_size=3, padding=1),
				nn.ReLU(),
				nn.MaxPool2d(2)
			)

			# ConvLSTM will operate on encoded features
			self.convlstm = ConvLSTM(input_dim=16, hidden_dim=hidden_dim, kernel_size=3)

			# Final classifier
			self.classifier = nn.Sequential(
				nn.AdaptiveAvgPool2d((1, 1)),
				nn.Flatten(),
				nn.Linear(hidden_dim, 1)
			)

		def forward(self, x: 'torch.Tensor') -> 'torch.Tensor':
			# x shape: [B, seq_len, 1, H, W]
			B, seq_len, c, H, W = x.shape
			# Merge batch and seq to encode frames
			x = x.view(B * seq_len, c, H, W)
			features = self.encoder(x)  # [B*seq, C, H', W']
			_, C, Hf, Wf = features.shape
			features = features.view(B, seq_len, C, Hf, Wf)

			# Initialize hidden state
			h, cstate = self.convlstm.init_hidden(B, (Hf, Wf))
			h = h.to(features.device)
			cstate = cstate.to(features.device)

			# Run ConvLSTM over sequence
			for t in range(seq_len):
				input_t = features[:, t, :, :, :]
				h, cstate = self.convlstm(input_t, (h, cstate))

			out = self.classifier(h)
			return out.squeeze(1)
else:
	# Dummy class when PyTorch is not available
	AccidentConvLSTM = None

