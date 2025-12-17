'use client';

import { useState, useEffect } from 'react';
import { cameraApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { X } from 'lucide-react';
import toast from 'react-hot-toast';

interface CameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
  camera?: any;
}

export const CameraModal = ({ isOpen, onClose, onSave, camera }: CameraModalProps) => {
  const [formData, setFormData] = useState({
    camera_id: '',
    name: '',
    stream_url: '',
    status: 'active',
    location: {
      latitude: '',
      longitude: '',
      address: '',
    },
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (camera) {
      setFormData({
        camera_id: camera.camera_id || '',
        name: camera.name || '',
        stream_url: camera.stream_url || '',
        status: camera.status || 'active',
        location: {
          latitude: camera.location?.latitude?.toString() || '',
          longitude: camera.location?.longitude?.toString() || '',
          address: camera.location?.address || '',
        },
      });
    } else {
      setFormData({
        camera_id: '',
        name: '',
        stream_url: '',
        status: 'active',
        location: {
          latitude: '',
          longitude: '',
          address: '',
        },
      });
    }
  }, [camera, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        ...formData,
        location: {
          ...formData.location,
          latitude: formData.location.latitude ? parseFloat(formData.location.latitude) : undefined,
          longitude: formData.location.longitude ? parseFloat(formData.location.longitude) : undefined,
        },
      };

      if (camera) {
        await cameraApi.update(camera.camera_id, payload);
        toast.success('Camera updated successfully');
      } else {
        await cameraApi.create(payload);
        toast.success('Camera created successfully');
      }
      onSave();
      onClose();
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to save camera');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {camera ? 'Edit Camera' : 'Add Camera'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="label">Camera ID *</label>
            <input
              type="text"
              required
              value={formData.camera_id}
              onChange={(e) => setFormData({ ...formData, camera_id: e.target.value })}
              className="input"
              disabled={!!camera}
            />
          </div>

          <div>
            <label className="label">Camera Name *</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input"
            />
          </div>

          <div>
            <label className="label">Stream URL *</label>
            <input
              type="text"
              required
              value={formData.stream_url}
              onChange={(e) => setFormData({ ...formData, stream_url: e.target.value })}
              className="input"
              placeholder="rtsp:// or http://"
            />
          </div>

          <div>
            <label className="label">Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="input"
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Location (Optional)</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Latitude</label>
                <input
                  type="number"
                  step="any"
                  value={formData.location.latitude}
                  onChange={(e) => setFormData({
                    ...formData,
                    location: { ...formData.location, latitude: e.target.value }
                  })}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Longitude</label>
                <input
                  type="number"
                  step="any"
                  value={formData.location.longitude}
                  onChange={(e) => setFormData({
                    ...formData,
                    location: { ...formData.location, longitude: e.target.value }
                  })}
                  className="input"
                />
              </div>
            </div>
            <div className="mt-4">
              <label className="label">Address</label>
              <input
                type="text"
                value={formData.location.address}
                onChange={(e) => setFormData({
                  ...formData,
                  location: { ...formData.location, address: e.target.value }
                })}
                className="input"
              />
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : camera ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

