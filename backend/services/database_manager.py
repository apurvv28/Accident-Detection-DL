"""
DatabaseManager: simple facade around MongoDBConnector and models
"""
from typing import Dict, Any, List, Optional
from ..database.mongodb_connector import MongoDBConnector
from ..database.models import DatabaseModels
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    def __init__(self):
        self.db = MongoDBConnector()

    # Cameras
    def insert_camera(self, data: Dict) -> str:
        return self.db.insert_camera(data)

    def get_camera(self, camera_id: str) -> Optional[Dict]:
        return self.db.get_camera(camera_id)

    def get_all_cameras(self) -> List[Dict]:
        return self.db.get_all_cameras()

    def get_cameras_count(self, query: Dict = None) -> int:
        return self.db.get_cameras_count(query)

    def update_camera(self, camera_id: str, data: Dict) -> bool:
        return self.db.update_camera(camera_id, data)

    def delete_camera(self, camera_id: str) -> bool:
        return self.db.delete_camera(camera_id)

    # Detections
    def insert_detection(self, data: Dict) -> str:
        return self.db.insert_detection(data)

    def get_detection_by_video(self, video_id: str) -> Optional[Dict]:
        return self.db.get_detection_by_video(video_id)

    def get_detections_paginated(self, query: Dict = None, page: int = 1, limit: int = 50) -> List[Dict]:
        return self.db.get_detections_paginated(query=query, page=page, limit=limit)

    def get_detections_count(self, query: Dict = None) -> int:
        return self.db.get_detections_count(query)

    def get_recent_accidents(self, limit: int = 10) -> List[Dict]:
        return self.db.get_recent_accidents(limit)

    def get_recent_detections(self, camera_id: str = None, limit: int = 10) -> List[Dict]:
        return self.db.get_recent_detections(camera_id, limit)

    def get_most_common_vehicles(self, camera_id: str, limit: int = 5) -> List[Dict]:
        return self.db.get_most_common_vehicles(camera_id, limit)

    def get_hourly_detections(self, start_date) -> List[Dict]:
        return self.db.get_hourly_detections(start_date)

    def get_daily_detections(self, start_date) -> List[Dict]:
        return self.db.get_daily_detections(start_date)

    def get_camera_detection_distribution(self, start_date, limit: int = 10) -> List[Dict]:
        return self.db.get_camera_detection_distribution(start_date, limit)

    def get_accident_categories(self, start_date) -> List[Dict]:
        return self.db.get_accident_categories(start_date)

    def get_recent_detections_all(self, start_date, limit: int = 20) -> List[Dict]:
        return self.db.get_recent_detections_all(start_date, limit)

    def get_accidents_with_location(self, start_date) -> List[Dict]:
        return self.db.get_accidents_with_location(start_date)

    def get_accident_clusters(self, start_date, radius_km: float = 1) -> List[Dict]:
        return self.db.get_accident_clusters(start_date, radius_km)

    def get_detections_for_export(self, start_date) -> List[Dict]:
        return self.db.get_detections_for_export(start_date)

    def get_accidents_for_export(self, start_date) -> List[Dict]:
        return self.db.get_accidents_for_export(start_date)

    # Alerts
    def insert_alert(self, data: Dict) -> str:
        return self.db.insert_alert(data)

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict]:
        return self.db.get_alert_by_id(alert_id)

    def get_alerts_paginated(self, query: Dict = None, page: int = 1, limit: int = 50) -> List[Dict]:
        return self.db.get_alerts_paginated(query=query, page=page, limit=limit)

    def get_alerts_count(self, query: Dict = None) -> int:
        return self.db.get_alerts_count(query)

    def get_recent_alerts(self, limit: int = 5) -> List[Dict]:
        return self.db.get_recent_alerts(limit)

    def get_pending_alerts(self) -> List[Dict]:
        return self.db.get_pending_alerts()

    def get_alert_success_timeline(self, start_date) -> List[Dict]:
        return self.db.get_alert_success_timeline(start_date)

    def get_alerts_for_export(self, start_date) -> List[Dict]:
        return self.db.get_alerts_for_export(start_date)

    def update_alert(self, alert_id: str, data: Dict) -> bool:
        return self.db.update_alert(alert_id, data)

    def update_alert_config(self, data: Dict) -> bool:
        return self.db.update_alert_config(data)

    def get_alerts_by_type(self) -> Dict:
        return self.db.get_alerts_by_type()

    def get_alert_success_rate(self) -> float:
        return self.db.get_alert_success_rate()

    def get_most_active_cameras_for_alerts(self, limit: int = 5) -> List[Dict]:
        return self.db.get_most_active_cameras_for_alerts(limit)

    def save_alert_config(self, data: Dict) -> str:
        # store in system collection
        cfg = {'config': data}
        return self.db.insert_alert(cfg)

    def get_alert_config(self) -> Optional[Dict]:
        # Simple stub that returns None
        return None

    def insert_alert_log(self, data: Dict) -> str:
        return self.db.insert_log(data)

    def test_connection(self) -> bool:
        """Return whether database connection is active"""
        try:
            # Use the underlying connector's test method if available
            if hasattr(self.db, 'test_connection'):
                return self.db.test_connection()
            # Fallback: try a simple command
            return self.db.client is not None
        except Exception:
            return False

    def reconnect(self) -> bool:
        """Reconnect to database"""
        return self.db.reconnect()

    def get_videos_paginated(self, page: int = 1, limit: int = 20) -> List[Dict]:
        return self.db.get_videos_paginated(page, limit)

    def get_videos_count(self) -> int:
        return self.db.get_videos_count()

    def get_system_logs(self, query: Dict = None, limit: int = 100) -> List[Dict]:
        return self.db.get_system_logs(query, limit)
