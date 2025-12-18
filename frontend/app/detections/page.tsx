'use client';

import { useEffect, useState } from 'react';
import { detectionApi, cameraApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Filter, RefreshCw } from 'lucide-react';
import { formatDate, formatRelativeTime, getSeverityColor } from '@/lib/utils';
import toast from 'react-hot-toast';

interface Detection {
  detection_id: string;
  camera_id: string;
  timestamp: string;
  confidence: number;
  is_accident: boolean;
  severity?: string;
  description?: string;
  location?: {
    latitude: number;
    longitude: number;
  };
}

export default function DetectionsPage() {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [cameras, setCameras] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    page: 1,
    limit: 50,
    camera_id: '',
    is_accident: '',
  });
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
    pages: 1,
  });

  const fetchDetections = async () => {
    setLoading(true);
    try {
      const params: any = {
        page: filters.page,
        limit: filters.limit,
      };
      if (filters.camera_id) params.camera_id = filters.camera_id;
      if (filters.is_accident !== '') params.is_accident = filters.is_accident === 'true';

      const response = await detectionApi.getAll(params);
      setDetections(response.data.detections || []);
      setPagination(response.data.pagination || pagination);
    } catch (error: any) {
      toast.error('Failed to load detections');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCameras = async () => {
    try {
      const response = await cameraApi.getAll();
      setCameras(response.data.cameras || []);
    } catch (error) {
      console.error('Failed to load cameras');
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  useEffect(() => {
    fetchDetections();
  }, [filters]);

  const handleFilterChange = (key: string, value: string) => {
    setFilters({ ...filters, [key]: value, page: 1 });
  };

  // Helper function to safely get severity color
  const getSafeSeverityColor = (severity?: string) => {
    if (!severity) return 'bg-gray-100 text-gray-800';
    return getSeverityColor(String(severity));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Detections</h1>
          <p className="text-gray-600 mt-1">View and filter accident detections</p>
        </div>
        <Button onClick={fetchDetections}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="card">
        <div className="flex items-center space-x-4 mb-4">
          <Filter className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Camera</label>
            <select
              value={filters.camera_id}
              onChange={(e) => handleFilterChange('camera_id', e.target.value)}
              className="input"
            >
              <option value="">All Cameras</option>
              {cameras.map((cam) => (
                <option key={cam.camera_id} value={cam.camera_id}>
                  {cam.name} ({cam.camera_id})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Type</label>
            <select
              value={filters.is_accident}
              onChange={(e) => handleFilterChange('is_accident', e.target.value)}
              className="input"
            >
              <option value="">All Detections</option>
              <option value="true">Accidents Only</option>
              <option value="false">Non-Accidents</option>
            </select>
          </div>
          <div>
            <label className="label">Items Per Page</label>
            <select
              value={filters.limit}
              onChange={(e) => handleFilterChange('limit', e.target.value)}
              className="input"
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">ID</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Camera</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Timestamp</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Confidence</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Type</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Severity</th>
                <th className="text-left py-3 px-4 font-semibold text-gray-900">Description</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
                  </td>
                </tr>
              ) : detections.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-gray-500">
                    No detections found
                  </td>
                </tr>
              ) : (
                detections.map((detection) => (
                  <tr key={detection.detection_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 text-sm font-mono text-gray-600">
                      {detection.detection_id.slice(0, 12)}...
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-900">{detection.camera_id}</td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      <div>{formatDate(detection.timestamp)}</div>
                      <div className="text-xs text-gray-500">{formatRelativeTime(detection.timestamp)}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        detection.confidence >= 0.8 
                          ? 'bg-danger-100 text-danger-800'
                          : detection.confidence >= 0.6
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {(detection.confidence * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        detection.is_accident
                          ? 'bg-danger-100 text-danger-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {detection.is_accident ? 'Accident' : 'Detection'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {detection.severity && (
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSafeSeverityColor(detection.severity)}`}>
                          {String(detection.severity)}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {detection.description || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {pagination.pages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              Showing {((pagination.page - 1) * pagination.limit) + 1} to{' '}
              {Math.min(pagination.page * pagination.limit, pagination.total)} of {pagination.total} results
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
                disabled={filters.page === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-gray-600">
                Page {pagination.page} of {pagination.pages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
                disabled={filters.page >= pagination.pages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}