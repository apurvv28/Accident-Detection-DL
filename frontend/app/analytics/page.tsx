'use client';

import { useEffect, useState } from 'react';
import { dashboardApi } from '@/lib/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { formatDate } from '@/lib/utils';

const COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6'];

export default function AnalyticsPage() {
  const [charts, setCharts] = useState<any>(null);
  const [heatmap, setHeatmap] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  const fetchData = async () => {
    try {
      const [chartsRes, heatmapRes] = await Promise.all([
        dashboardApi.getCharts(days),
        dashboardApi.getHeatmap(30),
      ]);
      setCharts(chartsRes.data.charts);
      setHeatmap(heatmapRes.data.heatmap);
    } catch (error) {
      console.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [days]);

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
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-600 mt-1">Detailed analytics and insights</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="input w-auto"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {charts && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {charts.daily_totals && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Totals</h3>
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

            {charts.hourly_detections && (
              <div className="card">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Hourly Detections</h3>
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

          {charts.camera_distribution && charts.camera_distribution.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Camera Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={charts.camera_distribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {charts.camera_distribution.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {heatmap && heatmap.points && heatmap.points.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Accident Heatmap</h3>
          <p className="text-sm text-gray-600 mb-4">
            {heatmap.total_points} accident points mapped
          </p>
          <div className="bg-gray-100 rounded-lg p-8 text-center">
            <p className="text-gray-500">Map visualization would be integrated here</p>
            <p className="text-sm text-gray-400 mt-2">
              Coordinates: {heatmap.points.slice(0, 5).map((p: any) => 
                `(${p.lat.toFixed(2)}, ${p.lng.toFixed(2)})`
              ).join(', ')}...
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

