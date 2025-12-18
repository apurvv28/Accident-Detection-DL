# Real-Time CCTV Accident Detection System

A comprehensive AI-powered system for real-time accident detection from CCTV camera feeds, featuring a modern web interface, intelligent alerting, and comprehensive monitoring capabilities.

## 🚀 Features

### Core Functionality
- **Real-Time Detection**: AI-powered accident detection from live CCTV streams
- **Video Processing**: Upload and analyze video files for accident detection
- **Multi-Camera Support**: Manage and monitor multiple camera feeds simultaneously
- **Intelligent Alerts**: Configurable SMS, voice, and TTS notifications
- **Location Tracking**: GPS/location-based incident mapping

### Web Interface
- **Modern Dashboard**: Real-time system overview with interactive charts
- **Camera Management**: Add, configure, and monitor CCTV cameras
- **Live Monitoring**: Real-time video stream monitoring interface
- **Detection History**: Comprehensive detection event analysis
- **Alert Management**: Configure and test notification systems
- **System Monitoring**: Health monitoring and performance metrics
- **Audit Logs**: Detailed system activity logging

### Technical Features
- **WebSocket Integration**: Real-time updates and notifications
- **RESTful API**: Comprehensive API for all system operations
- **Responsive Design**: Mobile-friendly interface
- **Docker Support**: Containerized deployment
- **Database Integration**: MongoDB for data persistence
- **Scalable Architecture**: Microservices-ready design

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database      │
│   (React)       │◄──►│   (Flask)       │◄──►│   (MongoDB)     │
│                 │    │                 │    │                 │
│ • Dashboard     │    │ • API Server    │    │ • Detections    │
│ • Camera Mgmt   │    │ • AI Models     │    │ • Cameras       │
│ • Live Monitor  │    │ • WebSocket     │    │ • Alerts        │
│ • Alerts        │    │ • File Upload   │    │ • System Logs   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **Python 3.10+** - Core runtime
- **Flask** - Web framework
- **PyTorch** - Deep learning framework
- **YOLO (v11)** - Object detection (configurable via `YOLO_MODEL_PATH`)
- **OpenCV** - Computer vision library
- **MongoDB** - Database
- **Socket.IO** - Real-time communication
- **Twilio** - SMS/Voice alerts
- **TTS (gTTS / pyttsx3)** - Text-to-speech options (engine configurable via `TTS_ENGINE`) 

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Socket.IO Client** - Real-time updates
- **Recharts** - Data visualization
- **Axios** - HTTP client

### Infrastructure
- **Docker** - Containerization
- **Nginx** - Reverse proxy
- **Redis** - Caching (optional)

## 📋 Prerequisites

- **Docker & Docker Compose** (recommended)
- **Python 3.10+** (for local development)
- **Node.js 16+** (for frontend development)
- **MongoDB** (if not using Docker)

Note: The backend scripts and models assume Python 3.10+ for full compatibility.

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository**:
```bash
git clone <repository-url>
cd accident-detection-system
```

2. **Start the services**:
```bash
docker-compose up -d
```

3. **Access the application**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- API Documentation: http://localhost:5000/api/v1/system/health

### Manual Setup

#### Backend Setup

1. **Navigate to backend directory**:
```bash
cd backend
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Start MongoDB** (if not using Docker):
```bash
mongod --dbpath /path/to/your/db
```

6. **Run the backend**:
```bash
python app.py
```

#### Frontend Setup

1. **Navigate to frontend directory**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your API endpoints
```

4. **Start development server**:
```bash
npm start
```

## 📖 Usage Guide

### 1. Camera Setup
1. Navigate to **Cameras** page
2. Click **Add Camera**
3. Configure camera details:
   - Camera ID and name
   - RTSP/HTTP stream URL
   - Location (optional)
4. Test camera connection
5. Save configuration

### 2. Start Monitoring
1. Go to **Live Monitoring** page
2. Select cameras to monitor
3. Click **Start Monitoring**
4. View real-time detection results

### 3. Configure Alerts
1. Access **Alerts** page
2. Configure notification settings:
   - SMS alerts (Twilio)
   - Voice calls
   - TTS announcements
3. Test alert functionality
4. Set confidence thresholds

### 4. Video Analysis
1. Visit **Video Upload** page
2. Select target camera
3. Upload video files
4. Monitor processing status
5. Review detection results

### 5. System Monitoring
1. Check **Dashboard** for overview
2. Monitor **System** health
3. Review **Logs** for troubleshooting

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```bash
# Database
MONGODB_URI=mongodb://localhost:27017/accident_detection
REDIS_URL=redis://localhost:6379/0

# API Configuration
PORT=5000
FLASK_ENV=development
SECRET_KEY=your-secret-key

# AI Model Settings
# Path to object detection model (supports YOLOv8 or YOLOv11)
YOLO_MODEL_PATH=static/models/yolov8n.pt
IOU_THRESHOLD=0.45
MIN_CONFIDENCE=0.75
PROCESS_FPS=2
TARGET_FPS=10
FRAME_SKIP=3

# Temporal model (for accident sequence analysis)
TEMPORAL_MODEL_PATH=static/models/temporal_accident.pth
TEMPORAL_MODEL_URL=      # optional: URL to download the temporal model

# Default Location
DEFAULT_LATITUDE=28.6139
DEFAULT_LONGITUDE=77.2090

# Alert Settings
ALERT_COOLDOWN_MINUTES=5
ENABLE_VOICE_ALERTS=false
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-number
ALERT_PHONE_NUMBERS=+1234567890  # comma separated

# TTS Settings
TTS_ENGINE=gtts
TTS_LANGUAGE=en
```

