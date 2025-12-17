# Quick Start Guide

## Installation Steps

1. **Navigate to frontend directory**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Create environment file**:
Create `.env.local` with:
```
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
NEXT_PUBLIC_SOCKET_URL=http://localhost:5000
```

4. **Start development server**:
```bash
npm run dev
```

5. **Open browser**:
Navigate to http://localhost:3000

## Backend Setup

Make sure the backend is running on port 5000:

```bash
cd ../backend
python app.py
```

## Features Overview

### Dashboard (`/dashboard`)
- Real-time statistics
- Interactive charts
- Recent accidents and alerts

### Cameras (`/cameras`)
- View all cameras
- Add new cameras
- Edit/delete cameras
- Start/stop inference

### Detections (`/detections`)
- View all detections
- Filter by camera and type
- Pagination support

### Live Monitor (`/monitor`)
- Start real-time monitoring
- View active streams
- Real-time accident alerts

### Video Upload (`/upload`)
- Upload CCTV videos
- Select target camera
- Monitor processing

### Alerts (`/alerts`)
- Test alert system
- View alert history
- Configure alerts

### Analytics (`/analytics`)
- Detailed charts
- Camera distribution
- Accident heatmap

### Settings (`/settings`)
- System health
- Configuration

## Troubleshooting

**Port already in use?**
- Change port: `PORT=3001 npm run dev`

**API connection errors?**
- Verify backend is running
- Check API URL in `.env.local`
- Verify CORS settings in backend

**WebSocket errors?**
- Ensure Socket.IO server is running
- Check WebSocket URL in `.env.local`

