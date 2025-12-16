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

    # Alerts
    def insert_alert(self, data: Dict) -> str:
        return self.db.insert_alert(data)

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict]:
        return self.db.get_alert_by_id(alert_id)

    def get_alerts_paginated(self, query: Dict = None, page: int = 1, limit: int = 50) -> List[Dict]:
        return self.db.get_alerts_paginated(query=query, page=page, limit=limit)

    def get_alerts_count(self, query: Dict = None) -> int:
        return self.db.get_alerts_count(query)

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
