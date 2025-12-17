"""Main Flask application for Accident Detection System."""
import os
import sys
import yaml
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent directory to Python path to allow imports when running from backend/
backend_dir = Path(__file__).parent
parent_dir = backend_dir.parent
if str(parent_dir) not in sys.path:
	sys.path.insert(0, str(parent_dir))

load_dotenv()

from backend.api import api_v1, socketio
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_app(config_path: str = 'config.yaml') -> Flask:
	app = Flask(__name__)
	CORS(app)

	# Default configuration
	app.config.update({
		'UPLOAD_DIR': os.getenv('UPLOAD_DIR', os.path.join(os.getcwd(), 'uploads')),
		'ALLOWED_EXTENSIONS': os.getenv('ALLOWED_EXTENSIONS', 'mp4,avi,mov,mkv').split(','),
		'MIN_CONFIDENCE': float(os.getenv('MIN_CONFIDENCE', 0.75)),
		'PROCESS_FPS': int(os.getenv('PROCESS_FPS', 2)),
		'TARGET_FPS': int(os.getenv('TARGET_FPS', 10)),
		'FRAME_SKIP': int(os.getenv('FRAME_SKIP', 3)),
		'DEFAULT_LATITUDE': float(os.getenv('DEFAULT_LATITUDE', 28.6139)),
		'DEFAULT_LONGITUDE': float(os.getenv('DEFAULT_LONGITUDE', 77.2090))
	})

	# Load YAML config if provided
	if os.path.exists(config_path):
		try:
			with open(config_path, 'r') as fh:
				cfg = yaml.safe_load(fh)
				app.config.update(cfg or {})
				logger.info(f"Loaded configuration from {config_path}")
		except Exception as e:
			logger.error(f"Failed to load config.yaml: {e}")

	# Register blueprints
	app.register_blueprint(api_v1)

	# Initialize WebSocket
	socketio.init_app(app, cors_allowed_origins='*')

	# Error handlers
	@app.errorhandler(404)
	def not_found(e):
		return jsonify({'status': 'error', 'message': 'Not found'}), 404

	@app.errorhandler(500)
	def internal_error(e):
		logger.exception(e)
		return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

	return app


if __name__ == '__main__':
	app = create_app()
	port = int(os.getenv('PORT', 5000))
	logger.info(f"Starting app on port {port}")
	socketio.run(app, host='0.0.0.0', port=port)

