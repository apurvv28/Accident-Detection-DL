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

from collections import deque


def process_video_async(video_path, camera_id, metadata, process_fps=2, video_id=None):
    """Process video in background thread using frame-by-frame processing."""
    # Initialize status tracking if needed
    if not hasattr(get_video_status, '_processing_status'):
        get_video_status._processing_status = {}
    
    if video_id:
        get_video_status._processing_status[video_id] = 'in_progress'
    
    try:
        db = DatabaseManager()
        detector = AccidentDetector()
        alert = AlertDispatcher()
        
        accident_count = 0

        # keep small rolling buffer to create clips on detection
        frame_buffer = deque(maxlen=32)

        for frame in frame_generator_from_file(video_path, fps=process_fps):
            # store frame in buffer
            frame_buffer.append(frame.copy())

            pred = detector.process_frame(frame)
            if pred and pred.is_accident:
                accident_count += 1

                # create a unique detection id
                detection_id = f"det_{int(time.time())}_{uuid.uuid4().hex[:8]}"

                # Try to get sequence frames/detections attached by detector
                seq_frames = None
                seq_dets = None
                if getattr(pred, 'features', None):
                    seq_frames = pred.features.get('sequence_frames')
                    seq_dets = pred.features.get('sequence_detections')

                # Fallback to recent buffer if sequence not present
                frames_to_save = seq_frames if seq_frames else list(frame_buffer)

                # Save annotated clip
                from ..utils.video_utils import save_annotated_clip

                accident_dir = os.path.join(os.getcwd(), 'uploads', 'processed', 'accidents')
                os.makedirs(accident_dir, exist_ok=True)
                clip_path = os.path.join(accident_dir, f"{detection_id}.mp4")

                try:
                    saved_path = save_annotated_clip(frames_to_save, seq_dets, clip_path, fps=process_fps)
                except Exception as e:
                    logger.error(f"Failed to save annotated clip for {detection_id}: {e}")
                    saved_path = None

                # Determine involved objects
                involved_objects = []
                try:
                    if seq_dets:
                        for frame_dets in seq_dets:
                            for d in frame_dets:
                                cls = getattr(d, 'class_name', getattr(d, 'class', None))
                                if cls and cls not in involved_objects:
                                    involved_objects.append(cls)
                except Exception:
                    pass

                # Derive camera location if available
                camera_info = db.get_camera(camera_id) or {}
                location = camera_info.get('location') if isinstance(camera_info, dict) else None

                detection_data = {
                    'detection_id': detection_id,
                    'camera_id': camera_id,
                    'timestamp': datetime.now(),
                    'video_path': video_path,
                    'accident_video_path': saved_path,
                    'confidence': pred.confidence,
                    'bbox': None,
                    'vehicles_involved': pred.features.get('trajectories') if getattr(pred, 'features', None) else [],
                    'involved_objects': involved_objects,
                    'location': location,
                    'is_accident': True,
                    'severity': pred.severity,
                    'severity_percent': round(float(pred.confidence) * 100.0, 1) if pred.confidence is not None else None,
                    'description': pred.description,
                    'metadata': metadata
                }

                db.insert_detection(detection_data)
                alert.send_accident_alert(detection_data, camera_id)

        logger.info(f"Video processing completed: {video_path}, Accidents detected: {accident_count}")
        
        if video_id:
            get_video_status._processing_status[video_id] = 'completed'

    except Exception as e:
        logger.error(f"Video processing failed: {str(e)}")
        if video_id:
            get_video_status._processing_status[video_id] = 'failed'

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

@api_v1.route('/video/<video_id>/status', methods=['GET'])
def get_video_status(video_id):
    """
    Get processing status of uploaded video
    """
    try:
        # Store processing status in a simple in-memory dict
        # In production, you might want to use Redis or database
        if not hasattr(get_video_status, '_processing_status'):
            get_video_status._processing_status = {}
        
        db = DatabaseManager()
        
        # Check if we have any detections for this video
        detections = db.get_detections_paginated(
            query={'video_path': {'$regex': video_id}},
            page=1,
            limit=1
        )
        
        # Determine status based on detections
        if detections:
            processing_status = 'completed'
            accidents_count = db.get_detections_count({
                'video_path': {'$regex': video_id},
                'is_accident': True
            })
            total_detections = db.get_detections_count({
                'video_path': {'$regex': video_id}
            })
        else:
            # Check in-memory status first
            if video_id in get_video_status._processing_status:
                processing_status = get_video_status._processing_status[video_id]
            else:
                # If no detections yet, assume still processing
                processing_status = 'in_progress'
            accidents_count = 0
            total_detections = 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'video_id': video_id,
                'processing_status': processing_status,
                'detections_count': total_detections,
                'accidents_detected': accidents_count
            }
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