#### Frontend (.env)
```bash
REACT_APP_API_URL=http://localhost:5000/api/v1
REACT_APP_SOCKET_URL=http://localhost:5000
GENERATE_SOURCEMAP=false
```

## 📊 API Documentation

### Core Endpoints

#### Dashboard
- `GET /api/v1/dashboard/overview` - System overview
- `GET /api/v1/dashboard/charts` - Chart data
- `GET /api/v1/dashboard/realtime` - Real-time updates

#### Cameras
- `GET /api/v1/cameras` - List cameras
- `POST /api/v1/cameras` - Add camera
- `GET /api/v1/cameras/{id}` - Get camera details
- `PUT /api/v1/cameras/{id}` - Update camera
- `DELETE /api/v1/cameras/{id}` - Delete camera
- `POST /api/v1/cameras/{id}/test` - Test camera connection / stream
- `GET /api/v1/cameras/{id}/detections` - Get detections for camera
- `GET /api/v1/cameras/{id}/stats` - Camera statistics

#### Video
- `POST /api/v1/video/upload` - Upload a video for analysis (multipart/form-data)
- `GET /api/v1/video/list` - List uploaded videos
- `GET /api/v1/video/{video_id}/status` - Check processing status

#### Inference
- `POST /api/v1/inference/start` - Start monitoring (JSON: `stream_url`, `camera_id`)
- `POST /api/v1/inference/stop/{camera_id}` - Stop monitoring
- `GET /api/v1/inference/status` - Get status
- `GET /api/v1/detections` - List detections (query: `page`, `limit`, `camera_id`, `is_accident`)

#### Accidents / Detections
- `GET /api/v1/accidents` - List detected accidents
- `GET /api/v1/accidents/{id}` - Get accident details
- `GET /api/v1/accidents/{id}/video` - Download recorded accident clip
- `GET /api/v1/accidents/{id}/thumbnail` - Get thumbnail image
- `PATCH /api/v1/accidents/{id}/status` - Update accident status
- `POST /api/v1/accidents/{id}/alert` - Re-send or trigger alerts for an accident
- `GET /api/v1/accidents/stats` - Aggregated accident statistics

#### Alerts
- `GET /api/v1/alert/config` - Get alert configuration
- `PUT /api/v1/alert/config` - Update alert configuration
- `POST /api/v1/alert/test` - Test alert sending
- `GET /api/v1/alert/history` - List sent alerts (pagination)
- `POST /api/v1/alert/resend/{alert_id}` - Re-send a past alert
- `GET /api/v1/alert/stats` - Alert delivery statistics

#### System
- `GET /api/v1/system/health` - System health
- `GET /api/v1/system/logs` - System logs
- `GET /api/v1/system/version` - Version info
- `GET /api/v1/system/config` - Current runtime configuration (read-only)

> WebSocket: `ws://localhost:5000` (Socket.IO) — used for realtime updates (detection events, status, alerts)

## 🔒 Security

### Authentication
- API token-based authentication
- Admin token for system operations
- CORS configuration for frontend

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection headers
- Secure file upload handling

### Network Security
- HTTPS support (production)
- Firewall configuration
- Rate limiting (recommended)

## 🚀 Deployment

### Production Deployment

1. **Configure environment variables**
2. **Set up SSL certificates**
3. **Configure reverse proxy**
4. **Deploy using Docker Compose**:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling Considerations

- **Load Balancing**: Use multiple backend instances
- **Database Scaling**: MongoDB replica sets
- **File Storage**: External storage for videos
- **CDN**: Static asset delivery
- **Monitoring**: Application performance monitoring

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📈 Monitoring & Maintenance

### Health Checks
- API health endpoints
- Database connectivity
- Model availability
- System resources

### Logging
- Application logs
- Access logs
- Error tracking
- Performance metrics

### Backup Strategy
- Database backups
- Configuration backups
- Model checkpoints
- User data exports

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Write comprehensive tests
- Update documentation
- Follow semantic versioning

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

### Community
- [GitHub Issues](https://github.com/your-repo/issues)
- [Discussions](https://github.com/your-repo/discussions)

### Commercial Support
For enterprise support and custom development, contact: support@yourcompany.com

## 🙏 Acknowledgments

- YOLOv8 by Ultralytics
- OpenCV community
- React and TypeScript communities
- All contributors and testers

---

**Built with ❤️ for safer roads and communities**