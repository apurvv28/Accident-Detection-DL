"""
Alert dispatcher with Text-to-Speech and optional Twilio integration.

Features:
- Uses pyttsx3 for Windows-compatible TTS playback (offline)
- Falls back to gTTS for file generation if needed
- Optional Twilio voice call for urgent alerts (if configured)
- Simple queuing and retry logic with cooldown management
"""
import os
import time
import threading
from typing import Dict, List, Optional
from queue import Queue, Empty
from ..utils.logger import setup_logger

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
		recipients = task.get('recipients', {})
		message = task.get('message', '')
		alert_id = task.get('alert_id')

		# Handle cooldown per recipient phone
		phone_numbers = recipients.get('phone_numbers', [])
		for phone in phone_numbers:
			last = self.last_alert_time.get(phone, 0)
			if time.time() - last < self.cooldown_seconds:
				logger.info(f"Skipping alert to {phone}: cooldown")
				continue

			sent = False

			# Try Twilio voice call if configured
			if self.twilio_client and recipients.get('use_twilio'):
				try:
					call = self.twilio_client.calls.create(
						twiml=f"<Response><Say>{message}</Say></Response>",
						to=phone,
						from_=os.getenv('TWILIO_FROM')
					)
					logger.info(f"Twilio call initiated: {call.sid}")
					sent = True
					self.last_alert_time[phone] = time.time()
				except Exception as e:
					logger.error(f"Twilio call failed for {phone}: {e}")

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

		# Optionally handle emails or SMS - omitted for brevity

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

	def queue_alert(self, message: str, recipients: Dict[str, List[str]], alert_id: Optional[str] = None):
		task = {
			'message': message,
			'recipients': recipients,
			'alert_id': alert_id
		}
		self.queue.put(task)

	def test_alert(self, message: str = "Test alert from Accident Detection System"):
		self.queue_alert(message, {'phone_numbers': [os.getenv('TEST_PHONE') or 'local']}, alert_id='test')

	# Convenience wrappers used by API
	def send_tts_alert(self, message: str, is_test: bool = False) -> Dict:
		"""Generate or play a TTS alert immediately (queues it)."""
		alert_id = f"tts_{int(time.time())}"
		self.queue_alert(message, {'phone_numbers': [os.getenv('TEST_PHONE') or 'local']}, alert_id=alert_id)
		return {'alert_id': alert_id, 'audio_file': None}

	def send_voice_alert(self, phone: str, message: str, is_test: bool = False) -> Dict:
		"""Trigger a voice alert to a phone number using Twilio if available."""
		task = {'message': message, 'recipients': {'phone_numbers': [phone], 'use_twilio': True}, 'alert_id': f"voice_{int(time.time())}"}
		self.queue.put(task)
		return {'call_sid': None}

	def send_sms_alert(self, phone: str, message: str, is_test: bool = False) -> Dict:
		"""Send SMS using Twilio if configured (queued)."""
		# For now we queue the task and rely on Twilio client in _send_now
		task = {'message': message, 'recipients': {'phone_numbers': [phone], 'use_twilio': True}, 'alert_id': f"sms_{int(time.time())}"}
		self.queue.put(task)
		return {'message_sid': None}

	def send_accident_alert(self, detection_data: Dict, camera_id: str):
		"""Helper to prepare and queue an accident alert using detection data."""
		message = f"Accident detected at camera {camera_id}. Confidence {detection_data.get('confidence', 0):.2f}. Please check the dashboard."
		recipients = {
			'phone_numbers': os.getenv('ALERT_PHONE_NUMBERS', '').split(',') if os.getenv('ALERT_PHONE_NUMBERS') else []
		}
		self.queue_alert(message, recipients, alert_id=f"acc_{int(time.time())}")

