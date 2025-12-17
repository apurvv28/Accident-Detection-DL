'use client';

import { useEffect, useState } from 'react';
import { cameraApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Plus, Settings, Trash2, Eye } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';
import Link from 'next/link';
import { CameraModal } from '@/components/cameras/CameraModal';

interface Camera {
  camera_id: string;
  name: string;
  stream_url: string;
  status: string;
  location?: {
    latitude: number;
    longitude: number;
    address?: string;
  };
  detections_today?: number;
  created_at?: string;
}

export default function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);

  const fetchCameras = async () => {
    try {
      const response = await cameraApi.getAll();
      setCameras(response.data.cameras || []);
    } catch (error: any) {
      toast.error('Failed to load cameras');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const handleDelete = async (cameraId: string) => {
    if (!confirm('Are you sure you want to delete this camera?')) return;

    try {
      await cameraApi.delete(cameraId);
      toast.success('Camera deleted successfully');
      fetchCameras();
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to delete camera');
    }
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Cameras</h1>
          <p className="text-gray-600 mt-1">Manage and monitor CCTV cameras</p>
        </div>
        <Button onClick={() => { setSelectedCamera(null); setIsModalOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Add Camera
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cameras.map((camera) => (
          <div key={camera.camera_id} className="card">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{camera.name}</h3>
                <p className="text-sm text-gray-600 mt-1">ID: {camera.camera_id}</p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                camera.status === 'active' 
                  ? 'bg-success-100 text-success-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {camera.status}
              </span>
            </div>

            <div className="space-y-2 mb-4">
              <div className="text-sm">
                <span className="text-gray-600">Stream:</span>
                <span className="ml-2 text-gray-900 font-mono text-xs truncate block">
                  {camera.stream_url}
                </span>
              </div>
              {camera.location && (
                <div className="text-sm text-gray-600">
                  <span>Location:</span>
                  <span className="ml-2">
                    {camera.location.address || 
                     `${camera.location.latitude.toFixed(4)}, ${camera.location.longitude.toFixed(4)}`}
                  </span>
                </div>
              )}
              <div className="text-sm text-gray-600">
                <span>Detections Today:</span>
                <span className="ml-2 font-medium">{camera.detections_today || 0}</span>
              </div>
            </div>

            <div className="flex items-center space-x-2 pt-4 border-t border-gray-200">
              <Link href={`/cameras/${camera.camera_id}`}>
                <Button variant="secondary" size="sm">
                  <Eye className="h-4 w-4" />
                </Button>
              </Link>
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => { setSelectedCamera(camera); setIsModalOpen(true); }}
              >
                <Settings className="h-4 w-4" />
              </Button>
              <Button 
                variant="danger" 
                size="sm"
                onClick={() => handleDelete(camera.camera_id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      {cameras.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-gray-500 mb-4">No cameras configured</p>
          <Button onClick={() => { setSelectedCamera(null); setIsModalOpen(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            Add Your First Camera
          </Button>
        </div>
      )}

      <CameraModal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setSelectedCamera(null); }}
        onSave={fetchCameras}
        camera={selectedCamera}
      />
    </div>
  );
}

