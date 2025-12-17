"""
Video Upload and Processing API Endpoints
"""
import os
import uuid
from datetime import datetime
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
import threading
import time

from ..services.video_processor import VideoStreamProcessor, frame_generator_from_file
from ..services.database_manager import DatabaseManager
from ..utils.file_handler import allowed_file, save_uploaded_file
from ..services.accident_detector import AccidentDetector
from ..services.alert_dispatcher import AlertDispatcher
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Register routes with blueprint
from . import api_v1

def get_or_create_default_camera(db, default_lat=28.6139, default_lng=77.2090):
    """Get or create default camera for video uploads."""
    DEFAULT_CAMERA_ID = 'default_upload_camera'
    
    # Try to get existing default camera
    camera = db.get_camera(DEFAULT_CAMERA_ID)
    if camera:
        return DEFAULT_CAMERA_ID
    
    # Create default camera if it doesn't exist
    default_camera_data = {
        'camera_id': DEFAULT_CAMERA_ID,
        'name': 'Default Upload Camera',
        'stream_url': 'N/A - Video Upload Only',
        'status': 'active',
        'location': {
            'latitude': default_lat,
            'longitude': default_lng,
            'address': 'Video Upload System'
        },
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    try:
        db.insert_camera(default_camera_data)
        logger.info(f"Created default camera: {DEFAULT_CAMERA_ID}")
        return DEFAULT_CAMERA_ID
    except Exception as e:
        logger.warning(f"Failed to create default camera, using ID anyway: {e}")
        return DEFAULT_CAMERA_ID

def process_video_async(video_path, camera_id, metadata):
    """Process video in background thread using frame-by-frame processing."""
    try:
        db = DatabaseManager()
        detector = AccidentDetector()
        alert = AlertDispatcher()
        
        accident_count = 0

        for frame in frame_generator_from_file(video_path, fps=current_app.config.get('PROCESS_FPS', 2)):
            pred = detector.process_frame(frame)
            if pred and pred.is_accident:
                accident_count += 1
                detection_data = {
                    'detection_id': f"det_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                    'camera_id': camera_id,
                    'timestamp': datetime.now(),
                    'video_path': video_path,
                    'confidence': pred.confidence,
                    'bbox': None,
                    'vehicles_involved': pred.features.get('trajectories') if getattr(pred, 'features', None) else [],
                    'is_accident': True,
                    'severity': pred.severity,
                    'description': pred.description,
                    'metadata': metadata
                }
                db.insert_detection(detection_data)
                alert.send_accident_alert(detection_data, camera_id)

        logger.info(f"Video processing completed: {video_path}, Accidents detected: {accident_count}")

    except Exception as e:
        logger.error(f"Video processing failed: {str(e)}")

@api_v1.route('/video/upload', methods=['POST'])
def upload_video():
    """
    Upload CCTV video for processing
    ---
    tags:
      - Video
    consumes:
      - multipart/form-data
    parameters:
      - name: video
        in: formData
        type: file
        required: true
        description: CCTV video file
      - name: metadata
        in: formData
        type: string
        required: false
        description: JSON metadata about the video
    responses:
      200:
        description: Video uploaded successfully
      400:
        description: Invalid file or missing parameters
    """
    try:
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No video file provided'
            }), 400
        
        file = request.files['video']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # Get metadata
        metadata = request.form.get('metadata', '{}')
        
        # Get camera_id from request (static camera_id sent from frontend)
        camera_id = request.form.get('camera_id', 'default_upload_camera')
        
        # Ensure default camera exists in database
        db = DatabaseManager()
        default_lat = current_app.config.get('DEFAULT_LATITUDE', 28.6139)
        default_lng = current_app.config.get('DEFAULT_LONGITUDE', 77.2090)
        # This ensures the camera exists, but we use the camera_id from request
        get_or_create_default_camera(db, default_lat, default_lng)
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': f'File type not allowed. Allowed types: {current_app.config.get("ALLOWED_EXTENSIONS", ["mp4", "avi", "mov", "mkv"])}'
            }), 400
        
        # Secure filename and save
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Save file
        video_path = save_uploaded_file(file, unique_filename)
        
        # Start async processing
        threading.Thread(
            target=process_video_async,
            args=(video_path, camera_id, metadata),
            daemon=True
        ).start()
        
        logger.info(f"Video uploaded: {filename} for camera: {camera_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Video uploaded and processing started',
            'video_id': unique_filename,
            'camera_id': camera_id,
            'processing_status': 'in_progress',
            'camera_name': 'Default Upload Camera'
        }), 200
        
    except Exception as e:
        logger.error(f"Video upload error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500

@api_v1.route('/video/status/<video_id>', methods=['GET'])
def get_video_status(video_id):
    """
    Get processing status of uploaded video
    """
    try:
        db = DatabaseManager()
        detection = db.get_detection_by_video(video_id)
        
        if not detection:
            return jsonify({
                'status': 'error',
                'message': 'Video not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'video_id': video_id,
            'processing_status': detection.get('status', 'unknown'),
            'detections_count': len(detection.get('detections', [])),
            'accidents_detected': sum(1 for d in detection.get('detections', []) if d.get('is_accident', False))
        }), 200
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Status check failed: {str(e)}'
        }), 500

@api_v1.route('/video/list', methods=['GET'])
def list_videos():
    """
    List all processed videos
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        db = DatabaseManager()
        videos = db.get_videos_paginated(page=page, limit=limit)
        total = db.get_videos_count()
        
        return jsonify({
            'status': 'success',
            'videos': videos,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"List videos error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to list videos: {str(e)}'
        }), 500