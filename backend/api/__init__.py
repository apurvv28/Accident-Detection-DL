"""
API Package Initialization
"""
from flask import Blueprint
from flask_socketio import SocketIO

# Create Blueprint for API v1
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Initialize WebSocket
socketio = SocketIO(cors_allowed_origins="*")

# Import all routes
from . import video_routes, inference_routes, alert_routes, camera_routes, dashboard_routes, system_api

__all__ = ['api_v1', 'socketio']