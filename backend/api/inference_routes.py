"""
Real-time Inference API Endpoints
"""
import json
import threading
import time
from datetime import datetime
from flask import request, jsonify, current_app

from ..services.accident_detector import AccidentDetector
from ..services.geolocation_service import GeoLocationService
from ..services.database_manager import DatabaseManager
from ..utils.logger import setup_logger
from . import api_v1, socketio

logger = setup_logger(__name__)

# Global inference instances
inference_instances = {}
active_streams = {}

class StreamProcessor:
    """Handle real-time stream processing"""
    
    def __init__(self, stream_url, camera_id):
        self.stream_url = stream_url
        self.camera_id = camera_id
        self.detector = AccidentDetector()
        self.geolocation = GeoLocationService()
        self.db = DatabaseManager()
        self.running = False
        self.thread = None
        
    def start(self):
        """Start processing stream"""
        if self.running:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._process_stream, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """Stop processing stream"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _process_stream(self):
        """Main stream processing loop"""
        import cv2
        import numpy as np
        
        cap = cv2.VideoCapture(self.stream_url)
        frame_count = 0
        
        # Get camera location
        camera_location = self.db.get_camera(self.camera_id)
        if not camera_location:
            logger.warning(f"No location data for camera {self.camera_id}")
            camera_location = {'latitude': current_app.config.get('DEFAULT_LATITUDE', 28.6139),
                              'longitude': current_app.config.get('DEFAULT_LONGITUDE', 77.2090)}
        
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                logger.error(f"Stream disconnected: {self.stream_url}")
                break
            
            frame_count += 1
            # Process every Nth frame (configurable)
            if frame_count % current_app.config.get('FRAME_SKIP', 3) != 0:
                continue
            
            try:
                # Run per-frame detection for dashboard visualization
                detections = self.detector.detector.detect(frame)

                prediction = self.detector.process_frame(frame)

                if prediction and prediction.is_accident:
                    logger.info(f"Accident detected on camera {self.camera_id}")

                    # derive location if possible (use camera location)
                    location = camera_location

                    detection_data = {
                        'detection_id': f"acc_{int(time.time())}_{self.camera_id}",
                        'camera_id': self.camera_id,
                        'timestamp': datetime.now(),
                        'confidence': prediction.confidence,
                        'bbox': None,
                        'vehicles_involved': prediction.features.get('trajectories') if getattr(prediction, 'features', None) else [],
                        'location': location,
                        'is_accident': True,
                        'stream_url': self.stream_url,
                        'frame_number': frame_count
                    }

                    # Save to database
                    self.db.insert_detection(detection_data)

                    # Emit WebSocket event
                    socketio.emit('accident_detected', {
                        'camera_id': self.camera_id,
                        'detection': detection_data,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Trigger alert if confidence high enough
                    if prediction.confidence >= current_app.config.get('MIN_CONFIDENCE', 0.75):
                        from ..services.alert_dispatcher import AlertDispatcher
                        alert = AlertDispatcher()
                        alert.send_accident_alert(detection_data, self.camera_id)
                
                # Emit frame with detections for dashboard
                if frame_count % 10 == 0:  # Send every 10th frame
                    # Convert frame to base64 for WebSocket
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_base64 = buffer.tobytes()
                    
                    socketio.emit('frame_update', {
                        'camera_id': self.camera_id,
                        'frame': frame_base64.decode('latin-1'),
                        'detections': detections,
                        'frame_count': frame_count,
                        'timestamp': time.time()
                    })
                
            except Exception as e:
                logger.error(f"Frame processing error: {str(e)}")
                continue
            
            # Control frame rate
            time.sleep(1 / current_app.config.get('TARGET_FPS', 10))
        
        cap.release()
        logger.info(f"Stream processing stopped: {self.stream_url}")

@api_v1.route('/inference/start', methods=['POST'])
def start_inference():
    """
    Start real-time inference on video stream
    ---
    tags:
      - Inference
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            stream_url:
              type: string
              required: true
            camera_id:
              type: string
              required: true
            model_config:
              type: object
    responses:
      200:
        description: Inference started successfully
    """
    try:
        data = request.get_json()
        stream_url = data.get('stream_url')
        camera_id = data.get('camera_id')
        
        if not stream_url or not camera_id:
            return jsonify({
                'status': 'error',
                'message': 'stream_url and camera_id are required'
            }), 400
        
        # Check if already running
        if camera_id in active_streams:
            return jsonify({
                'status': 'success',
                'message': 'Inference already running for this camera',
                'camera_id': camera_id
            }), 200
        
        # Create and start processor
        processor = StreamProcessor(stream_url, camera_id)
        if processor.start():
            active_streams[camera_id] = processor
            inference_instances[camera_id] = processor
            
            logger.info(f"Started inference for camera {camera_id} on stream {stream_url}")
            
            return jsonify({
                'status': 'success',
                'message': 'Inference started successfully',
                'camera_id': camera_id,
                'stream_url': stream_url,
                'start_time': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to start inference'
            }), 500
            
    except Exception as e:
        logger.error(f"Start inference error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to start inference: {str(e)}'
        }), 500

@api_v1.route('/inference/stop/<camera_id>', methods=['POST'])
def stop_inference(camera_id):
    """
    Stop real-time inference for a camera
    """
    try:
        if camera_id not in active_streams:
            return jsonify({
                'status': 'error',
                'message': f'No active inference for camera {camera_id}'
            }), 404
        
        processor = active_streams[camera_id]
        processor.stop()
        
        # Cleanup
        del active_streams[camera_id]
        if camera_id in inference_instances:
            del inference_instances[camera_id]
        
        logger.info(f"Stopped inference for camera {camera_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Inference stopped successfully',
            'camera_id': camera_id,
            'stop_time': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Stop inference error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to stop inference: {str(e)}'
        }), 500

@api_v1.route('/inference/status', methods=['GET'])
def get_inference_status():
    """
    Get status of all inference instances
    """
    try:
        status_list = []
        for camera_id, processor in active_streams.items():
            status_list.append({
                'camera_id': camera_id,
                'stream_url': processor.stream_url,
                'running': processor.running,
                'inference_active': True
            })
        
        return jsonify({
            'status': 'success',
            'active_streams': status_list,
            'total_active': len(status_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get status: {str(e)}'
        }), 500


@api_v1.route('/detections', methods=['GET'])
def list_detections():
    """List detections with pagination and optional filters"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        camera_id = request.args.get('camera_id')
        is_accident = request.args.get('is_accident')

        query = {}
        if camera_id:
            query['camera_id'] = camera_id
        if is_accident is not None:
            query['is_accident'] = is_accident.lower() == 'true'

        db = DatabaseManager()
        detections = db.get_detections_paginated(query=query, page=page, limit=limit)
        total = db.get_detections_count(query)

        return jsonify({
            'status': 'success',
            'detections': detections,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        logger.error(f"List detections error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_v1.route('/inference/detect', methods=['POST'])
def detect_accident():
    """
    Perform single frame accident detection
    """
    try:
        if 'frame' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No frame image provided'
            }), 400
        
        frame_file = request.files['frame']
        camera_id = request.form.get('camera_id', 'unknown')
        
        # Read image
        import cv2
        import numpy as np
        
        frame_data = frame_file.read()
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({
                'status': 'error',
                'message': 'Invalid image file'
            }), 400
        
        # Process frame using the streaming detector
        detector = AccidentDetector()
        prediction = detector.process_frame(frame)

        db = DatabaseManager()
        camera_location = db.get_camera(camera_id)
        if not camera_location:
            camera_location = {'latitude': current_app.config.get('DEFAULT_LATITUDE', 28.6139),
                              'longitude': current_app.config.get('DEFAULT_LONGITUDE', 77.2090)}

        response = {
            'status': 'success',
            'accident_detected': bool(prediction.is_accident) if prediction else False,
            'confidence': float(prediction.confidence) if prediction else 0.0,
            'camera_id': camera_id,
            'timestamp': datetime.now().isoformat()
        }

        if prediction and prediction.is_accident:
            geolocation = GeoLocationService()
            response['location'] = camera_location
            response['accident_details'] = {
                'type': prediction.accident_type,
                'severity': prediction.severity,
                'description': prediction.description,
                'features': prediction.features
            }

        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Single frame detection error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Detection failed: {str(e)}'
        }), 500