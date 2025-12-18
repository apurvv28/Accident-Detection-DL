"""
Video Upload and Processing API Endpoints
"""
import os
import uuid
import cv2
import json
from datetime import datetime
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
import threading
import time

from ..services.video_processor import VideoStreamProcessor, frame_generator_from_file
from ..utils.video_utils import save_frames_as_video, convert_to_mp4
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

from collections import deque

def process_video_async(video_path, camera_id, metadata, process_fps=2, video_id=None):
    """
    Process video in background thread using video-level accident detection.
    
    Args:
        video_path: Path to the video file to process
        camera_id: ID of the camera that captured the video
        metadata: Additional metadata about the video
        process_fps: Frames per second to process
        video_id: Optional unique ID for tracking progress
    """
    # Initialize status tracking
    if video_id:
        if not hasattr(get_video_status, '_processing_status'):
            get_video_status._processing_status = {}
        get_video_status._processing_status[video_id] = {
            'status': 'in_progress',
            'progress': 0,
            'message': 'Starting video processing',
            'accident_detected': False
        }
    
    try:
        db = DatabaseManager()
        detector = AccidentDetector()
        alert = AlertDispatcher()
        
        # Video-level variables
        accident_detected = False
        max_confidence = 0.0
        max_severity = 0.0
        accident_frames = []
        accident_descriptions = set()
        involved_objects = set()
        frame_buffer = deque(maxlen=60)  # Store last 2 seconds of frames at 30fps
        accident_start_time = None
        
        # Get total frames for progress tracking
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        # Process each frame in the video
        for frame_idx, frame in enumerate(frame_generator_from_file(video_path, fps=process_fps)):
            if video_id and frame_idx % 10 == 0:  # Update progress every 10 frames
                progress = min(99, int((frame_idx / max(1, total_frames)) * 100))
                if not hasattr(get_video_status, '_processing_status'):
                    get_video_status._processing_status = {}
                get_video_status._processing_status[video_id].update({
                    'progress': progress,
                    'message': f'Processing frame {frame_idx} of ~{total_frames}'
                })
            
            frame_buffer.append(frame.copy())
            
            # Process frame through accident detector
            pred = detector.process_frame(frame, camera_id)
            
            # If accident detected in this frame
            if pred and pred.is_accident:
                if not accident_detected:  # First detection in this video
                    accident_detected = True
                    accident_start_time = datetime.now()
                    if video_id:
                        if not hasattr(get_video_status, '_processing_status'):
                            get_video_status._processing_status = {}
                        get_video_status._processing_status[video_id]['accident_detected'] = True
                
                # Track max confidence and severity
                max_confidence = max(max_confidence, pred.confidence)
                max_severity = max(max_severity, pred.severity)
                
                # Store accident frames (last 30 frames)
                accident_frames = list(frame_buffer)[-30:]
                
                # Collect unique descriptions
                if pred.description:
                    accident_descriptions.add(pred.description)
                
                # Collect involved objects
                if hasattr(pred, 'involved_tracks') and pred.involved_tracks:
                    involved_objects.update([f"track_{tid}" for tid in pred.involved_tracks])
        
        # After processing all frames, handle accident if detected
        if accident_detected and accident_frames:
            detection_id = f"det_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            accident_dir = os.path.join('static', 'accidents', detection_id)
            os.makedirs(accident_dir, exist_ok=True)
            
            # Save accident clip
            clip_path = os.path.join(accident_dir, 'clip.mp4')
            saved_path = save_frames_as_video(accident_frames, clip_path, fps=process_fps)
            if saved_path:
                converted_path = os.path.join(accident_dir, 'clip_h264.mp4')
                clip_path = convert_to_mp4(saved_path, converted_path)
            
            # Create detection data
            detection_data = {
                'detection_id': detection_id,
                'camera_id': camera_id,
                'timestamp': datetime.now(),
                'video_path': video_path,
                'accident_video_path': clip_path,
                'confidence': float(max_confidence),
                'involved_objects': list(involved_objects),
                'location': None,  # Can be enhanced with GPS data
                'is_accident': True,
                'severity': float(max_severity),
                'severity_percent': round(float(max_confidence) * 100.0, 1),
                'description': '; '.join(accident_descriptions) if accident_descriptions else "Accident detected",
                'metadata': metadata if isinstance(metadata, dict) else json.loads(metadata or '{}'),
                'duration_seconds': (datetime.now() - accident_start_time).total_seconds() if accident_start_time else 0,
                'processed_at': datetime.now()
            }
            
            # Save to database and trigger alert
            db.insert_detection(detection_data)
            alert.send_accident_alert(detection_data, camera_id)
            
            logger.info(f"Accident detected in {video_path}: {detection_data['description']}")
        
        # Update status to completed
        if video_id:
            if not hasattr(get_video_status, '_processing_status'):
                get_video_status._processing_status = {}
            get_video_status._processing_status[video_id].update({
                'status': 'completed',
                'progress': 100,
                'message': 'Processing completed',
                'accident_detected': accident_detected
            })
        
        logger.info(f"Video processing completed: {video_path}, Accidents detected: {1 if accident_detected else 0}")
        
    except Exception as e:
        logger.error(f"Video processing failed: {str(e)}", exc_info=True)
        if video_id:
            if not hasattr(get_video_status, '_processing_status'):
                get_video_status._processing_status = {}
            get_video_status._processing_status[video_id].update({
                'status': 'failed',
                'message': f'Error: {str(e)}'
            })

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
        
        # Get config values before starting thread (to avoid app context issues)
        process_fps = current_app.config.get('PROCESS_FPS', 2)
        
        # Start async processing
        threading.Thread(
            target=process_video_async,
            args=(video_path, camera_id, metadata, process_fps, unique_filename),
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
    # Initialize processing status if it doesn't exist
    if not hasattr(get_video_status, '_processing_status'):
        get_video_status._processing_status = {}
            
    try:
        status = get_video_status._processing_status.get(video_id, {
            'status': 'not_found',
            'message': 'Video ID not found',
            'progress': 0,
            'accident_detected': False
        })

        response_data = {
            'video_id': video_id,
            'processing_status': status.get('status', 'unknown'),
            'progress': status.get('progress', 0),
            'message': status.get('message', ''),
            'accident_detected': bool(status.get('accident_detected', False)),
            'accidents_detected': 1 if status.get('accident_detected', False) else 0,
        }
        
        # If processing is complete, check database for results
        if status.get('status') == 'completed':
            db = DatabaseManager()
            # Get the most recent detection for this video
            detection = db.get_detection_by_video(video_id)
            if detection:

                # Convert ObjectId to string for JSON serialization
                if '_id' in detection:
                    detection['_id'] = str(detection['_id'])
                # Convert datetime to string
                if 'timestamp' in detection and isinstance(detection['timestamp'], datetime):
                    detection['timestamp'] = detection['timestamp'].isoformat()
                response_data['detection'] = detection
        
        return jsonify({
            'status': 'success',
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"Error getting video status: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_v1.route('/video/<video_id>/status', methods=['GET'])
def get_video_status_alias(video_id):
    return get_video_status(video_id)

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