'use client';

import { useEffect, useState, useCallback } from 'react';
import { accidentApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';

interface Accident {
  id: string;
  timestamp: string;
  camera_id: string;
  severity: number;
  severity_percent: number;
  severity_level: 'low' | 'medium' | 'high' | 'critical';
  accident_type: string;
  description: string;
  location?: { latitude?: number; longitude?: number; address?: string };
  involved_vehicles: number;
  confidence: number;
  status: 'detected' | 'verified' | 'false_alarm' | 'resolved';
  video_url?: string;
  thumbnail_url?: string;
  alert_sent: boolean;
  auto_alerted: boolean;
}

interface AccidentStats {
  total: number;
  by_severity: { critical: number; high: number; medium: number; low: number };
  by_status: { detected: number; verified: number; resolved: number; false_alarm: number };
  auto_alerted: number;
}

const SEVERITY_COLORS = {
  critical: 'bg-red-600 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-green-500 text-white',
};

const STATUS_COLORS = {
  detected: 'bg-blue-100 text-blue-800',
  verified: 'bg-purple-100 text-purple-800',
  resolved: 'bg-green-100 text-green-800',
  false_alarm: 'bg-gray-100 text-gray-800',
};

export default function AccidentsPage() {
  const [accidents, setAccidents] = useState<Accident[]>([]);
  const [stats, setStats] = useState<AccidentStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [alertAccident, setAlertAccident] = useState<Accident | null>(null);
  
  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchAccidents = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, limit: 12 };
      if (severityFilter) params.severity_min = parseInt(severityFilter);
      if (statusFilter) params.status = statusFilter;

      const res = await accidentApi.getAll(params);
      const data = res.data.data || {};
      
      setAccidents(data.accidents || []);
      setTotalPages(data.pagination?.pages || 1);
    } catch (e) {
      console.error(e);
      toast.error('Failed to load accidents');
    } finally {
      setLoading(false);
    }
  }, [page, severityFilter, statusFilter]);

  const fetchStats = async () => {
    try {
      const res = await accidentApi.getStats();
      setStats(res.data.data || null);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchAccidents();
  }, [fetchAccidents]);

  useEffect(() => {
    fetchStats();
  }, []);

  const handleStatusChange = async (accidentId: string, newStatus: string) => {
    try {
      await accidentApi.updateStatus(accidentId, newStatus);
      toast.success(`Status updated to ${newStatus}`);
      fetchAccidents();
      fetchStats();
    } catch (e) {
      toast.error('Failed to update status');
    }
  };

  const handleSendAlert = async (accidentId: string, recipients: string[]) => {
    try {
      await accidentApi.sendAlert(accidentId, recipients);
      toast.success(`Alerts sent to: ${recipients.join(', ')}`);
      fetchAccidents();
      setShowAlertModal(false);
    } catch (e) {
      toast.error('Failed to send alerts');
    }
  };

  const openAlertModal = (accident: Accident) => {
    setAlertAccident(accident);
    setShowAlertModal(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Accident Detections</h1>
          <p className="text-gray-600 mt-1">View and manage detected accidents</p>
        </div>
        <Button onClick={() => { fetchAccidents(); fetchStats(); }}>
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-gray-500">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-600">Total Accidents</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-red-500">
            <div className="text-2xl font-bold text-red-600">{stats.by_severity.critical}</div>
            <div className="text-sm text-gray-600">Critical</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-orange-500">
            <div className="text-2xl font-bold text-orange-600">{stats.by_severity.high}</div>
            <div className="text-sm text-gray-600">High Severity</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500">
            <div className="text-2xl font-bold text-blue-600">{stats.by_status.detected}</div>
            <div className="text-sm text-gray-600">Pending Review</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border-l-4 border-purple-500">
            <div className="text-2xl font-bold text-purple-600">{stats.auto_alerted}</div>
            <div className="text-sm text-gray-600">Auto-Alerted</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow flex flex-wrap gap-4 items-center">
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">Severity:</label>
          <select
            value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
            className="border rounded-md px-3 py-1.5 text-sm"
          >
            <option value="">All</option>
            <option value="90">Critical (≥90%)</option>
            <option value="70">High (≥70%)</option>
            <option value="50">Medium (≥50%)</option>
            <option value="30">Low (≥30%)</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="border rounded-md px-3 py-1.5 text-sm"
          >
            <option value="">All</option>
            <option value="detected">Detected</option>
            <option value="verified">Verified</option>
            <option value="resolved">Resolved</option>
            <option value="false_alarm">False Alarm</option>
          </select>
        </div>
      </div>

      {/* Accidents Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full text-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-500">Loading accidents...</p>
          </div>
        ) : accidents.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <div className="text-6xl mb-4">🚗</div>
            <p className="text-gray-500">No accidents found</p>
          </div>
        ) : (
          accidents.map((accident) => (
            <div key={accident.id} className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow">
              {/* Video/Thumbnail */}
              <div className="relative aspect-video bg-gray-900">
                {accident.video_url ? (
                  <video
                    key={accident.id}
                    src={accident.video_url.startsWith('http') ? accident.video_url : accidentApi.getVideoUrl(accident.id)}
                    poster={accident.thumbnail_url ? accidentApi.getThumbnailUrl(accident.id) : undefined}
                    controls
                    playsInline
                    preload="metadata"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">
                    <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                )}
                {/* Severity Badge */}
                <div className={`absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-bold ${SEVERITY_COLORS[accident.severity_level]}`}>
                  {accident.severity_level.toUpperCase()} ({Math.round(accident.severity)}%)
                </div>
                {/* Auto-Alert Indicator */}
                {accident.auto_alerted && (
                  <div className="absolute top-2 left-2 px-2 py-1 rounded-full text-xs font-bold bg-red-600 text-white animate-pulse">
                    🚨 AUTO-ALERTED
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[accident.status]}`}>
                    {accident.status.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="text-xs text-gray-500">{formatDate(accident.timestamp)}</span>
                </div>

                <div>
                  <div className="text-sm font-medium text-gray-900">{accident.accident_type || 'Unknown Type'}</div>
                  <div className="text-xs text-gray-500">Camera: {accident.camera_id}</div>
                  <div className="text-xs text-gray-600 mt-1 line-clamp-2">{accident.description}</div>
                </div>

                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Vehicles: {accident.involved_vehicles}</span>
                  <span>Confidence: {Math.round(accident.confidence * 100)}%</span>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t">
                  <select
                    value={accident.status}
                    onChange={(e) => handleStatusChange(accident.id, e.target.value)}
                    className="flex-1 text-xs border rounded px-2 py-1"
                  >
                    <option value="detected">Detected</option>
                    <option value="verified">Verified</option>
                    <option value="resolved">Resolved</option>
                    <option value="false_alarm">False Alarm</option>
                  </select>
                  
                  {!accident.alert_sent && (
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => openAlertModal(accident)}
                      className="text-xs"
                    >
                      🚨 Alert
                    </Button>
                  )}
                  
                  {accident.alert_sent && (
                    <span className="text-xs text-green-600 flex items-center">
                      ✓ Alerted
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >
            Previous
          </Button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            disabled={page === totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </Button>
        </div>
      )}

      {/* Alert Modal */}
      {showAlertModal && alertAccident && (
        <AlertModal
          accident={alertAccident}
          onClose={() => setShowAlertModal(false)}
          onSend={handleSendAlert}
        />
      )}
    </div>
  );
}

// Alert Modal Component
function AlertModal({
  accident,
  onClose,
  onSend,
}: {
  accident: Accident;
  onClose: () => void;
  onSend: (accidentId: string, recipients: string[]) => void;
}) {
  const [selectedRecipients, setSelectedRecipients] = useState<string[]>(['police', 'ambulance']);

  useEffect(() => {
    // TTS Announcement
    const speak = () => {
      window.speechSynthesis.cancel();
      const text = `Alert. ${accident.severity_level} severity accident detected. Highest severity is ${Math.round(accident.severity)} percent. Confidence is ${Math.round(accident.confidence * 100)} percent.`;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      window.speechSynthesis.speak(utterance);
    };

    speak();

    return () => {
      window.speechSynthesis.cancel();
    };
  }, [accident]);

  const toggleRecipient = (recipient: string) => {
    setSelectedRecipients(prev =>
      prev.includes(recipient)
        ? prev.filter(r => r !== recipient)
        : [...prev, recipient]
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        <div className="bg-red-600 text-white px-6 py-4">
          <h3 className="text-xl font-bold flex items-center gap-2">
            <span className="text-2xl">🚨</span>
            Send Emergency Alert
          </h3>
          <p className="text-red-100 text-sm mt-1">Select authorities to notify</p>
        </div>
        
        <div className="p-6 space-y-4">
          <div className="space-y-3">
            {[
              { id: 'police', label: 'Police', icon: '👮', desc: 'Local police station' },
              { id: 'ambulance', label: 'Ambulance', icon: '🚑', desc: 'Emergency medical services' },
              { id: 'fire', label: 'Fire Station', icon: '🚒', desc: 'Fire and rescue services' },
            ].map(({ id, label, icon, desc }) => (
              <button
                key={id}
                onClick={() => toggleRecipient(id)}
                className={`w-full p-4 rounded-lg border-2 text-left transition-all ${
                  selectedRecipients.includes(id)
                    ? 'border-red-500 bg-red-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{icon}</span>
                  <div>
                    <div className="font-semibold text-gray-900">{label}</div>
                    <div className="text-sm text-gray-500">{desc}</div>
                  </div>
                  {selectedRecipients.includes(id) && (
                    <span className="ml-auto text-red-600 text-xl">✓</span>
                  )}
                </div>
              </button>
            ))}
          </div>

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="danger"
              className="flex-1"
              disabled={selectedRecipients.length === 0}
              onClick={() => onSend(accident.id, selectedRecipients)}
            >
              Send Alerts ({selectedRecipients.length})
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
