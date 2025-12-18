"""
Alert dispatcher with Text-to-Speech and optional Twilio integration.

Features:
- Uses pyttsx3 for Windows-compatible TTS playback (offline)
- Falls back to gTTS for file generation if needed
- Optional Twilio voice/SMS alerts (if configured)
- Simple queuing and retry logic with cooldown management
"""
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from queue import Queue, Empty
from ..utils.logger import setup_logger
from .database_manager import DatabaseManager

logger = setup_logger(__name__)

try:
	import pyttsx3
	PYTTSX3_AVAILABLE = True
except Exception:
	PYTTSX3_AVAILABLE = False
	logger.warning("pyttsx3 not available; TTS may be degraded")

try:
	from gtts import gTTS
	GTTS_AVAILABLE = True
except Exception:
	GTTS_AVAILABLE = False

try:
	from twilio.rest import Client as TwilioClient
	TWILIO_AVAILABLE = True
except Exception:
	TWILIO_AVAILABLE = False


class AlertDispatcher:
	"""Dispatch alerts as TTS audio or voice calls."""

	def __init__(self, cooldown_seconds: int = 60):
		self.cooldown_seconds = cooldown_seconds
		self.last_alert_time: Dict[str, float] = {}
		self.queue: "Queue[Dict]" = Queue()
		self._worker = threading.Thread(target=self._worker_loop, daemon=True)
		self._worker.start()

		# Twilio setup
		self.twilio_client = None
		if TWILIO_AVAILABLE and os.getenv('TWILIO_ACCOUNT_SID'):
			try:
				self.twilio_client = TwilioClient(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
			except Exception as e:
				logger.error(f"Failed to init Twilio client: {e}")

	def _worker_loop(self):
		while True:
			try:
				task = self.queue.get(timeout=1.0)
			except Empty:
				continue

			try:
				self._send_now(task)
			except Exception as e:
				logger.error(f"Failed to send alert task: {e}")
			finally:
				self.queue.task_done()

	def _send_now(self, task: Dict):
		recipients = task.get('recipients', {}) or {}
		message = task.get('message', '') or ''
		alert_id = task.get('alert_id')
		channel = task.get('channel', 'voice')  # 'voice' | 'sms' | 'tts'

		# Handle cooldown per recipient phone
		phone_numbers = recipients.get('phone_numbers', [])
		if not phone_numbers:
			phone_numbers = ['local']

		for phone in phone_numbers:
			last = self.last_alert_time.get(phone, 0)
			if time.time() - last < self.cooldown_seconds:
				logger.info(f"Skipping alert to {phone}: cooldown")
				continue

			sent = False

			use_twilio = (
				self.twilio_client is not None
				and recipients.get('use_twilio')
				and phone not in ('local', '')
			)

			# Try Twilio first (voice or SMS)
			if use_twilio:
				try:
					from_number = os.getenv('TWILIO_PHONE_NUMBER')
					if not from_number:
						logger.warning("TWILIO_PHONE_NUMBER not configured; skipping Twilio send")
					else:
						if channel == 'sms':
							msg = self.twilio_client.messages.create(
								body=message,
								to=phone,
								from_=from_number
							)
							logger.info(f"Twilio SMS sent: {msg.sid}")
						else:
							call = self.twilio_client.calls.create(
								twiml=f"<Response><Say>{message}</Say></Response>",
								to=phone,
								from_=from_number
							)
							logger.info(f"Twilio call initiated: {call.sid}")
						sent = True
						self.last_alert_time[phone] = time.time()
				except Exception as e:
					logger.error(f"Twilio delivery failed for {phone}: {e}")

			# Fallback: generate/play TTS locally
			if not sent:
				try:
					audio_path = self._produce_tts(message, alert_id)
					# For Windows, pyttsx3 speaks directly; we still return audio path
					logger.info(f"TTS generated at {audio_path}")
					sent = True
					self.last_alert_time[phone] = time.time()
				except Exception as e:
					logger.error(f"TTS failed for {phone}: {e}")

	def _produce_tts(self, text: str, alert_id: Optional[str] = None) -> str:
		"""Produce TTS audio and play it locally. Returns path to file if created."""
		filename = f"temp_alert_{alert_id or int(time.time())}.mp3"
		path = os.path.join(os.getenv('TEMP', '/tmp'), filename)

		if PYTTSX3_AVAILABLE:
			try:
				engine = pyttsx3.init()
				engine.say(text)
				engine.runAndWait()
				# pyttsx3 does not reliably produce mp3 files cross-platform; we return None
				return path
			except Exception as e:
				logger.error(f"pyttsx3 playback failed: {e}")

		if GTTS_AVAILABLE:
			tts = gTTS(text=text)
			tts.save(path)
			# try to play using platform default
			try:
				# simple playback using OS
				if os.name == 'nt':
					import subprocess
					subprocess.Popen(['powershell', '-c', f'(New-Object Media.SoundPlayer "{path}").PlaySync();'])
				else:
					import simpleaudio as sa
					wave_obj = sa.WaveObject.from_wave_file(path)
					wave_obj.play().wait_done()
			except Exception:
				logger.info("Could not play TTS file automatically; file saved")

			return path

		raise RuntimeError("No TTS backend available")

	def queue_alert(self, message: str, recipients: Dict[str, List[str]], alert_id: Optional[str] = None, channel: str = 'voice'):
		task = {
			'message': message,
			'recipients': recipients,
			'alert_id': alert_id,
			'channel': channel,
		}
		self.queue.put(task)

	def test_alert(self, message: str = "Test alert from Accident Detection System"):
		self.queue_alert(message, {'phone_numbers': [os.getenv('TEST_PHONE') or 'local']}, alert_id='test')

	# Convenience wrappers used by API
	def send_tts_alert(self, message: str, is_test: bool = False) -> Dict:
		"""Generate or play a TTS alert immediately (queues it)."""
		alert_id = f"tts_{int(time.time())}"
		self.queue_alert(
			message,
			{'phone_numbers': [os.getenv('TEST_PHONE') or 'local']},
			alert_id=alert_id,
			channel='tts',
		)
		return {'alert_id': alert_id, 'audio_file': None}

	def send_voice_alert(self, phone: str, message: str, is_test: bool = False) -> Dict:
		"""Trigger a voice alert to a phone number using Twilio if available."""
		task = {
			'message': message,
			'recipients': {'phone_numbers': [phone], 'use_twilio': True},
			'alert_id': f"voice_{int(time.time())}",
			'channel': 'voice',
		}
		self.queue.put(task)
		return {'call_sid': None}

	def send_sms_alert(self, phone: str, message: str, is_test: bool = False) -> Dict:
		"""Send SMS using Twilio if configured (queued)."""
		task = {
			'message': message,
			'recipients': {'phone_numbers': [phone], 'use_twilio': True},
			'alert_id': f"sms_{int(time.time())}",
			'channel': 'sms',
		}
		self.queue.put(task)
		return {'message_sid': None}

	def send_accident_alert(self, detection_data: Dict, camera_id: str):
		"""Helper to prepare and queue an accident alert using detection data."""
		severity = detection_data.get('severity', 0)
		severity_percent = detection_data.get('severity_percent', severity)
		confidence = detection_data.get('confidence', 0)

		# Normalise confidence into percentage for clearer thresholds
		try:
			conf_pct = float(confidence) * 100.0 if confidence <= 1 else float(confidence)
		except Exception:
			conf_pct = 0.0

		message = (
			f"ACCIDENT ALERT! Detected at camera {camera_id}. "
			f"Severity: {severity_percent:.1f}%. "
			f"Confidence: {conf_pct:.1f}%. "
			f"Please check the dashboard immediately."
		)
		
		env_numbers = os.getenv('ALERT_PHONE_NUMBERS', '')
		phone_numbers = [p.strip() for p in env_numbers.split(',')] if env_numbers else []
		phone_numbers = [p for p in phone_numbers if p]
		recipients = {
			'phone_numbers': phone_numbers
		}
		
		alert_id = f"acc_{int(time.time())}"
		# General notification (typically local TTS / speakers)
		self.queue_alert(message, recipients, alert_id=alert_id, channel='tts')
		# SMS notification (Twilio) to configured recipients
		if phone_numbers:
			for phone in phone_numbers:
				self.send_sms_alert(phone, message)
		else:
			logger.warning("ALERT_PHONE_NUMBERS not configured; skipping SMS send")
		
		# Emit WebSocket alert
		self._emit_websocket_alert(detection_data, camera_id)
		
		# Auto-alert authorities by SMS if any of the scores crosses 90%
		auto_threshold = max(severity_percent, severity, conf_pct)
		if auto_threshold >= 90:
			logger.warning(f"AUTO-ALERTING AUTHORITIES - Threshold {auto_threshold:.1f}%")
			for authority in ('police', 'ambulance', 'fire'):
				self.send_authority_alert(detection_data, authority)

			# Best-effort: mark detection as auto-alerted in DB so UI can reflect it
			try:
				detection_id = detection_data.get('detection_id')
				if detection_id:
					db = DatabaseManager()
					db.update_detection(
						detection_id,
						{
							'auto_alerted': True,
							'alert_sent': True,
							'alert_recipients': ['police', 'ambulance', 'fire'],
							'alert_sent_at': datetime.utcnow(),
						},
					)
			except Exception as e:
				logger.error(f"Failed to mark detection {detection_data.get('detection_id')} as auto-alerted: {e}")

	def _emit_websocket_alert(self, detection_data: Dict, camera_id: str):
		"""Emit real-time WebSocket alert to dashboard"""
		try:
			from ..api import socketio
			
			severity = detection_data.get('severity', 0)
			severity_percent = detection_data.get('severity_percent', severity)
			
			alert_payload = {
				'event_id': detection_data.get('detection_id', f"evt_{int(time.time())}"),
				'type': 'accident',
				'severity': severity,
				'severity_percent': severity_percent,
				'severity_level': self._get_severity_level(severity_percent),
				'message': f"Accident detected at camera {camera_id}",
				'camera_id': camera_id,
				'timestamp': detection_data.get('timestamp', time.strftime('%Y-%m-%dT%H:%M:%SZ')),
				'requires_action': severity_percent >= 70,
				'auto_alerted': severity_percent >= 90,
				'video_url': f"/api/v1/accidents/{detection_data.get('detection_id', '')}/video",
				'description': detection_data.get('description', ''),
				'location': detection_data.get('location')
			}
			
			socketio.emit('accident_alert', alert_payload, namespace='/')
			logger.info(f"WebSocket alert emitted: {alert_payload['event_id']}")
			
		except Exception as e:
			logger.error(f"Failed to emit WebSocket alert: {e}")

	def send_authority_alert(self, detection_data: Dict, authority_type: str):
		"""Send alert to specific authority (police, ambulance, fire)"""
		authority_contacts = {
			'police': os.getenv('POLICE_PHONE', ''),
			'ambulance': os.getenv('AMBULANCE_PHONE', ''),
			'fire': os.getenv('FIRE_PHONE', '')
		}
		
		phone = authority_contacts.get(authority_type, '')
		if not phone:
			logger.warning(f"No phone number configured for {authority_type}")
			return
		
		severity = detection_data.get('severity_percent', detection_data.get('severity', 0))
		camera_id = detection_data.get('camera_id', 'Unknown')
		location = detection_data.get('location', {})
		
		location_str = 'Unknown location'
		lat = None
		lng = None
		
		if isinstance(location, dict):
			location_str = location.get('address', location_str)
			lat = location.get('latitude', lat)
			lng = location.get('longitude', lng)
		
		if lat is None:
			try:
				lat = float(os.getenv('DEFAULT_LATITUDE')) if os.getenv('DEFAULT_LATITUDE') else None
			except Exception:
				lat = None
		if lng is None:
			try:
				lng = float(os.getenv('DEFAULT_LONGITUDE')) if os.getenv('DEFAULT_LONGITUDE') else None
			except Exception:
				lng = None
		
		coords_str = None
		maps_url = None
		if lat is not None and lng is not None:
			coords_str = f"{lat:.6f}, {lng:.6f}"
			maps_url = f"https://www.google.com/maps?q={lat:.6f},{lng:.6f}"
		
		message = (
			f"EMERGENCY {authority_type.upper()} ALERT! "
			f"Vehicle accident detected. "
			f"Severity: {severity:.1f}%. "
			f"Camera: {camera_id}. "
			f"Location: {location_str}. "
			f"Coordinates: {coords_str or 'N/A'}. "
			f"Map: {maps_url or 'N/A'}. "
			f"Immediate response required."
		)
		
		task = {
			'message': message,
			'recipients': {'phone_numbers': [phone], 'use_twilio': True},
			'alert_id': f"{authority_type}_{int(time.time())}",
			'channel': 'sms',
		}
		self.queue.put(task)
		logger.info(f"Alert queued for {authority_type}: {phone}")

	def _get_severity_level(self, severity: float) -> str:
		"""Convert severity percentage to level string"""
		if severity >= 90:
			return 'critical'
		elif severity >= 70:
			return 'high'
		elif severity >= 50:
			return 'medium'
		else:
			return 'low'

	def clear_cache(self):
		"""Clear cooldowns and pending queue (used by system restart API)."""
		self.last_alert_time.clear()
		with self.queue.mutex:
			self.queue.queue.clear()
		logger.info("Alert dispatcher cache cleared")

