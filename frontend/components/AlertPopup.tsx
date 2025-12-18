'use client';

import { useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { accidentApi } from '@/lib/api';
import toast from 'react-hot-toast';

interface AccidentAlert {
  event_id: string;
  type: string;
  severity: number;
  severity_percent: number;
  severity_level: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  camera_id: string;
  timestamp: string;
  requires_action: boolean;
  auto_alerted: boolean;
  video_url?: string;
  description?: string;
  location?: any;
}

interface AlertPopupProps {
  onClose?: () => void;
}

const SEVERITY_STYLES = {
  critical: {
    bg: 'bg-gradient-to-r from-red-600 to-red-700',
    border: 'border-red-400',
    pulse: 'animate-pulse',
    icon: '🚨',
  },
  high: {
    bg: 'bg-gradient-to-r from-orange-500 to-orange-600',
    border: 'border-orange-400',
    pulse: '',
    icon: '⚠️',
  },
  medium: {
    bg: 'bg-gradient-to-r from-yellow-500 to-yellow-600',
    border: 'border-yellow-400',
    pulse: '',
    icon: '⚡',
  },
  low: {
    bg: 'bg-gradient-to-r from-blue-500 to-blue-600',
    border: 'border-blue-400',
    pulse: '',
    icon: 'ℹ️',
  },
};

export default function AlertPopup({ onClose }: AlertPopupProps) {
  const [alerts, setAlerts] = useState<AccidentAlert[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [currentAlert, setCurrentAlert] = useState<AccidentAlert | null>(null);
  const [selectedRecipients, setSelectedRecipients] = useState<string[]>(['police', 'ambulance']);
  const [sending, setSending] = useState(false);

  // Initialize WebSocket connection
  useEffect(() => {
    const socketUrl = process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:5000';
    
    const newSocket = io(socketUrl, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });

    newSocket.on('accident_alert', (alert: AccidentAlert) => {
      console.log('Received accident alert:', alert);
      
      // Add to alerts list
      setAlerts(prev => [alert, ...prev].slice(0, 10)); // Keep last 10 alerts
      
      // Show toast notification
      const severity = alert.severity_level || 'medium';
      const style = SEVERITY_STYLES[severity];
      
      toast.custom((t) => (
        <div
          className={`${
            t.visible ? 'animate-enter' : 'animate-leave'
          } max-w-md w-full bg-white shadow-2xl rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 overflow-hidden`}
        >
          <div className={`w-2 ${style.bg}`} />
          <div className="flex-1 p-4">
            <div className="flex items-start">
              <span className="text-2xl mr-3">{style.icon}</span>
              <div className="flex-1">
                <p className="text-sm font-bold text-gray-900">
                  {severity.toUpperCase()} SEVERITY ACCIDENT
                </p>
                <p className="text-sm text-gray-500">
                  {alert.message}
                </p>
                {alert.auto_alerted && (
                  <p className="text-xs text-red-600 font-semibold mt-1">
                    🚨 Authorities auto-alerted
                  </p>
                )}
              </div>
            </div>
          </div>
          <div className="border-l border-gray-200 flex flex-col">
            <button
              onClick={() => {
                setCurrentAlert(alert);
                setShowAlertModal(true);
                toast.dismiss(t.id);
              }}
              className="flex-1 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
            >
              Alert
            </button>
            <button
              onClick={() => toast.dismiss(t.id)}
              className="flex-1 border-t border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Dismiss
            </button>
          </div>
        </div>
      ), {
        duration: 15000,
        position: 'top-right',
      });

      // Auto-show modal for critical alerts
      if (severity === 'critical' && !alert.auto_alerted) {
        setCurrentAlert(alert);
        setShowAlertModal(true);
      }
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, []);

  const handleSendAlert = async () => {
    if (!currentAlert || selectedRecipients.length === 0) return;
    
    setSending(true);
    try {
      await accidentApi.sendAlert(currentAlert.event_id, selectedRecipients);
      toast.success(`Emergency alerts sent to: ${selectedRecipients.join(', ')}`);
      setShowAlertModal(false);
      setCurrentAlert(null);
    } catch (error) {
      toast.error('Failed to send alerts. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const toggleRecipient = (recipient: string) => {
    setSelectedRecipients(prev =>
      prev.includes(recipient)
        ? prev.filter(r => r !== recipient)
        : [...prev, recipient]
    );
  };

  return (
    <>
      {/* Connection Status Indicator */}
      <div className="fixed bottom-4 right-4 z-40">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium shadow-lg ${
          isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          {isConnected ? 'Live Alerts Active' : 'Reconnecting...'}
        </div>
      </div>

      {/* Alert History Mini Panel */}
      {alerts.length > 0 && (
        <div className="fixed top-20 right-4 w-80 z-30">
          <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow-xl border border-gray-200 max-h-96 overflow-hidden">
            <div className="bg-gray-800 text-white px-4 py-2 text-sm font-semibold flex items-center justify-between">
              <span>🚨 Recent Alerts ({alerts.length})</span>
              <button
                onClick={() => setAlerts([])}
                className="text-gray-400 hover:text-white text-xs"
              >
                Clear
              </button>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {alerts.map((alert, idx) => {
                const style = SEVERITY_STYLES[alert.severity_level || 'medium'];
                return (
                  <div
                    key={`${alert.event_id}-${idx}`}
                    className="p-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => {
                      setCurrentAlert(alert);
                      setShowAlertModal(true);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span>{style.icon}</span>
                      <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${style.bg} text-white`}>
                        {alert.severity_level?.toUpperCase()}
                      </span>
                      {alert.auto_alerted && (
                        <span className="text-xs text-red-500">Auto-sent</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-700 mt-1">{alert.message}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Alert Modal */}
      {showAlertModal && currentAlert && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden transform transition-all">
            {/* Header */}
            <div className={`${SEVERITY_STYLES[currentAlert.severity_level || 'medium'].bg} ${SEVERITY_STYLES[currentAlert.severity_level || 'medium'].pulse} text-white px-6 py-5`}>
              <div className="flex items-center gap-3">
                <span className="text-4xl">{SEVERITY_STYLES[currentAlert.severity_level || 'medium'].icon}</span>
                <div>
                  <h3 className="text-2xl font-bold">
                    {currentAlert.severity_level?.toUpperCase()} ACCIDENT
                  </h3>
                  <p className="text-white/80 text-sm mt-1">
                    Severity: {Math.round(currentAlert.severity_percent || currentAlert.severity)}%
                  </p>
                </div>
              </div>
              {currentAlert.auto_alerted && (
                <div className="mt-3 bg-white/20 rounded-lg p-2 text-sm">
                  ✅ Authorities have been automatically notified
                </div>
              )}
            </div>

            {/* Content */}
            <div className="p-6 space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-700">{currentAlert.description || currentAlert.message}</p>
                <div className="mt-2 text-sm text-gray-500">
                  <span className="font-medium">Camera:</span> {currentAlert.camera_id}
                </div>
                <div className="text-sm text-gray-500">
                  <span className="font-medium">Time:</span>{' '}
                  {new Date(currentAlert.timestamp).toLocaleString()}
                </div>
              </div>

              {/* Recipients Selection */}
              {!currentAlert.auto_alerted && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">
                    Send Emergency Alert To:
                  </h4>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { id: 'police', label: 'Police', icon: '👮', color: 'blue' },
                      { id: 'ambulance', label: 'Ambulance', icon: '🚑', color: 'red' },
                      { id: 'fire', label: 'Fire', icon: '🚒', color: 'orange' },
                    ].map(({ id, label, icon, color }) => (
                      <button
                        key={id}
                        onClick={() => toggleRecipient(id)}
                        className={`p-4 rounded-xl border-2 text-center transition-all ${
                          selectedRecipients.includes(id)
                            ? `border-${color}-500 bg-${color}-50 ring-2 ring-${color}-200`
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <span className="text-3xl block mb-1">{icon}</span>
                        <span className="text-sm font-medium">{label}</span>
                        {selectedRecipients.includes(id) && (
                          <span className="block text-green-600 text-xs mt-1">✓ Selected</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowAlertModal(false);
                    setCurrentAlert(null);
                  }}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition"
                >
                  {currentAlert.auto_alerted ? 'Close' : 'Cancel'}
                </button>
                {!currentAlert.auto_alerted && (
                  <button
                    onClick={handleSendAlert}
                    disabled={selectedRecipients.length === 0 || sending}
                    className={`flex-1 px-4 py-3 rounded-lg font-medium text-white transition ${
                      selectedRecipients.length === 0 || sending
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-red-600 hover:bg-red-700'
                    }`}
                  >
                    {sending ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="animate-spin">⏳</span> Sending...
                      </span>
                    ) : (
                      `🚨 Send Alerts (${selectedRecipients.length})`
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

