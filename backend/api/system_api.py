"""
System Health and Management API Endpoints
"""
import os
import sys
import json
from datetime import datetime
from flask import request, jsonify, current_app

from ..utils.logger import setup_logger
from ..services.database_manager import DatabaseManager
from . import api_v1

logger = setup_logger(__name__)

@api_v1.route('/system/health', methods=['GET'])
def system_health():
    """
    Get system health status
    ---
    tags:
      - System
    responses:
      200:
        description: System health information
    """
    try:
        import psutil
        import socket
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        # Application info
        app_info = {
            'name': 'Accident Detection System',
            'version': '1.0.0',
            'environment': current_app.config.get('FLASK_ENV', 'production'),
            'debug_mode': current_app.config.get('DEBUG', False)
        }
        
        # Database health
        db = DatabaseManager()
        db_connected = db.test_connection()
        
        # Services status
        from ..api.inference_routes import active_streams
        from ..services.accident_detector import AccidentDetector
        
        services_status = {
            'database': 'connected' if db_connected else 'disconnected',
            'ai_model': 'available' if AccidentDetector().model_loaded() else 'unavailable',
            'active_streams': len(active_streams),
            'alert_system': 'enabled' if current_app.config.get('ENABLE_VOICE_ALERTS') or current_app.config.get('TWILIO_ACCOUNT_SID') else 'disabled'
        }
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'system': {
                'hostname': hostname,
                'ip_address': ip_address,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / 1024 / 1024 / 1024, 2),
                'memory_total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                'uptime_seconds': int(psutil.boot_time()),
                'python_version': sys.version
            },
            'application': app_info,
            'services': services_status,
            'checks': {
                'database': db_connected,
                'model_loaded': AccidentDetector().model_loaded(),
                'config_loaded': bool(current_app.config)
            }
        }
        
        # Determine overall health
        if not db_connected:
            health_status['status'] = 'degraded'
            health_status['issues'] = ['Database connection failed']
        
        # Return in format expected by frontend (flattened structure)
        return jsonify({
            'status': 'success',
            'data': {
                'status': health_status['status'],
                'database': services_status['database'],
                'models_loaded': services_status['ai_model'] == 'available',
                'system': health_status['system'],
                'application': health_status['application'],
                'services': services_status
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'message': 'Health check failed'
        }), 500

@api_v1.route('/system/logs', methods=['GET'])
def get_system_logs():
    """
    Get system logs
    """
    try:
        level = request.args.get('level', 'INFO')
        limit = int(request.args.get('limit', 100))
        since = request.args.get('since')
        
        db = DatabaseManager()
        
        query = {}
        if level != 'ALL':
            query['level'] = level.upper()
        
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query['timestamp'] = {'$gte': since_dt}
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid since parameter format. Use ISO format.'
                }), 400
        
        logs = db.get_system_logs(query=query, limit=limit)
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'count': len(logs),
            'parameters': {
                'level': level,
                'limit': limit,
                'since': since
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get logs error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get logs: {str(e)}'
        }), 500

@api_v1.route('/system/config', methods=['GET'])
def get_system_config():
    """
    Get current system configuration (safe version)
    """
    try:
        # Only return safe configuration values
        safe_config = {
            'application': {
                'name': 'Accident Detection System',
                'environment': current_app.config.get('FLASK_ENV'),
                'debug': current_app.config.get('DEBUG'),
                'secret_key_set': bool(current_app.config.get('SECRET_KEY')),
                'upload_folder': current_app.config.get('UPLOAD_FOLDER'),
                'max_upload_size': current_app.config.get('MAX_UPLOAD_SIZE')
            },
            'ai': {
                'detection_confidence': current_app.config.get('DETECTION_CONFIDENCE'),
                'min_confidence': current_app.config.get('MIN_CONFIDENCE'),
                'frame_rate': current_app.config.get('FRAME_RATE'),
                'inference_device': current_app.config.get('INFERENCE_DEVICE')
            },
            'alerts': {
                'enable_voice_alerts': current_app.config.get('ENABLE_VOICE_ALERTS'),
                'cooldown_minutes': current_app.config.get('ALERT_COOLDOWN_MINUTES'),
                'tts_engine': current_app.config.get('TTS_ENGINE')
            },
            'database': {
                'connected': True,
                'database_name': current_app.config.get('MONGODB_DB')
            }
        }
        
        return jsonify({
            'status': 'success',
            'config': safe_config
        }), 200
        
    except Exception as e:
        logger.error(f"Get config error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get configuration: {str(e)}'
        }), 500

