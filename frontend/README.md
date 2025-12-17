# Accident Detection System - Frontend

Modern Next.js frontend for the Real-Time CCTV Accident Detection System.

## 🚀 Features

- **Dashboard**: Real-time overview with statistics and charts
- **Camera Management**: Add, edit, and monitor CCTV cameras
- **Live Monitoring**: Real-time accident detection monitoring
- **Video Upload**: Upload and process CCTV videos
- **Detections**: View and filter accident detections
- **Alerts**: Test and manage alert notifications
- **Analytics**: Detailed analytics and insights
- **WebSocket Integration**: Real-time updates via Socket.IO

## 🛠️ Technology Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **TailwindCSS** - Utility-first CSS framework
- **Recharts** - Chart library
- **Socket.IO Client** - Real-time communication
- **Axios** - HTTP client
- **React Hot Toast** - Toast notifications
- **Lucide React** - Icon library

## 📋 Prerequisites

- Node.js 18+ 
- npm or yarn

## 🚀 Quick Start

1. **Install dependencies**:
```bash
npm install
```

2. **Configure environment variables**:
Create a `.env.local` file:
```bash
NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1
NEXT_PUBLIC_SOCKET_URL=http://localhost:5000
```

3. **Start development server**:
```bash
npm run dev
```

4. **Open your browser**:
Navigate to [http://localhost:3000](http://localhost:3000)

## 📁 Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── dashboard/         # Dashboard page
│   ├── cameras/           # Camera management pages
│   ├── detections/        # Detections listing page
│   ├── monitor/           # Live monitoring page
│   ├── upload/            # Video upload page
│   ├── alerts/            # Alert management page
│   ├── analytics/         # Analytics page
│   └── settings/          # Settings page
├── components/            # React components
│   ├── layout/           # Layout components (Sidebar, Header)
│   ├── ui/               # Reusable UI components
│   └── cameras/          # Camera-specific components
├── lib/                  # Utilities and API clients
│   ├── api.ts            # API client functions
│   ├── socket.ts         # WebSocket client
│   └── utils.ts          # Utility functions
└── public/               # Static assets
```

## 🔌 API Integration

The frontend integrates with the backend API through:

- **REST API**: All CRUD operations via Axios
- **WebSocket**: Real-time updates via Socket.IO
- **File Upload**: Multipart form data for video uploads

### API Endpoints Used

- `/api/v1/dashboard/*` - Dashboard data
- `/api/v1/cameras/*` - Camera management
- `/api/v1/detections` - Detection listing
- `/api/v1/inference/*` - Inference management
- `/api/v1/video/*` - Video upload
- `/api/v1/alert/*` - Alert management
- `/api/v1/system/*` - System health

## 🎨 UI Components

### Reusable Components

- **Button**: Styled button component with variants
- **StatCard**: Statistics display card
- **CameraModal**: Modal for adding/editing cameras

### Layout Components

- **Sidebar**: Navigation sidebar
- **Header**: Top header with search

## 🔄 Real-time Updates

The application uses WebSocket for real-time updates:

- **Accident Detection**: Real-time notifications when accidents are detected
- **Frame Updates**: Live video frame updates (if implemented)
- **System Status**: Real-time system status updates

## 🎯 Key Features

### Dashboard
- Overview statistics
- Interactive charts (daily/hourly detections)
- Recent accidents and alerts
- Auto-refresh every 30 seconds

### Camera Management
- List all cameras
- Add new cameras
- Edit camera details
- Delete cameras
- Start/stop inference
- View camera statistics

### Detections
- Filter by camera and type
- Pagination support
- Detailed detection information
- Severity indicators

### Live Monitor
- Start/stop real-time inference
- View active streams
- Real-time accident alerts

### Video Upload
- Drag-and-drop file upload
- Camera selection
- Upload progress
- Processing status

### Alerts
- Test alert system
- View alert history
- Configure alert settings

## 🚀 Building for Production

1. **Build the application**:
```bash
npm run build
```

2. **Start production server**:
```bash
npm start
```

## 🔧 Configuration

### Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:5000/api/v1)
- `NEXT_PUBLIC_SOCKET_URL`: WebSocket server URL (default: http://localhost:5000)

### TailwindCSS

The project uses TailwindCSS for styling. Configuration is in `tailwind.config.ts`.

## 📝 Development Guidelines

- Use TypeScript for all new files
- Follow the existing component structure
- Use TailwindCSS utility classes for styling
- Implement proper error handling
- Add loading states for async operations
- Use toast notifications for user feedback

## 🐛 Troubleshooting

### API Connection Issues
- Verify backend is running on the configured port
- Check CORS settings in backend
- Verify API URL in environment variables

### WebSocket Connection Issues
- Ensure Socket.IO server is running
- Check WebSocket URL configuration
- Verify network connectivity

### Build Errors
- Clear `.next` directory: `rm -rf .next`
- Reinstall dependencies: `rm -rf node_modules && npm install`
- Check TypeScript errors: `npm run lint`

## 📄 License

This project is part of the Accident Detection System and follows the same license.

