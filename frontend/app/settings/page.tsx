'use client';

import { useEffect, useState } from 'react';
import { systemApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Save, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    try {
      const response = await systemApi.getHealth();
      setHealth(response.data);
    } catch (error) {
      console.error('Failed to load system health');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">System configuration and health</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">System Health</h3>
          {health ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Status</span>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  health.status === 'healthy' 
                    ? 'bg-success-100 text-success-800'
                    : 'bg-danger-100 text-danger-800'
                }`}>
                  {health.status || 'Unknown'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Database</span>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  health.database === 'connected'
                    ? 'bg-success-100 text-success-800'
                    : 'bg-danger-100 text-danger-800'
                }`}>
                  {health.database || 'Unknown'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Models</span>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                  health.models_loaded
                    ? 'bg-success-100 text-success-800'
                    : 'bg-danger-100 text-danger-800'
                }`}>
                  {health.models_loaded ? 'Loaded' : 'Not Loaded'}
                </span>
              </div>
              <Button variant="secondary" onClick={fetchHealth} className="w-full mt-4">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          ) : (
            <p className="text-gray-500">Loading health status...</p>
          )}
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">System Information</h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">API URL</span>
              <span className="text-gray-900 font-mono">
                {process.env.NEXT_PUBLIC_API_URL || 'Not configured'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Socket URL</span>
              <span className="text-gray-900 font-mono">
                {process.env.NEXT_PUBLIC_SOCKET_URL || 'Not configured'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Application Settings</h3>
        <p className="text-gray-500">Additional settings and configuration options will be available here.</p>
      </div>
    </div>
  );
}

