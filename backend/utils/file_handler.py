"""File helper utilities for uploads and storage."""
import os
from werkzeug.datastructures import FileStorage
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'mp4,avi,mov,mkv').split(','))
UPLOAD_DIR = os.getenv('UPLOAD_DIR', os.path.join(os.getcwd(), 'uploads'))

os.makedirs(UPLOAD_DIR, exist_ok=True)


def allowed_file(filename: str) -> bool:
	if not filename or '.' not in filename:
		return False
	ext = filename.rsplit('.', 1)[1].lower()
	return ext in ALLOWED_EXTENSIONS


def save_uploaded_file(file: FileStorage, filename: str) -> str:
	path = os.path.join(UPLOAD_DIR, filename)
	file.save(path)
	logger.info(f"Saved uploaded file to {path}")
	return path

