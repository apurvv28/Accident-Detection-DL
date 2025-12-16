"""
MongoDB Connection Manager
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class MongoDBConnector:
    """
    MongoDB connection and operations manager
    """
    
    def __init__(self):
        load_dotenv()
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Establish connection to MongoDB"""
        try:
            # Get connection string from environment or use default
            mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
            database_name = os.getenv('MONGODB_DB', 'accident_detection')
            
            # Connect to MongoDB
            self.client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Select database
            self.db = self.client[database_name]
            
            # Create collections if they don't exist
            self._create_collections()
            
            # Create indexes for performance
            self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {database_name}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            self.client = None
            self.db = None
            return False
        except Exception as e:
            logger.error(f"Unexpected MongoDB error: {e}")
            self.client = None
            self.db = None
            return False
    
    def _create_collections(self):
        """Create required collections if they don't exist"""
        collections = ['cameras', 'detections', 'alerts', 'system_logs']
        
        existing_collections = self.db.list_collection_names()
        
        for collection_name in collections:
            if collection_name not in existing_collections:
                self.db.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")
    
    def _create_indexes(self):
        """Create indexes for query performance"""
        
        # Cameras collection indexes
        self.db.cameras.create_index([('camera_id', ASCENDING)], unique=True)
        self.db.cameras.create_index([('status', ASCENDING)])
        self.db.cameras.create_index([('location', '2dsphere')])
        
        # Detections collection indexes
        self.db.detections.create_index([('timestamp', DESCENDING)])
        self.db.detections.create_index([('camera_id', ASCENDING), ('timestamp', DESCENDING)])
        self.db.detections.create_index([('is_accident', ASCENDING), ('timestamp', DESCENDING)])
        self.db.detections.create_index([('confidence', DESCENDING)])
        self.db.detections.create_index([('location', '2dsphere')])
        self.db.detections.create_index([('detection_id', ASCENDING)], unique=True)
        
        # Alerts collection indexes
        self.db.alerts.create_index([('timestamp', DESCENDING)])
        self.db.alerts.create_index([('alert_id', ASCENDING)], unique=True)
        self.db.alerts.create_index([('status', ASCENDING), ('timestamp', DESCENDING)])
        
        # System logs collection indexes
        self.db.system_logs.create_index([('timestamp', DESCENDING)])
        self.db.system_logs.create_index([('level', ASCENDING), ('timestamp', DESCENDING)])
        
        logger.info("Database indexes created/verified")
    
    def test_connection(self):
        """Test if database connection is active"""
        try:
            if self.client is None:
                return False
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def reconnect(self):
        """Reconnect to database"""
        self.disconnect()
        return self.connect()
    
    def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed")
    
    # ========== CAMERA OPERATIONS ==========
    
    def insert_camera(self, camera_data: Dict) -> str:
        """Insert a new camera document"""
        try:
            result = self.db.cameras.insert_one(camera_data)
            logger.info(f"Camera inserted: {camera_data.get('camera_id')}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to insert camera: {e}")
            raise
    
    def get_camera(self, camera_id: str) -> Optional[Dict]:
        """Get camera by camera_id"""
        try:
            camera = self.db.cameras.find_one({'camera_id': camera_id})
            if camera:
                camera['_id'] = str(camera['_id'])
            return camera
        except Exception as e:
            logger.error(f"Failed to get camera {camera_id}: {e}")
            return None
    
    def get_all_cameras(self) -> List[Dict]:
        """Get all cameras"""
        try:
            cameras = list(self.db.cameras.find().sort('camera_id', ASCENDING))
            for camera in cameras:
                camera['_id'] = str(camera['_id'])
            return cameras
        except Exception as e:
            logger.error(f"Failed to get cameras: {e}")
            return []
    
    def update_camera(self, camera_id: str, update_data: Dict) -> bool:
        """Update camera document"""
        try:
            # Don't update _id
            if '_id' in update_data:
                del update_data['_id']
            
            result = self.db.cameras.update_one(
                {'camera_id': camera_id},
                {'$set': update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Camera updated: {camera_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to update camera {camera_id}: {e}")
            return False
    
    def delete_camera(self, camera_id: str) -> bool:
        """Delete camera document"""
        try:
            result = self.db.cameras.delete_one({'camera_id': camera_id})
            success = result.deleted_count > 0
            if success:
                logger.info(f"Camera deleted: {camera_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete camera {camera_id}: {e}")
            return False
    
    def get_cameras_count(self, query: Dict = None) -> int:
        """Count cameras matching query"""
        try:
            if query is None:
                query = {}
            return self.db.cameras.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count cameras: {e}")
            return 0
    
    # ========== DETECTION OPERATIONS ==========
    
    def insert_detection(self, detection_data: Dict) -> str:
        """Insert a new detection document"""
        try:
            # Ensure required fields
            if 'timestamp' not in detection_data:
                detection_data['timestamp'] = datetime.now()
            
            result = self.db.detections.insert_one(detection_data)
            detection_id = detection_data.get('detection_id', str(result.inserted_id))
            logger.info(f"Detection inserted: {detection_id}")
            return detection_id
        except Exception as e:
            logger.error(f"Failed to insert detection: {e}")
            raise
    
    def get_detection_by_id(self, detection_id: str) -> Optional[Dict]:
        """Get detection by detection_id"""
        try:
            detection = self.db.detections.find_one({'detection_id': detection_id})
            if detection:
                detection['_id'] = str(detection['_id'])
            return detection
        except Exception as e:
            logger.error(f"Failed to get detection {detection_id}: {e}")
            return None
    
    def get_detections_paginated(self, query: Dict = None, page: int = 1, 
                               limit: int = 50, sort_by: str = 'timestamp', 
                               sort_order: int = DESCENDING) -> List[Dict]:
        """Get detections with pagination"""
        try:
            if query is None:
                query = {}
            
            skip = (page - 1) * limit
            
            detections = list(self.db.detections.find(query)
                            .sort(sort_by, sort_order)
                            .skip(skip)
                            .limit(limit))
            
            for detection in detections:
                detection['_id'] = str(detection['_id'])
                
                # Convert ObjectId to string for any nested documents
                if 'camera_id' in detection and isinstance(detection['camera_id'], dict):
                    if '_id' in detection['camera_id']:
                        detection['camera_id']['_id'] = str(detection['camera_id']['_id'])
            
            return detections
        except Exception as e:
            logger.error(f"Failed to get detections: {e}")
            return []
    
    def get_detections_count(self, query: Dict = None) -> int:
        """Count detections matching query"""
        try:
            if query is None:
                query = {}
            return self.db.detections.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count detections: {e}")
            return 0
    
    def update_detection(self, detection_id: str, update_data: Dict) -> bool:
        """Update detection document"""
        try:
            # Don't update _id
            if '_id' in update_data:
                del update_data['_id']
            
            result = self.db.detections.update_one(
                {'detection_id': detection_id},
                {'$set': update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Detection updated: {detection_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to update detection {detection_id}: {e}")
            return False
    
    def delete_detection(self, detection_id: str) -> bool:
        """Delete detection document"""
        try:
            result = self.db.detections.delete_one({'detection_id': detection_id})
            success = result.deleted_count > 0
            if success:
                logger.info(f"Detection deleted: {detection_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete detection {detection_id}: {e}")
            return False
    
    def get_detection_by_video(self, video_id: str) -> Optional[Dict]:
        """Get detection by video filename"""
        try:
            detection = self.db.detections.find_one({'video_path': {'$regex': video_id}})
            if detection:
                detection['_id'] = str(detection['_id'])
            return detection
        except Exception as e:
            logger.error(f"Failed to get detection for video {video_id}: {e}")
            return None
    
    def get_recent_detections(self, camera_id: str = None, limit: int = 10) -> List[Dict]:
        """Get recent detections"""
        try:
            query = {}
            if camera_id:
                query['camera_id'] = camera_id
            
            detections = list(self.db.detections.find(query)
                            .sort('timestamp', DESCENDING)
                            .limit(limit))
            
            for detection in detections:
                detection['_id'] = str(detection['_id'])
            
            return detections
        except Exception as e:
            logger.error(f"Failed to get recent detections: {e}")
            return []
    
    def get_recent_accidents(self, limit: int = 10) -> List[Dict]:
        """Get recent accidents"""
        try:
            detections = list(self.db.detections.find({'is_accident': True})
                            .sort('timestamp', DESCENDING)
                            .limit(limit))
            
            for detection in detections:
                detection['_id'] = str(detection['_id'])
            
            return detections
        except Exception as e:
            logger.error(f"Failed to get recent accidents: {e}")
            return []
    
    # ========== ALERT OPERATIONS ==========
    
    def insert_alert(self, alert_data: Dict) -> str:
        """Insert a new alert document"""
        try:
            # Ensure required fields
            if 'timestamp' not in alert_data:
                alert_data['timestamp'] = datetime.now()
            if 'status' not in alert_data:
                alert_data['status'] = 'sent'
            
            result = self.db.alerts.insert_one(alert_data)
            alert_id = alert_data.get('alert_id', str(result.inserted_id))
            logger.info(f"Alert inserted: {alert_id}")
            return alert_id
        except Exception as e:
            logger.error(f"Failed to insert alert: {e}")
            raise
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Dict]:
        """Get alert by alert_id"""
        try:
            alert = self.db.alerts.find_one({'alert_id': alert_id})
            if alert:
                alert['_id'] = str(alert['_id'])
            return alert
        except Exception as e:
            logger.error(f"Failed to get alert {alert_id}: {e}")
            return None
    
    def get_alerts_paginated(self, query: Dict = None, page: int = 1, 
                           limit: int = 50) -> List[Dict]:
        """Get alerts with pagination"""
        try:
            if query is None:
                query = {}
            
            skip = (page - 1) * limit
            
            alerts = list(self.db.alerts.find(query)
                         .sort('timestamp', DESCENDING)
                         .skip(skip)
                         .limit(limit))
            
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
            
            return alerts
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def get_alerts_count(self, query: Dict = None) -> int:
        """Count alerts matching query"""
        try:
            if query is None:
                query = {}
            return self.db.alerts.count_documents(query)
        except Exception as e:
            logger.error(f"Failed to count alerts: {e}")
            return 0
    
    def update_alert(self, alert_id: str, update_data: Dict) -> bool:
        """Update alert document"""
        try:
            # Don't update _id
            if '_id' in update_data:
                del update_data['_id']
            
            result = self.db.alerts.update_one(
                {'alert_id': alert_id},
                {'$set': update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Alert updated: {alert_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to update alert {alert_id}: {e}")
            return False
    
    def get_recent_alerts(self, limit: int = 5) -> List[Dict]:
        """Get recent alerts"""
        try:
            alerts = list(self.db.alerts.find()
                         .sort('timestamp', DESCENDING)
                         .limit(limit))
            
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
            
            return alerts
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    def get_pending_alerts(self) -> List[Dict]:
        """Get pending/failed alerts that need retry"""
        try:
            # Alerts that failed and haven't been retried recently
            cutoff_time = datetime.now() - timedelta(minutes=5)
            
            query = {
                'status': {'$in': ['failed', 'pending']},
                'last_retry': {'$lt': cutoff_time}
            }
            
            alerts = list(self.db.alerts.find(query)
                         .sort('timestamp', ASCENDING)
                         .limit(10))
            
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
            
            return alerts
        except Exception as e:
            logger.error(f"Failed to get pending alerts: {e}")
            return []
    
    # ========== SYSTEM LOGS OPERATIONS ==========
    
    def insert_log(self, log_data: Dict) -> str:
        """Insert a system log document"""
        try:
            # Ensure required fields
            if 'timestamp' not in log_data:
                log_data['timestamp'] = datetime.now()
            if 'level' not in log_data:
                log_data['level'] = 'INFO'
            
            result = self.db.system_logs.insert_one(log_data)
            log_id = str(result.inserted_id)
            return log_id
        except Exception as e:
            logger.error(f"Failed to insert log: {e}")
            raise
    
    def get_system_logs(self, query: Dict = None, limit: int = 100) -> List[Dict]:
        """Get system logs"""
        try:
            if query is None:
                query = {}
            
            logs = list(self.db.system_logs.find(query)
                       .sort('timestamp', DESCENDING)
                       .limit(limit))
            
            for log in logs:
                log['_id'] = str(log['_id'])
            
            return logs
        except Exception as e:
            logger.error(f"Failed to get system logs: {e}")
            return []
    
    # ========== ANALYTICS & AGGREGATION OPERATIONS ==========
    
    def get_hourly_detections(self, start_date: datetime) -> List[Dict]:
        """Get hourly detection counts"""
        try:
            pipeline = [
                {
                    '$match': {
                        'timestamp': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'year': {'$year': '$timestamp'},
                            'month': {'$month': '$timestamp'},
                            'day': {'$dayOfMonth': '$timestamp'},
                            'hour': {'$hour': '$timestamp'}
                        },
                        'count': {'$sum': 1},
                        'accidents': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$is_accident', True]},
                                    1,
                                    0
                                ]
                            }
                        }
                    }
                },
                {
                    '$sort': {'_id': 1}
                },
                {
                    '$project': {
                        '_id': 0,
                        'date': {
                            '$dateFromParts': {
                                'year': '$_id.year',
                                'month': '$_id.month',
                                'day': '$_id.day',
                                'hour': '$_id.hour'
                            }
                        },
                        'hour': '$_id.hour',
                        'count': 1,
                        'accidents': 1
                    }
                }
            ]
            
            result = list(self.db.detections.aggregate(pipeline))
            return result
        except Exception as e:
            logger.error(f"Failed to get hourly detections: {e}")
            return []
    
    def get_daily_detections(self, start_date: datetime) -> List[Dict]:
        """Get daily detection counts"""
        try:
            pipeline = [
                {
                    '$match': {
                        'timestamp': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'year': {'$year': '$timestamp'},
                            'month': {'$month': '$timestamp'},
                            'day': {'$dayOfMonth': '$timestamp'}
                        },
                        'detections': {'$sum': 1},
                        'accidents': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$is_accident', True]},
                                    1,
                                    0
                                ]
                            }
                        }
                    }
                },
                {
                    '$sort': {'_id': 1}
                },
                {
                    '$project': {
                        '_id': 0,
                        'date': {
                            '$dateFromParts': {
                                'year': '$_id.year',
                                'month': '$_id.month',
                                'day': '$_id.day'
                            }
                        },
                        'detections': 1,
                        'accidents': 1
                    }
                }
            ]
            
            result = list(self.db.detections.aggregate(pipeline))
            return result
        except Exception as e:
            logger.error(f"Failed to get daily detections: {e}")
            return []
    
    def get_camera_detection_distribution(self, start_date: datetime, limit: int = 10) -> List[Dict]:
        """Get detection distribution by camera"""
        try:
            pipeline = [
                {
                    '$match': {
                        'timestamp': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': '$camera_id',
                        'detections': {'$sum': 1},
                        'accidents': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$is_accident', True]},
                                    1,
                                    0
                                ]
                            }
                        }
                    }
                },
                {
                    '$sort': {'detections': -1}
                },
                {
                    '$limit': limit
                },
                {
                    '$project': {
                        '_id': 0,
                        'camera_id': '$_id',
                        'detections': 1,
                        'accidents': 1
                    }
                }
            ]
            
            result = list(self.db.detections.aggregate(pipeline))
            return result
        except Exception as e:
            logger.error(f"Failed to get camera distribution: {e}")
            return []
    
    def get_accidents_with_location(self, start_date: datetime) -> List[Dict]:
        """Get accidents with location data"""
        try:
            query = {
                'is_accident': True,
                'timestamp': {'$gte': start_date},
                'location': {'$exists': True}
            }
            
            accidents = list(self.db.detections.find(query)
                           .sort('timestamp', DESCENDING))
            
            for accident in accidents:
                accident['_id'] = str(accident['_id'])
            
            return accidents
        except Exception as e:
            logger.error(f"Failed to get accidents with location: {e}")
            return []
    
    def get_daily_average_detections(self, camera_id: str, days: int = 7) -> float:
        """Get daily average detections for a camera"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'camera_id': camera_id,
                        'timestamp': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'year': {'$year': '$timestamp'},
                            'month': {'$month': '$timestamp'},
                            'day': {'$dayOfMonth': '$timestamp'}
                        },
                        'count': {'$sum': 1}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'average': {'$avg': '$count'}
                    }
                }
            ]
            
            result = list(self.db.detections.aggregate(pipeline))
            
            if result and 'average' in result[0]:
                return round(result[0]['average'], 2)
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get daily average: {e}")
            return 0.0
    
    def get_peak_detection_hours(self, camera_id: str) -> List[Dict]:
        """Get peak detection hours for a camera"""
        try:
            start_date = datetime.now() - timedelta(days=30)
            
            pipeline = [
                {
                    '$match': {
                        'camera_id': camera_id,
                        'timestamp': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': {'$hour': '$timestamp'},
                        'count': {'$sum': 1},
                        'accidents': {
                            '$sum': {
                                '$cond': [
                                    {'$eq': ['$is_accident', True]},
                                    1,
                                    0
                                ]
                            }
                        }
                    }
                },
                {
                    '$sort': {'count': -1}
                },
                {
                    '$limit': 5
                },
                {
                    '$project': {
                        '_id': 0,
                        'hour': '$_id',
                        'count': 1,
                        'accidents': 1
                    }
                }
            ]
            
            result = list(self.db.detections.aggregate(pipeline))
            return result
        except Exception as e:
            logger.error(f"Failed to get peak hours: {e}")
            return []
    
    # ========== CLEANUP OPERATIONS ==========
    
    def cleanup_old_logs(self, cutoff_date: datetime) -> int:
        """Delete logs older than cutoff date"""
        try:
            result = self.db.system_logs.delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            deleted_count = result.deleted_count
            logger.info(f"Cleaned up {deleted_count} old logs")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0
    
    def archive_old_detections(self, cutoff_date: datetime) -> int:
        """Archive detections older than cutoff date (mark as archived)"""
        try:
            result = self.db.detections.update_many(
                {
                    'timestamp': {'$lt': cutoff_date},
                    'archived': {'$ne': True}
                },
                {
                    '$set': {'archived': True, 'archived_at': datetime.now()}
                }
            )
            archived_count = result.modified_count
            logger.info(f"Archived {archived_count} old detections")
            return archived_count
        except Exception as e:
            logger.error(f"Failed to archive old detections: {e}")
            return 0
    
    # ========== ALERT CONFIGURATION ==========
    
    def save_alert_config(self, config_data: Dict) -> str:
        """Save alert configuration"""
        try:
            # Store in a dedicated collection or in system settings
            config_data['config_type'] = 'alert'
            config_data['updated_at'] = datetime.now()
            
            # Remove old config
            self.db.system_settings.delete_many({'config_type': 'alert'})
            
            # Insert new config
            result = self.db.system_settings.insert_one(config_data)
            config_id = str(result.inserted_id)
            
            logger.info("Alert configuration saved")
            return config_id
        except Exception as e:
            logger.error(f"Failed to save alert config: {e}")
            raise
    
    def get_alert_config(self) -> Optional[Dict]:
        """Get alert configuration"""
        try:
            config = self.db.system_settings.find_one({'config_type': 'alert'})
            if config:
                config['_id'] = str(config['_id'])
            return config
        except Exception as e:
            logger.error(f"Failed to get alert config: {e}")
            return None
    
    def update_alert_config(self, update_data: Dict) -> bool:
        """Update alert configuration"""
        try:
            update_data['updated_at'] = datetime.now()
            
            result = self.db.system_settings.update_one(
                {'config_type': 'alert'},
                {'$set': update_data},
                upsert=True
            )
            
            success = result.modified_count > 0 or result.upserted_id is not None
            if success:
                logger.info("Alert configuration updated")
            return success
        except Exception as e:
            logger.error(f"Failed to update alert config: {e}")
            return False