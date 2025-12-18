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
	socketio.init_app(app, cors_allowed_origins='*', async_mode='threading')
	
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
	
	# Check if port is available
	import socket
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		sock.bind(('0.0.0.0', port))
		sock.close()
	except OSError:
		logger.error(f"Port {port} is already in use. Please stop the other application or use a different port.")
		sys.exit(1)
	
	logger.info("=" * 60)
	logger.info(f"Starting Accident Detection System Backend")
	logger.info(f"Server will be available at http://localhost:{port}")
	logger.info(f"API endpoints available at http://localhost:{port}/api/v1")
	logger.info(f"WebSocket available at ws://localhost:{port}")
	logger.info("=" * 60)
	logger.info("Press CTRL+C to stop the server")
	logger.info("")
	
	# Print startup confirmation
	print("\n" + "=" * 60)
	print(f"✓ Server starting on port {port}")
	print(f"✓ API: http://localhost:{port}/api/v1")
	print(f"✓ Health: http://localhost:{port}/api/v1/system/health")
	print("=" * 60 + "\n")
	
	try:
		# Use threading mode for better compatibility
		socketio.run(
			app, 
			host='0.0.0.0', 
			port=port, 
			debug=False, 
			allow_unsafe_werkzeug=True, 
			log_output=True,
			use_reloader=False
		)
	except KeyboardInterrupt:
		logger.info("")
		logger.info("Server stopped by user")
	except Exception as e:
		logger.error(f"Server error: {e}")
		import traceback
		logger.error(traceback.format_exc())
		raise

