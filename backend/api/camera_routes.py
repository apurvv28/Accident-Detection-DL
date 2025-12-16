"""
Camera Management API Endpoints
"""
import json
import uuid
from datetime import datetime, timedelta
from flask import request, jsonify, current_app

from ..services.database_manager import DatabaseManager
from ..services.geolocation_service import GeolocationService
from ..utils.logger import setup_logger
from . import api_v1

logger = setup_logger(__name__)

@api_v1.route('/cameras', methods=['GET', 'POST'])
def manage_cameras():
    """
    Get all cameras or add new camera
    ---
    tags:
      - Cameras
    responses:
      200:
        description: List of cameras
      201:
        description: Camera created
    """
    try:
        db = DatabaseManager()
        
        if request.method == 'GET':
            # Get all cameras
            cameras = db.get_all_cameras()
            
            # Get status for each camera
            for camera in cameras:
                camera_id = camera.get('camera_id')
                # Check if camera has active inference
                from ..api.inference_routes import active_streams
                camera['inference_active'] = camera_id in active_streams
                
                # Get recent detections count
                detections_count = db.get_detections_count({'camera_id': camera_id, 'timestamp': {'$gte': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}})
                camera['detections_today'] = detections_count
            
            return jsonify({
                'status': 'success',
                'cameras': cameras,
                'total': len(cameras)
            }), 200
        
        elif request.method == 'POST':
            # Add new camera
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['camera_id', 'name', 'stream_url']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'status': 'error',
                        'message': f'Missing required field: {field}'
                    }), 400
            
            # Generate unique ID if not provided
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            # Set default values
            data['status'] = data.get('status', 'active')
            data['created_at'] = datetime.now()
            data['updated_at'] = datetime.now()
            
            # If location provided, verify it
            if 'location' in data:
                geolocation = GeolocationService()
                try:
                    # Verify coordinates are valid
                    lat = float(data['location'].get('latitude', 0))
                    lng = float(data['location'].get('longitude', 0))
                    
                    if lat == 0 and lng == 0:
                        # Try to geocode address if provided
                        if 'address' in data['location']:
                            geocoded = geolocation.geocode_address(data['location']['address'])
                            if geocoded:
                                data['location']['latitude'] = geocoded['latitude']
                                data['location']['longitude'] = geocoded['longitude']
                            else:
                                # Use default location
                                data['location']['latitude'] = current_app.config.get('DEFAULT_LATITUDE', 28.6139)
                                data['location']['longitude'] = current_app.config.get('DEFAULT_LONGITUDE', 77.2090)
                except ValueError:
                    return jsonify({
                        'status': 'error',
                        'message': 'Invalid location coordinates'
                    }), 400
            
            # Save camera
            try:
                camera_id = db.insert_camera(data)

                logger.info(f"Camera added: {data['camera_id']}")

                return jsonify({
                    'status': 'success',
                    'message': 'Camera added successfully',
                    'camera_id': data['camera_id'],
                    'id': camera_id
                }), 201
            except Exception as e:
                # Handle duplicate camera_id specially
                try:
                    from pymongo.errors import DuplicateKeyError
                    if isinstance(e, DuplicateKeyError) or 'duplicate key error' in str(e).lower():
                        return jsonify({
                            'status': 'error',
                            'message': f"Camera with id '{data.get('camera_id')}' already exists"
                        }), 409
                except Exception:
                    pass

                logger.error(f"Camera insertion failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to add camera: {str(e)}'
                }), 500
            
    except Exception as e:
        logger.error(f"Camera management error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Camera operation failed: {str(e)}'
        }), 500

