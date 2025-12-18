"""
Alert Management API Endpoints
"""
import json
from datetime import datetime, timedelta
from flask import request, jsonify, current_app

from ..services.alert_dispatcher import AlertDispatcher
from ..services.database_manager import DatabaseManager
from ..utils.logger import setup_logger
from . import api_v1

logger = setup_logger(__name__)

@api_v1.route('/alert/test', methods=['POST'])
def test_alert():
    """
    Test alert system
    ---
    tags:
      - Alerts
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            alert_type:
              type: string
              enum: [voice, tts, sms, all]
            message:
              type: string
            phone_numbers:
              type: array
              items:
                type: string
    responses:
      200:
        description: Alert test initiated
    """
    try:
        data = request.get_json()
        alert_type = data.get('alert_type', 'tts')
        message = data.get('message', 'Test alert from Accident Detection System')
        phone_numbers = data.get('phone_numbers', [])
        
        alert = AlertDispatcher()
        
        test_result = {
            'status': 'success',
            'tests': []
        }
        
        # Test TTS
        if alert_type in ['tts', 'all']:
            try:
                tts_result = alert.send_tts_alert(message, is_test=True)
                test_result['tests'].append({
                    'type': 'tts',
                    'success': True,
                    'message': 'TTS alert generated successfully',
                    'audio_file': tts_result.get('audio_file')
                })
            except Exception as e:
                test_result['tests'].append({
                    'type': 'tts',
                    'success': False,
                    'message': str(e)
                })
        
        # Test voice call (if Twilio enabled)
        if alert_type in ['voice', 'all'] and current_app.config.get('ENABLE_VOICE_ALERTS', False):
            if not phone_numbers:
                test_result['tests'].append({
                    'type': 'voice',
                    'success': False,
                    'message': 'Phone numbers required for voice test'
                })
            else:
                for phone in phone_numbers:
                    try:
                        voice_result = alert.send_voice_alert(phone, message, is_test=True)
                        test_result['tests'].append({
                            'type': 'voice',
                            'phone': phone,
                            'success': True,
                            'message': 'Voice call initiated',
                            'call_sid': voice_result.get('call_sid')
                        })
                    except Exception as e:
                        test_result['tests'].append({
                            'type': 'voice',
                            'phone': phone,
                            'success': False,
                            'message': str(e)
                        })
        
        # Test SMS
        if alert_type in ['sms', 'all'] and current_app.config.get('TWILIO_ACCOUNT_SID'):
            if not phone_numbers:
                test_result['tests'].append({
                    'type': 'sms',
                    'success': False,
                    'message': 'Phone numbers required for SMS test'
                })
            else:
                for phone in phone_numbers:
                    try:
                        sms_result = alert.send_sms_alert(phone, message, is_test=True)
                        test_result['tests'].append({
                            'type': 'sms',
                            'phone': phone,
                            'success': True,
                            'message': 'SMS sent',
                            'message_sid': sms_result.get('message_sid')
                        })
                    except Exception as e:
                        test_result['tests'].append({
                            'type': 'sms',
                            'phone': phone,
                            'success': False,
                            'message': str(e)
                        })
        
        # Save test result
        db = DatabaseManager()
        db.insert_alert_log({
            'alert_id': f"test_{int(datetime.now().timestamp())}",
            'type': 'test',
            'message': message,
            'result': test_result,
            'timestamp': datetime.now()
        })
        
        return jsonify(test_result), 200
        
    except Exception as e:
        logger.error(f"Alert test error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Alert test failed: {str(e)}'
        }), 500

@api_v1.route('/alert/config', methods=['GET', 'POST', 'PUT'])
def manage_alert_config():
    """
    Manage alert configuration
    """
    try:
        db = DatabaseManager()
        
        if request.method == 'GET':
            # Get current configuration
            config = db.get_alert_config()
            
            default_config = {
                'enable_voice_alerts': current_app.config.get('ENABLE_VOICE_ALERTS', False),
                'enable_sms_alerts': bool(current_app.config.get('TWILIO_ACCOUNT_SID')),
                'enable_tts_alerts': True,
                'min_confidence': current_app.config.get('MIN_CONFIDENCE', 0.75),
                'cooldown_minutes': current_app.config.get('ALERT_COOLDOWN_MINUTES', 5),
                'recipients': {
                    'phone_numbers': current_app.config.get('ALERT_PHONE_NUMBERS', '').split(',')
                },
                'tts_settings': {
                    'engine': current_app.config.get('TTS_ENGINE', 'gtts'),
                    'language': current_app.config.get('TTS_LANGUAGE', 'en'),
                    'speed': current_app.config.get('TTS_SPEED', 'normal')
                }
            }
            
            # Merge with saved config
            if config:
                default_config.update(config)
            
            return jsonify({
                'status': 'success',
                'config': default_config
            }), 200
        
        elif request.method == 'POST':
            # Create new configuration
            data = request.get_json()
            config_id = db.save_alert_config(data)
            
            return jsonify({
                'status': 'success',
                'message': 'Alert configuration saved',
                'config_id': config_id
            }), 201
        
        elif request.method == 'PUT':
            # Update configuration
            data = request.get_json()
            success = db.update_alert_config(data)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Alert configuration updated'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to update configuration'
                }), 500
                
    except Exception as e:
        logger.error(f"Alert config error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Configuration management failed: {str(e)}'
        }), 500

