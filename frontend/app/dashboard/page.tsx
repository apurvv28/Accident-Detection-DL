'use client';

import { useEffect, useState } from 'react';
import { dashboardApi } from '@/lib/api';
import { StatCard } from '@/components/ui/StatCard';
import { Button } from '@/components/ui/Button';
import { 
  Camera, 
  Activity, 
  AlertTriangle, 
  TrendingUp,
  RefreshCw
} from 'lucide-react';
import { formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface OverviewData {
  summary: {
    total_cameras: number;
    active_cameras: number;
    total_detections: number;
    detections_today: number;
    detection_change_percent: number;
    total_accidents: number;
    accidents_today: number;
    accident_change_percent: number;
    total_alerts: number;
    alerts_today: number;
  };
  recent_activity: {
    recent_accidents: any[];
    active_alerts: any[];
  };
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [charts, setCharts] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const [overviewRes, chartsRes] = await Promise.all([
        dashboardApi.getOverview(),
        dashboardApi.getCharts(7),
      ]);
      setOverview(overviewRes.data.overview);
      setCharts(chartsRes.data.charts);
    } catch (error: any) {
      toast.error('Failed to load dashboard data');
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
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
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Real-time system overview and statistics</p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {overview && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Total Cameras"
              value={overview.summary.total_cameras}
              icon={Camera}
              iconColor="text-blue-600"
            />
            <StatCard
              title="Active Cameras"
              value={overview.summary.active_cameras}
              icon={Activity}
              iconColor="text-success-600"
            />
            <StatCard
              title="Detections Today"
              value={overview.summary.detections_today}
              change={overview.summary.detection_change_percent}
              icon={TrendingUp}
              iconColor="text-purple-600"
            />
            <StatCard
              title="Accidents Today"
              value={overview.summary.accidents_today}
              change={overview.summary.accident_change_percent}
              icon={AlertTriangle}
              iconColor="text-danger-600"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {charts?.daily_totals && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Detections (Last 7 Days)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={charts.daily_totals.labels.map((label: string, idx: number) => ({
                    date: label,
                    detections: charts.daily_totals.detections[idx],
                    accidents: charts.daily_totals.accidents[idx],
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="detections" fill="#3b82f6" />
                    <Bar dataKey="accidents" fill="#ef4444" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {charts?.hourly_detections && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Hourly Detections (Last 24 Hours)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={charts.hourly_detections.labels.map((label: string, idx: number) => ({
                    hour: label,
                    detections: charts.hourly_detections.detections[idx],
                    accidents: charts.hourly_detections.accidents[idx],
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="detections" stroke="#3b82f6" strokeWidth={2} />
                    <Line type="monotone" dataKey="accidents" stroke="#ef4444" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Accidents</h3>
              <div className="space-y-3">
                {overview.recent_activity.recent_accidents?.length > 0 ? (
                  overview.recent_activity.recent_accidents.slice(0, 5).map((accident: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">Camera {accident.camera_id}</p>
                        <p className="text-sm text-gray-600">{formatDate(accident.timestamp)}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-danger-600">{(accident.confidence * 100).toFixed(1)}%</p>
                        <p className="text-sm text-gray-600">{accident.severity || 'Medium'}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No recent accidents</p>
                )}
              </div>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Active Alerts</h3>
              <div className="space-y-3">
                {overview.recent_activity.active_alerts?.length > 0 ? (
                  overview.recent_activity.active_alerts.slice(0, 5).map((alert: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">{alert.type || 'Alert'}</p>
                        <p className="text-sm text-gray-600">{formatDate(alert.timestamp)}</p>
                      </div>
                      <div className="text-right">
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">
                          Active
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No active alerts</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

