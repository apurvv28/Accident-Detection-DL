"""
Database Seeding Script
Populates initial data for development and testing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
from .mongodb_connector import MongoDBConnector
from .models import (
    CameraDocument, DetectionDocument, AlertDocument, 
    Location, BoundingBox, VehicleInfo, AlertType, AlertStatus,
    DetectionSeverity
)

def seed_database():
    """Seed the database with initial data"""
    
    print("🌱 Seeding database with initial data...")
    
    # Connect to database
    db = MongoDBConnector()
    
    if not db.test_connection():
        print("❌ Database connection failed")
        return
    
    # Clear existing data (optional - for development only)
    # Uncomment for fresh seeding
    # db.db.cameras.delete_many({})
    # db.db.detections.delete_many({})
    # db.db.alerts.delete_many({})
    
    # ========== SEED CAMERAS ==========
    
    cameras_data = [
        {
            "camera_id": "cam_001",
            "name": "Highway Entrance - North",
            "stream_url": "rtsp://admin:password@192.168.1.101:554/stream1",
            "location": {
                "latitude": 28.6139,
                "longitude": 77.2090,
                "address": "New Delhi, India"
            },
            "direction": 180,
            "status": "active",
            "resolution": "1920x1080",
            "fps": 25,
            "metadata": {
                "zone": "highway",
                "direction": "northbound"
            }
        },
        {
            "camera_id": "cam_002",
            "name": "City Center - Intersection",
            "stream_url": "rtsp://admin:password@192.168.1.102:554/stream1",
            "location": {
                "latitude": 28.6145,
                "longitude": 77.2095,
                "address": "Connaught Place, New Delhi"
            },
            "direction": 270,
            "status": "active",
            "resolution": "1280x720",
            "fps": 30,
            "metadata": {
                "zone": "city_center",
                "intersection": "main_crossing"
            }
        },
        {
            "camera_id": "cam_003",
            "name": "School Zone - West",
            "stream_url": "rtsp://admin:password@192.168.1.103:554/stream1",
            "location": {
                "latitude": 28.6125,
                "longitude": 77.2080,
                "address": "Near Delhi Public School"
            },
            "direction": 90,
            "status": "active",
            "resolution": "1920x1080",
            "fps": 20,
            "metadata": {
                "zone": "school",
                "speed_limit": "30 km/h"
            }
        },
        {
            "camera_id": "cam_004",
            "name": "Shopping Mall - Parking",
            "stream_url": "http://192.168.1.104:8080/video",
            "location": {
                "latitude": 28.6150,
                "longitude": 77.2100,
                "address": "Select Citywalk Mall"
            },
            "direction": 0,
            "status": "active",
            "resolution": "1280x720",
            "fps": 15,
            "metadata": {
                "zone": "parking",
                "mall": "select_citywalk"
            }
        },
        {
            "camera_id": "cam_005",
            "name": "Bridge - River View",
            "stream_url": "rtsp://admin:password@192.168.1.105:554/stream1",
            "location": {
                "latitude": 28.6110,
                "longitude": 77.2075,
                "address": "Yamuna Bridge"
            },
            "direction": 135,
            "status": "maintenance",
            "resolution": "2560x1440",
            "fps": 25,
            "metadata": {
                "zone": "bridge",
                "structure": "yamuna_bridge"
            }
        }
    ]
    
    cameras_seeded = 0
    for camera_data in cameras_data:
        try:
            # Check if camera already exists
            existing = db.get_camera(camera_data["camera_id"])
            if not existing:
                db.insert_camera(camera_data)
                cameras_seeded += 1
        except Exception as e:
            print(f"  ⚠️ Failed to seed camera {camera_data['camera_id']}: {e}")
    
    print(f"  ✅ Seeded {cameras_seeded} cameras")
    
    # ========== SEED DETECTIONS (Sample Data) ==========
    
    # Generate sample detections for the last 7 days
    detections_seeded = 0
    for day_offset in range(7):
        base_date = datetime.now() - timedelta(days=day_offset)
        
        # Generate 5-15 detections per day
        num_detections = random.randint(5, 15)
        
        for i in range(num_detections):
            camera_id = random.choice(["cam_001", "cam_002", "cam_003", "cam_004"])
            is_accident = random.random() < 0.3  # 30% chance of accident
            
            # Random time within the day
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            timestamp = base_date.replace(hour=hour, minute=minute, second=second)
            
            # Random location near camera
            camera = db.get_camera(camera_id)
            if camera and 'location' in camera:
                base_lat = camera['location']['latitude']
                base_lng = camera['location']['longitude']
            else:
                base_lat = 28.6139
                base_lng = 77.2090
            
            # Add small random offset
            lat_offset = random.uniform(-0.001, 0.001)
            lng_offset = random.uniform(-0.001, 0.001)
            
            detection_data = {
                "detection_id": f"det_{timestamp.strftime('%Y%m%d_%H%M%S')}_{i}",
                "camera_id": camera_id,
                "timestamp": timestamp,
                "confidence": random.uniform(0.6, 0.95),
                "is_accident": is_accident,
                "severity": random.choice(["low", "medium", "high", "critical"]),
                "location": {
                    "latitude": base_lat + lat_offset,
                    "longitude": base_lng + lng_offset,
                    "accuracy": random.uniform(10, 50)
                },
                "vehicles_involved": [
                    {
                        "type": random.choice(["car", "truck", "bus", "motorcycle"]),
                        "confidence": random.uniform(0.7, 0.95),
                        "bbox": {
                            "x": random.randint(100, 500),
                            "y": random.randint(100, 300),
                            "width": random.randint(50, 150),
                            "height": random.randint(50, 100)
                        }
                    }
                ],
                "bbox": {
                    "x": random.randint(100, 500),
                    "y": random.randint(100, 300),
                    "width": random.randint(100, 300),
                    "height": random.randint(100, 200)
                },
                "pedestrians_involved": random.randint(0, 2) if is_accident else 0,
                "model_version": "yolov8_accident_v1.0",
                "verified": random.random() < 0.5,
                "alert_sent": is_accident and random.random() < 0.7
            }
            
            try:
                db.insert_detection(detection_data)
                detections_seeded += 1
                
                # If it's an accident and alert was sent, create alert record
                if is_accident and detection_data["alert_sent"]:
                    alert_data = {
                        "alert_id": f"alert_{timestamp.strftime('%Y%m%d_%H%M%S')}",
                        "type": random.choice(["voice", "tts", "sms"]),
                        "status": "sent",
                        "detection_id": detection_data["detection_id"],
                        "camera_id": camera_id,
                        "message": f"Accident detected at {detection_data['location']['latitude']:.6f}, {detection_data['location']['longitude']:.6f}",
                        "recipients": {
                            "phone_numbers": ["+919876543210", "+919876543211"]
                        },
                        "delivery_attempts": 1,
                        "timestamp": timestamp + timedelta(seconds=30),
                        "sent_at": timestamp + timedelta(seconds=30)
                    }
                    
                    db.insert_alert(alert_data)
                    
            except Exception as e:
                print(f"  ⚠️ Failed to seed detection: {e}")
    
    print(f"  ✅ Seeded {detections_seeded} detections")
    
    # ========== SEED SYSTEM LOGS ==========
    
    logs_data = [
        {
            "level": "INFO",
            "component": "system",
            "message": "Accident Detection System started",
            "timestamp": datetime.now() - timedelta(minutes=30)
        },
        {
            "level": "INFO",
            "component": "database",
            "message": "Database connection established",
            "timestamp": datetime.now() - timedelta(minutes=29)
        },
        {
            "level": "INFO",
            "component": "inference",
            "message": "AI model loaded successfully",
            "timestamp": datetime.now() - timedelta(minutes=28)
        },
        {
            "level": "WARNING",
            "component": "camera",
            "camera_id": "cam_005",
            "message": "Camera stream connection timeout",
            "timestamp": datetime.now() - timedelta(minutes=25)
        },
        {
            "level": "INFO",
            "component": "alert",
            "message": "Alert system initialized",
            "timestamp": datetime.now() - timedelta(minutes=20)
        },
        {
            "level": "INFO",
            "component": "api",
            "message": "API server started on port 5000",
            "timestamp": datetime.now() - timedelta(minutes=15)
        },
        {
            "level": "ERROR",
            "component": "inference",
            "camera_id": "cam_002",
            "message": "Frame processing failed - corrupted frame data",
            "timestamp": datetime.now() - timedelta(minutes=10)
        },
        {
            "level": "INFO",
            "component": "inference",
            "camera_id": "cam_001",
            "detection_id": f"det_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
            "message": "Accident detected with confidence 0.87",
            "timestamp": datetime.now() - timedelta(minutes=5)
        }
    ]
    
    logs_seeded = 0
    for log_data in logs_data:
        try:
            db.insert_log(log_data)
            logs_seeded += 1
        except Exception as e:
            print(f"  ⚠️ Failed to seed log: {e}")
    
    print(f"  ✅ Seeded {logs_seeded} system logs")
    
    print("\n" + "="*50)
    print("🌿 Database seeding completed!")
    print("="*50)
    
    # Show summary
    print(f"\n📊 Database Summary:")
    print(f"  Cameras: {db.get_cameras_count()}")
    print(f"  Detections: {db.get_detections_count()}")
    print(f"  Accidents: {db.get_detections_count({'is_accident': True})}")
    print(f"  Alerts: {db.get_alerts_count()}")
    print(f"  System Logs: {db.db.system_logs.count_documents({})}")
    
    print(f"\n🚀 Database is ready!")
    print(f"   Connect with MongoDB Compass using:")
    print(f"   URI: mongodb://localhost:27017")
    print(f"   Database: accident_detection")

if __name__ == "__main__":
    seed_database()