@api_v1.route('/alert/history', methods=['GET'])
def get_alert_history():
    """
    Get alert history with pagination
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        alert_type = request.args.get('type')
        
        db = DatabaseManager()
        
        # Build query
        query = {}
        if alert_type:
            query['type'] = alert_type
        
        alerts = db.get_alerts_paginated(query=query, page=page, limit=limit)
        total = db.get_alerts_count(query)
        
        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Alert history error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get alert history: {str(e)}'
        }), 500

@api_v1.route('/alert/resend/<alert_id>', methods=['POST'])
def resend_alert(alert_id):
    """
    Resend a specific alert
    """
    try:
        db = DatabaseManager()
        alert = db.get_alert_by_id(alert_id)
        
        if not alert:
            return jsonify({
                'status': 'error',
                'message': 'Alert not found'
            }), 404
        
        # Check cooldown
        last_sent = alert.get('timestamp')
        if last_sent:
            last_sent_dt = last_sent if isinstance(last_sent, datetime) else datetime.fromisoformat(str(last_sent))
            cooldown_minutes = current_app.config.get('ALERT_COOLDOWN_MINUTES', 5)
            
            if datetime.now() - last_sent_dt < timedelta(minutes=cooldown_minutes):
                return jsonify({
                    'status': 'error',
                    'message': f'Alert was sent recently. Please wait {cooldown_minutes} minutes between alerts.'
                }), 429
        
        # Resend alert
        alert_service = AlertDispatcher()
        
        # Get message from alert
        message = alert.get('message', 'Accident detected. Please check the system.')
        
        # Send based on original type
        alert_type = alert.get('type', 'tts')
        
        if alert_type == 'voice' and current_app.config.get('ENABLE_VOICE_ALERTS'):
            phone_numbers = alert.get('recipients', {}).get('phone_numbers', [])
            for phone in phone_numbers:
                alert_service.send_voice_alert(phone, message)
        
        elif alert_type == 'sms' and current_app.config.get('TWILIO_ACCOUNT_SID'):
            phone_numbers = alert.get('recipients', {}).get('phone_numbers', [])
            for phone in phone_numbers:
                alert_service.send_sms_alert(phone, message)
        
        else:  # Default to TTS
            alert_service.send_tts_alert(message)
        
        # Update alert record
        alert['resend_count'] = alert.get('resend_count', 0) + 1
        alert['last_resend'] = datetime.now()
        db.update_alert(alert_id, alert)
        
        return jsonify({
            'status': 'success',
            'message': 'Alert resent successfully',
            'alert_id': alert_id,
            'resend_count': alert['resend_count']
        }), 200
        
    except Exception as e:
        logger.error(f"Resend alert error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to resend alert: {str(e)}'
        }), 500

@api_v1.route('/alert/stats', methods=['GET'])
def get_alert_stats():
    """
    Get alert statistics
    """
    try:
        db = DatabaseManager()
        
        # Time range filter
        days = int(request.args.get('days', 7))
        start_date = datetime.now() - timedelta(days=days)
        
        stats = {
            'total_alerts': db.get_alerts_count(),
            'alerts_today': db.get_alerts_count({'timestamp': {'$gte': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}}),
            'alerts_last_7_days': db.get_alerts_count({'timestamp': {'$gte': start_date}}),
            'by_type': db.get_alerts_by_type(),
            'success_rate': db.get_alert_success_rate(),
            'most_active_cameras': db.get_most_active_cameras_for_alerts(limit=5)
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'period_days': days
        }), 200
        
    except Exception as e:
        logger.error(f"Alert stats error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get alert statistics: {str(e)}'
        }), 500