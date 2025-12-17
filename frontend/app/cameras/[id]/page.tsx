'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { cameraApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { ArrowLeft } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';
import Link from 'next/link';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function CameraDetailPage() {
  const params = useParams();
  const cameraId = params.id as string;
  const [camera, setCamera] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [detections, setDetections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [cameraRes, statsRes, detectionsRes] = await Promise.all([
        cameraApi.getById(cameraId),
        cameraApi.getStats(cameraId, 7),
        cameraApi.getDetections(cameraId, 1, 10),
      ]);
      setCamera(cameraRes.data.camera);
      setStats(statsRes.data.stats);
      setDetections(detectionsRes.data.detections || []);
    } catch (error: any) {
      toast.error('Failed to load camera details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (cameraId) {
      fetchData();
    }
  }, [cameraId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!camera) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 mb-4">Camera not found</p>
        <Link href="/cameras">
          <Button variant="secondary">Back to Cameras</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/cameras">
            <Button variant="secondary" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{camera.name}</h1>
            <p className="text-gray-600 mt-1">Camera ID: {camera.camera_id}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Detections</h3>
          <p className="text-3xl font-bold text-gray-900">{stats?.total_detections || 0}</p>
        </div>
        <div className="card">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Accidents</h3>
          <p className="text-3xl font-bold text-danger-600">{stats?.total_accidents || 0}</p>
        </div>
        <div className="card">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Detections (Last 7 Days)</h3>
          <p className="text-3xl font-bold text-primary-600">{stats?.detections_last_n_days || 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Camera Details</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Status</span>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                camera.status === 'active'
                  ? 'bg-success-100 text-success-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {camera.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Stream URL</span>
              <span className="text-gray-900 font-mono text-xs">{camera.stream_url}</span>
            </div>
            {camera.location && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Latitude</span>
                  <span className="text-gray-900">{camera.location.latitude}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Longitude</span>
                  <span className="text-gray-900">{camera.location.longitude}</span>
                </div>
                {camera.location.address && (
                  <div>
                    <span className="text-gray-600">Address</span>
                    <p className="text-gray-900 mt-1">{camera.location.address}</p>
                  </div>
                )}
              </>
            )}
            {camera.created_at && (
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Created</span>
                <span className="text-gray-900">{formatDate(camera.created_at)}</span>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Detections</h3>
          <div className="space-y-2">
            {detections.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No detections yet</p>
            ) : (
              detections.map((detection) => (
                <div key={detection.detection_id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {detection.is_accident ? 'Accident' : 'Detection'}
                      </p>
                      <p className="text-xs text-gray-600">{formatDate(detection.timestamp)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        {(detection.confidence * 100).toFixed(1)}%
                      </p>
                      {detection.severity && (
                        <p className="text-xs text-gray-600">{detection.severity}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

