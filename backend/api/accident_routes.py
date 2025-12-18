"""
Accident Detection API Endpoints
"""
import os
from datetime import datetime
from flask import request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from . import api_v1
from ..services.database_manager import DatabaseManager
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@api_v1.route('/accidents', methods=['GET'])
def get_accidents():
    """
    Get list of detected accidents
    ---
    tags:
      - Accidents
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: limit
        in: query
        type: integer
        default: 20
      - name: severity_min
        in: query
        type: number
        description: Minimum severity filter (0-100)
      - name: status
        in: query
        type: string
        description: Filter by status (detected, verified, false_alarm, resolved)
      - name: camera_id
        in: query
        type: string
        description: Filter by camera
      - name: start_date
        in: query
        type: string
        description: Filter from date (ISO format)
      - name: end_date
        in: query
        type: string
        description: Filter to date (ISO format)
    responses:
      200:
        description: List of accidents
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        severity_min = request.args.get('severity_min', type=float)
        status = request.args.get('status')
        camera_id = request.args.get('camera_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        db = DatabaseManager()
        
        # Build query
        query = {'is_accident': True}
        
        if severity_min is not None:
            query['severity'] = {'$gte': severity_min}
        
        if status:
            query['status'] = status
            
        if camera_id:
            query['camera_id'] = camera_id
            
        if start_date or end_date:
            query['timestamp'] = {}
            if start_date:
                query['timestamp']['$gte'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                query['timestamp']['$lte'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Get accidents (stored as detections with is_accident=True)
        # Note: results are sorted by timestamp descending by default in mongodb_connector
        accidents = db.get_detections_paginated(
            query=query,
            page=page,
            limit=limit
        )
        
        total = db.get_detections_count(query)
        
        # Format response
        formatted_accidents = []
        for acc in accidents:
            formatted_accidents.append({
                'id': acc.get('detection_id', str(acc.get('_id', ''))),
                'timestamp': acc.get('timestamp', datetime.now()).isoformat() if acc.get('timestamp') else None,
                'camera_id': acc.get('camera_id'),
                'severity': acc.get('severity', 0),
                'severity_percent': acc.get('severity_percent', 0),
                'severity_level': _get_severity_level(acc.get('severity', 0)),
                'accident_type': acc.get('accident_type', 'unknown'),
                'description': acc.get('description', ''),
                'location': acc.get('location'),
                'involved_vehicles': len(acc.get('vehicles_involved', [])) or acc.get('vehicles_involved_count', 0),
                'confidence': acc.get('confidence', 0),
                'status': acc.get('status', 'detected'),
                'video_url': f"/api/v1/accidents/{acc.get('detection_id', '')}/video" if acc.get('accident_video_path') else None,
                'thumbnail_url': f"/api/v1/accidents/{acc.get('detection_id', '')}/thumbnail" if acc.get('thumbnail_path') else None,
                'alert_sent': acc.get('alert_sent', False),
                'auto_alerted': acc.get('auto_alerted', False)
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'accidents': formatted_accidents,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit if limit > 0 else 0
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting accidents: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_v1.route('/accidents/<accident_id>', methods=['GET'])
def get_accident(accident_id):
    """
    Get single accident details
    """
    try:
        db = DatabaseManager()
        accident = db.get_detection(accident_id)
        
        if not accident:
            return jsonify({
                'status': 'error',
                'message': 'Accident not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': accident.get('detection_id', str(accident.get('_id', ''))),
                'timestamp': accident.get('timestamp', datetime.now()).isoformat() if accident.get('timestamp') else None,
                'camera_id': accident.get('camera_id'),
                'severity': accident.get('severity', 0),
                'severity_percent': accident.get('severity_percent', 0),
                'severity_level': _get_severity_level(accident.get('severity', 0)),
                'accident_type': accident.get('accident_type', 'unknown'),
                'description': accident.get('description', ''),
                'location': accident.get('location'),
                'involved_vehicles': accident.get('vehicles_involved', []),
                'involved_objects': accident.get('involved_objects', []),
                'confidence': accident.get('confidence', 0),
                'status': accident.get('status', 'detected'),
                'video_path': accident.get('accident_video_path'),
                'video_url': f"/api/v1/accidents/{accident_id}/video" if accident.get('accident_video_path') else None,
                'thumbnail_url': f"/api/v1/accidents/{accident_id}/thumbnail" if accident.get('thumbnail_path') else None,
                'alert_sent': accident.get('alert_sent', False),
                'alert_recipients': accident.get('alert_recipients', []),
                'auto_alerted': accident.get('auto_alerted', False),
                'metadata': accident.get('metadata')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting accident {accident_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_v1.route('/accidents/<accident_id>/video', methods=['GET'])
def get_accident_video(accident_id):
    """
    Get accident video clip
    """
    try:
        db = DatabaseManager()
        accident = db.get_detection(accident_id)
        
        if not accident:
            return jsonify({
                'status': 'error',
                'message': 'Accident not found'
            }), 404
        
        video_path = accident.get('accident_video_path')
        
        if not video_path or not os.path.exists(video_path):
            return jsonify({
                'status': 'error',
                'message': 'Video not found'
            }), 404
        
        return send_file(
            video_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=f"accident_{accident_id}.mp4"
        )
        
    except Exception as e:
        logger.error(f"Error getting accident video {accident_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_v1.route('/accidents/<accident_id>/thumbnail', methods=['GET'])
def get_accident_thumbnail(accident_id):
    """
    Get accident thumbnail image
    """
    try:
        db = DatabaseManager()
        accident = db.get_detection(accident_id)
        
        if not accident:
            return jsonify({
                'status': 'error',
                'message': 'Accident not found'
            }), 404
        
        thumb_path = accident.get('thumbnail_path')
        
        if not thumb_path or not os.path.exists(thumb_path):
            # Try to generate from video path
            video_path = accident.get('accident_video_path')
            if video_path and os.path.exists(video_path):
                # Return a placeholder or generate thumbnail
                pass
            return jsonify({
                'status': 'error',
                'message': 'Thumbnail not found'
            }), 404
        
        return send_file(
            thumb_path,
            mimetype='image/jpeg',
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error getting accident thumbnail {accident_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_v1.route('/accidents/<accident_id>/status', methods=['PATCH'])
def update_accident_status(accident_id):
    """
    Update accident status (verified, false_alarm, resolved)
    """
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['detected', 'verified', 'false_alarm', 'resolved']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid status. Must be: detected, verified, false_alarm, resolved'
            }), 400
        
        db = DatabaseManager()
        result = db.update_detection(accident_id, {'status': new_status})
        
        if result:
            return jsonify({
                'status': 'success',
                'message': f'Status updated to {new_status}'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Accident not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error updating accident status {accident_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_v1.route('/accidents/<accident_id>/alert', methods=['POST'])
def send_accident_alert(accident_id):
    """
    Manually send alert for an accident to authorities
    """
    try:
        data = request.get_json() or {}
        recipients = data.get('recipients', ['police', 'ambulance', 'fire'])
        
        db = DatabaseManager()
        accident = db.get_detection(accident_id)
        
        if not accident:
            return jsonify({
                'status': 'error',
                'message': 'Accident not found'
            }), 404
        
        # Import and use alert dispatcher
        from ..services.alert_dispatcher import AlertDispatcher
        alert_service = AlertDispatcher()
        
        # Send alerts
        sent_to = []
        for recipient in recipients:
            try:
                alert_service.send_authority_alert(accident, recipient)
                sent_to.append(recipient)
            except Exception as e:
                logger.error(f"Failed to send alert to {recipient}: {e}")
        
        # Update accident record
        db.update_detection(accident_id, {
            'alert_sent': True,
            'alert_recipients': sent_to,
            'alert_sent_at': datetime.now()
        })
        
        return jsonify({
            'status': 'success',
            'message': f'Alerts sent to: {", ".join(sent_to)}',
            'sent_to': sent_to
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending alert for {accident_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@api_v1.route('/accidents/stats', methods=['GET'])
def get_accident_stats():
    """
    Get accident statistics
    """
    try:
        db = DatabaseManager()
        
        # Get total accidents
        total = db.get_detections_count({'is_accident': True})
        
        # Get by severity
        critical = db.get_detections_count({'is_accident': True, 'severity': {'$gte': 90}})
        high = db.get_detections_count({'is_accident': True, 'severity': {'$gte': 70, '$lt': 90}})
        medium = db.get_detections_count({'is_accident': True, 'severity': {'$gte': 50, '$lt': 70}})
        low = db.get_detections_count({'is_accident': True, 'severity': {'$lt': 50}})
        
        # Get by status
        detected = db.get_detections_count({'is_accident': True, 'status': 'detected'})
        verified = db.get_detections_count({'is_accident': True, 'status': 'verified'})
        resolved = db.get_detections_count({'is_accident': True, 'status': 'resolved'})
        false_alarms = db.get_detections_count({'is_accident': True, 'status': 'false_alarm'})
        
        # Auto-alerted count
        auto_alerted = db.get_detections_count({'is_accident': True, 'auto_alerted': True})
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total,
                'by_severity': {
                    'critical': critical,
                    'high': high,
                    'medium': medium,
                    'low': low
                },
                'by_status': {
                    'detected': detected,
                    'verified': verified,
                    'resolved': resolved,
                    'false_alarm': false_alarms
                },
                'auto_alerted': auto_alerted
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting accident stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def _get_severity_level(severity: float) -> str:
    """Convert severity percentage to level string"""
    if severity >= 90:
        return 'critical'
    elif severity >= 70:
        return 'high'
    elif severity >= 50:
        return 'medium'
    else:
        return 'low'

