"""
Dashboard Data API Endpoints
"""
import json
from datetime import datetime, timedelta
from flask import request, jsonify

from ..services.database_manager import DatabaseManager
from ..utils.logger import setup_logger
from . import api_v1

logger = setup_logger(__name__)

@api_v1.route('/dashboard/overview', methods=['GET'])
def dashboard_overview():
    """
    Get dashboard overview statistics
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Dashboard overview data
    """
    try:
        db = DatabaseManager()
        
        # Time ranges
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        
        # Get counts
        total_cameras = db.get_cameras_count()
        active_cameras = db.get_cameras_count({'status': 'active'})
        
        total_detections = db.get_detections_count()
        detections_today = db.get_detections_count({'timestamp': {'$gte': today_start}})
        detections_yesterday = db.get_detections_count({'timestamp': {'$gte': yesterday_start, '$lt': today_start}})
        
        total_accidents = db.get_detections_count({'is_accident': True})
        accidents_today = db.get_detections_count({'is_accident': True, 'timestamp': {'$gte': today_start}})
        
        total_alerts = db.get_alerts_count()
        alerts_today = db.get_alerts_count({'timestamp': {'$gte': today_start}})
        
        # Calculate changes
        detection_change = calculate_percentage_change(detections_today, detections_yesterday)
        accident_change = calculate_percentage_change(accidents_today, db.get_detections_count({'is_accident': True, 'timestamp': {'$gte': yesterday_start, '$lt': today_start}}))
        
        # Get recent accidents
        recent_accidents = db.get_recent_accidents(limit=10)
        
        # Get active alerts
        active_alerts = db.get_recent_alerts(limit=5)
        
        # Get system health
        from ..api.inference_routes import active_streams
        active_inferences = len(active_streams)
        
        overview = {
            'summary': {
                'total_cameras': total_cameras,
                'active_cameras': active_cameras,
                'total_detections': total_detections,
                'detections_today': detections_today,
                'detection_change_percent': detection_change,
                'total_accidents': total_accidents,
                'accidents_today': accidents_today,
                'accident_change_percent': accident_change,
                'total_alerts': total_alerts,
                'alerts_today': alerts_today,
                'active_inferences': active_inferences
            },
            'recent_activity': {
                'recent_accidents': recent_accidents,
                'active_alerts': active_alerts
            },
            'timestamps': {
                'generated_at': datetime.now().isoformat(),
                'today_start': today_start.isoformat()
            }
        }
        
        return jsonify({
            'status': 'success',
            'overview': overview
        }), 200
        
    except Exception as e:
        logger.error(f"Dashboard overview error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get dashboard overview: {str(e)}'
        }), 500

@api_v1.route('/dashboard/charts', methods=['GET'])
def dashboard_charts():
    """
    Get chart data for dashboard
    """
    try:
        days = int(request.args.get('days', 7))
        start_date = datetime.now() - timedelta(days=days)
        
        db = DatabaseManager()
        
        # Get hourly data for last N days
        hourly_data = db.get_hourly_detections(start_date)
        
        # Get daily totals
        daily_data = db.get_daily_detections(start_date)
        
        # Get camera-wise distribution
        camera_distribution_raw = db.get_camera_detection_distribution(start_date, limit=10)
        # Transform to match frontend expectations (name and count for pie chart)
        camera_distribution = [
            {
                'name': item.get('camera_id', 'Unknown'),
                'count': item.get('detections', 0)
            }
            for item in camera_distribution_raw
        ]
        
        # Get accident types/categories
        accident_categories = db.get_accident_categories(start_date)
        
        # Get alert success rate over time
        alert_success_data = db.get_alert_success_timeline(start_date)
        
        charts = {
            'hourly_detections': {
                'labels': [f"{h['hour']}:00" for h in hourly_data],
                'detections': [h['count'] for h in hourly_data],
                'accidents': [h.get('accidents', 0) for h in hourly_data]
            },
            'daily_totals': {
                'labels': [d['date'].strftime('%Y-%m-%d') for d in daily_data],
                'detections': [d['detections'] for d in daily_data],
                'accidents': [d['accidents'] for d in daily_data]
            },
            'camera_distribution': camera_distribution,
            'accident_categories': accident_categories,
            'alert_success_rate': alert_success_data,
            'time_range': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.now().isoformat(),
                'days': days
            }
        }
        
        return jsonify({
            'status': 'success',
            'charts': charts
        }), 200
        
    except Exception as e:
        logger.error(f"Dashboard charts error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get chart data: {str(e)}'
        }), 500

