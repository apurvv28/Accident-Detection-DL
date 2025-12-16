(The file is currently empty)
# Real-Time CCTV Accident Detection - Backend

This backend provides endpoints and services to process CCTV videos, run object detection and temporal analysis to detect accidents, store detections in MongoDB, and dispatch alerts (voice/TTS/SMS).

## Quick Setup

1. Create a Python 3.10+ virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file (example):

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=accident_detection
YOLO_MODEL_PATH=static/models/yolov8n.pt
TEMPORAL_MODEL_PATH=static/models/temporal_accident.pth
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM=
ALERT_PHONE_NUMBERS=+1234567890
```

4. Run the app:

```bash
python app.py
```

The app runs on port 5000 by default and exposes API under `/api/v1`.

## Important Endpoints

- POST `/api/v1/video/upload` – Upload video (multipart/form-data, fields: `video`, `camera_id`)
- POST `/api/v1/inference/start` – Start real-time inference (JSON body: `stream_url`, `camera_id`)
- GET  `/api/v1/detections` – List detections (query params: `page`, `limit`, `camera_id`, `is_accident`)
- POST `/api/v1/alert/test` – Test alert system (JSON body: `alert_type`, `message`, `phone_numbers`)
- GET  `/api/v1/cameras` – List cameras

## Notes

- If `ultralytics` (YOLOv8) or `torch` are not installed, the detector/analyzer will fall back to dummy behavior for testing.
- For Windows, `pyttsx3` is used for TTS playback; ensure audio is configured correctly.
- Use local MongoDB (Compass) and ensure `.env` MONGODB_URI points to it.