@api_v1.route('/cameras/<camera_id>', methods=['GET', 'PUT', 'DELETE'])
def camera_detail(camera_id):
    """
    Get, update, or delete specific camera
    """
    try:
        db = DatabaseManager()
        
        if request.method == 'GET':
            # Get camera details
            camera = db.get_camera(camera_id)
            
            if not camera:
                return jsonify({
                    'status': 'error',
                    'message': f'Camera {camera_id} not found'
                }), 404
            
            # Get camera statistics
            detections_today = db.get_detections_count({
                'camera_id': camera_id,
                'timestamp': {'$gte': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            accidents_today = db.get_detections_count({
                'camera_id': camera_id,
                'is_accident': True,
                'timestamp': {'$gte': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            # Check if inference is active
            from ..api.inference_routes import active_streams
            inference_active = camera_id in active_streams
            
            camera['stats'] = {
                'detections_today': detections_today,
                'accidents_today': accidents_today,
                'inference_active': inference_active,
                'total_detections': db.get_detections_count({'camera_id': camera_id})
            }
            
            return jsonify({
                'status': 'success',
                'camera': camera
            }), 200
        
        elif request.method == 'PUT':
            # Update camera
            data = request.get_json()
            
            # Don't allow updating camera_id
            if 'camera_id' in data and data['camera_id'] != camera_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Cannot change camera_id'
                }), 400
            
            data['updated_at'] = datetime.now()
            
            success = db.update_camera(camera_id, data)
            
            if success:
                logger.info(f"Camera updated: {camera_id}")
                return jsonify({
                    'status': 'success',
                    'message': 'Camera updated successfully'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Camera not found or update failed'
                }), 404
        
        elif request.method == 'DELETE':
            # Delete camera
            # First check if camera has active inference
            from ..api.inference_routes import active_streams
            if camera_id in active_streams:
                return jsonify({
                    'status': 'error',
                    'message': 'Cannot delete camera with active inference. Stop inference first.'
                }), 400
            
            success = db.delete_camera(camera_id)
            
            if success:
                logger.info(f"Camera deleted: {camera_id}")
                return jsonify({
                    'status': 'success',
                    'message': 'Camera deleted successfully'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Camera not found'
                }), 404
                
    except Exception as e:
        logger.error(f"Camera detail error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Camera operation failed: {str(e)}'
        }), 500

@api_v1.route('/cameras/<camera_id>/test', methods=['POST'])
def test_camera(camera_id):
    """
    Test camera connection
    """
    try:
        db = DatabaseManager()
        camera = db.get_camera(camera_id)
        
        if not camera:
            return jsonify({
                'status': 'error',
                'message': f'Camera {camera_id} not found'
            }), 404
        
        stream_url = camera.get('stream_url')
        if not stream_url:
            return jsonify({
                'status': 'error',
                'message': 'Camera has no stream URL configured'
            }), 400
        
        # Test stream connection
        import cv2
        
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            return jsonify({
                'status': 'error',
                'message': 'Cannot open stream URL'
            }), 400
        
        # Try to read a frame
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Get frame info
            height, width = frame.shape[:2]
            
            return jsonify({
                'status': 'success',
                'message': 'Camera stream is accessible',
                'stream_url': stream_url,
                'frame_info': {
                    'width': width,
                    'height': height,
                    'channels': frame.shape[2] if len(frame.shape) > 2 else 1
                },
                'connection_test': 'passed'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Cannot read frames from stream'
            }), 400
            
    except Exception as e:
        logger.error(f"Camera test error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Camera test failed: {str(e)}'
        }), 500

@api_v1.route('/cameras/<camera_id>/detections', methods=['GET'])
def get_camera_detections(camera_id):
    """
    Get detections for specific camera
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        is_accident = request.args.get('is_accident')
        
        db = DatabaseManager()
        
        # Build query
        query = {'camera_id': camera_id}
        if is_accident is not None:
            query['is_accident'] = is_accident.lower() == 'true'
        
        detections = db.get_detections_paginated(query=query, page=page, limit=limit)
        total = db.get_detections_count(query)
        
        return jsonify({
            'status': 'success',
            'camera_id': camera_id,
            'detections': detections,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Camera detections error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get camera detections: {str(e)}'
        }), 500

@api_v1.route('/cameras/<camera_id>/stats', methods=['GET'])
def get_camera_stats(camera_id):
    """
    Get statistics for specific camera
    """
    try:
        days = int(request.args.get('days', 7))
        start_date = datetime.now() - timedelta(days=days)
        
        db = DatabaseManager()
        
        # Base query
        base_query = {'camera_id': camera_id}
        time_query = {'camera_id': camera_id, 'timestamp': {'$gte': start_date}}
        
        stats = {
            'total_detections': db.get_detections_count(base_query),
            'total_accidents': db.get_detections_count({**base_query, 'is_accident': True}),
            'detections_last_n_days': db.get_detections_count(time_query),
            'accidents_last_n_days': db.get_detections_count({**time_query, 'is_accident': True}),
            'daily_average': db.get_daily_average_detections(camera_id, days),
            'most_common_vehicle_types': db.get_most_common_vehicles(camera_id, limit=5),
            'peak_hours': db.get_peak_detection_hours(camera_id),
            'recent_activity': db.get_recent_detections(camera_id, limit=10)
        }
        
        return jsonify({
            'status': 'success',
            'camera_id': camera_id,
            'stats': stats,
            'period_days': days
        }), 200
        
    except Exception as e:
        logger.error(f"Camera stats error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get camera statistics: {str(e)}'
        }), 500