@api_v1.route('/dashboard/realtime', methods=['GET'])
def realtime_updates():
    """
    Get real-time updates for dashboard
    """
    try:
        # Get active inferences
        from ..api.inference_routes import active_streams
        active_inferences = []
        
        for camera_id, processor in active_streams.items():
            active_inferences.append({
                'camera_id': camera_id,
                'stream_url': processor.stream_url,
                'running': processor.running
            })
        
        # Get recent detections (last 5 minutes)
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        db = DatabaseManager()
        recent_detections = db.get_recent_detections_all(five_minutes_ago, limit=20)
        
        # Get system metrics
        import psutil
        import os
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get process memory
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        system_metrics = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / 1024 / 1024 / 1024,
            'memory_total_gb': memory.total / 1024 / 1024 / 1024,
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / 1024 / 1024 / 1024,
            'process_memory_mb': process_memory,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get pending alerts
        pending_alerts = db.get_pending_alerts()
        
        realtime_data = {
            'active_inferences': active_inferences,
            'recent_detections': recent_detections,
            'system_metrics': system_metrics,
            'pending_alerts': pending_alerts,
            'update_time': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'realtime': realtime_data
        }), 200
        
    except Exception as e:
        logger.error(f"Realtime updates error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get realtime updates: {str(e)}'
        }), 500

@api_v1.route('/dashboard/heatmap', methods=['GET'])
def accident_heatmap():
    """
    Get accident heatmap data
    """
    try:
        days = int(request.args.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        db = DatabaseManager()
        
        # Get accidents with location data
        accidents = db.get_accidents_with_location(start_date)
        
        # Process for heatmap
        heatmap_data = []
        for accident in accidents:
            if 'location' in accident and 'latitude' in accident['location'] and 'longitude' in accident['location']:
                heatmap_data.append({
                    'lat': float(accident['location']['latitude']),
                    'lng': float(accident['location']['longitude']),
                    'weight': accident.get('confidence', 0.5),
                    'timestamp': accident.get('timestamp'),
                    'camera_id': accident.get('camera_id'),
                    'severity': accident.get('severity', 'medium')
                })
        
        # Get clusters (high accident zones)
        clusters = db.get_accident_clusters(start_date, radius_km=1)
        
        return jsonify({
            'status': 'success',
            'heatmap': {
                'points': heatmap_data,
                'clusters': clusters,
                'total_points': len(heatmap_data)
            },
            'time_range': {
                'days': days,
                'start_date': start_date.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Heatmap error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get heatmap data: {str(e)}'
        }), 500

@api_v1.route('/dashboard/export', methods=['GET'])
def export_data():
    """
    Export dashboard data
    """
    try:
        format_type = request.args.get('format', 'json')
        days = int(request.args.get('days', 30))
        
        if format_type not in ['json', 'csv']:
            return jsonify({
                'status': 'error',
                'message': 'Unsupported format. Use json or csv'
            }), 400
        
        start_date = datetime.now() - timedelta(days=days)
        db = DatabaseManager()
        
        # Get data to export
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'time_range_days': days,
                'start_date': start_date.isoformat(),
                'end_date': datetime.now().isoformat()
            },
            'summary': {
                'total_detections': db.get_detections_count({'timestamp': {'$gte': start_date}}),
                'total_accidents': db.get_detections_count({'is_accident': True, 'timestamp': {'$gte': start_date}}),
                'total_alerts': db.get_alerts_count({'timestamp': {'$gte': start_date}})
            },
            'detections': db.get_detections_for_export(start_date),
            'accidents': db.get_accidents_for_export(start_date),
            'alerts': db.get_alerts_for_export(start_date)
        }
        
        if format_type == 'json':
            return jsonify({
                'status': 'success',
                'data': export_data
            }), 200
        else:
            # For CSV, you would generate CSV files
            # This is a simplified version
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write headers and data (simplified)
            writer.writerow(['Export Date', 'Time Range Days', 'Total Detections', 'Total Accidents'])
            writer.writerow([
                export_data['metadata']['export_date'],
                export_data['metadata']['time_range_days'],
                export_data['summary']['total_detections'],
                export_data['summary']['total_accidents']
            ])
            
            output.seek(0)
            
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": f"attachment; filename=accident_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
            
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to export data: {str(e)}'
        }), 500

def calculate_percentage_change(current, previous):
    """
    Calculate percentage change
    """
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous) * 100