@api_v1.route('/system/restart', methods=['POST'])
def restart_system():
    """
    Restart system services (admin only)
    """
    try:
        # Check for admin token
        admin_token = request.headers.get('X-Admin-Token')
        expected_token = current_app.config.get('ADMIN_TOKEN')
        
        if not expected_token or admin_token != expected_token:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized: Admin token required'
            }), 401
        
        service = request.args.get('service', 'all')
        
        restart_info = {
            'status': 'success',
            'message': f'Restart initiated for {service}',
            'timestamp': datetime.now().isoformat(),
            'restarted_services': []
        }
        
        # Restart specific service
        if service == 'inference' or service == 'all':
            from ..api.inference_routes import active_streams
            
            # Stop all active streams
            for camera_id, processor in list(active_streams.items()):
                processor.stop()
                restart_info['restarted_services'].append(f'inference:{camera_id}')
            
            active_streams.clear()
        
        if service == 'alert' or service == 'all':
            # Clear alert cache
            from ..services.alert_dispatcher import AlertDispatcher
            alert = AlertDispatcher()
            alert.clear_cache()
            restart_info['restarted_services'].append('alert_system')
        
        if service == 'database' or service == 'all':
            # Reconnect database
            db = DatabaseManager()
            db.reconnect()
            restart_info['restarted_services'].append('database')
        
        logger.info(f"System restart initiated for {service}")
        
        return jsonify(restart_info), 200
        
    except Exception as e:
        logger.error(f"Restart error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Restart failed: {str(e)}'
        }), 500

@api_v1.route('/system/cleanup', methods=['POST'])
def cleanup_system():
    """
    Cleanup temporary files and old data
    """
    try:
        # Check for admin token
        admin_token = request.headers.get('X-Admin-Token')
        expected_token = current_app.config.get('ADMIN_TOKEN')
        
        if not expected_token or admin_token != expected_token:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized: Admin token required'
            }), 401
        
        cleanup_type = request.args.get('type', 'temp')
        days_old = int(request.args.get('days', 7))
        
        cleanup_info = {
            'status': 'success',
            'message': f'Cleanup initiated for {cleanup_type}',
            'timestamp': datetime.now().isoformat(),
            'cleaned_items': []
        }
        
        import os
        import shutil
        from datetime import datetime, timedelta
        
        if cleanup_type in ['temp', 'all']:
            # Clean temp folder
            temp_folder = current_app.config.get('TEMP_FOLDER', 'temp')
            if os.path.exists(temp_folder):
                cutoff_time = datetime.now() - timedelta(days=days_old)
                
                for root, dirs, files in os.walk(temp_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_time:
                            try:
                                os.remove(file_path)
                                cleanup_info['cleaned_items'].append(f'temp:{file_path}')
                            except:
                                pass
            
            # Clean audio cache
            audio_folder = current_app.config.get('AUDIO_FOLDER', 'static/audio')
            if os.path.exists(audio_folder):
                for file in os.listdir(audio_folder):
                    if file.endswith('.mp3'):
                        file_path = os.path.join(audio_folder, file)
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_time:
                            try:
                                os.remove(file_path)
                                cleanup_info['cleaned_items'].append(f'audio:{file_path}')
                            except:
                                pass
        
        if cleanup_type in ['database', 'all']:
            # Clean old database records
            db = DatabaseManager()
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Clean old logs
            logs_deleted = db.cleanup_old_logs(cutoff_date)
            cleanup_info['cleaned_items'].append(f'database:logs:{logs_deleted}')
            
            # Clean old detections (archive instead of delete)
            detections_archived = db.archive_old_detections(cutoff_date)
            cleanup_info['cleaned_items'].append(f'database:detections:{detections_archived}')
        
        logger.info(f"System cleanup completed for {cleanup_type}")
        
        return jsonify(cleanup_info), 200
        
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Cleanup failed: {str(e)}'
        }), 500

@api_v1.route('/system/version', methods=['GET'])
def system_version():
    """
    Get system version information
    """
    try:
        import pkg_resources
        
        # Get package versions
        packages = [
            'Flask', 'torch', 'torchvision', 'ultralytics', 
            'opencv-python', 'pymongo', 'googlemaps'
        ]
        
        versions = {}
        for package in packages:
            try:
                versions[package] = pkg_resources.get_distribution(package).version
            except:
                versions[package] = 'not found'
        
        version_info = {
            'application': {
                'name': 'Real-Time CCTV Accident Detection System',
                'version': '1.0.0',
                'build_date': '2024-12-15',
                'api_version': 'v1'
            },
            'python': {
                'version': sys.version,
                'implementation': sys.implementation.name if hasattr(sys, 'implementation') else 'CPython'
            },
            'packages': versions,
            'system': {
                'platform': sys.platform,
                'machine': os.uname().machine if hasattr(os, 'uname') else 'unknown'
            }
        }
        
        return jsonify({
            'status': 'success',
            'version': version_info
        }), 200
        
    except Exception as e:
        logger.error(f"Version check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get version info: {str(e)}'
        }), 500