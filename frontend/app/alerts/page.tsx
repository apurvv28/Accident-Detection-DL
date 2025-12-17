'use client';

import { useEffect, useState } from 'react';
import { alertApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Bell, Send, Settings, History } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatDate } from '@/lib/utils';

export default function AlertsPage() {
  const [activeTab, setActiveTab] = useState<'test' | 'history' | 'config'>('test');
  const [testData, setTestData] = useState({
    alert_type: 'tts',
    message: 'Test alert from Accident Detection System',
    phone_numbers: [] as string[],
  });
  const [phoneNumber, setPhoneNumber] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchHistory = async () => {
    try {
      const response = await alertApi.getHistory(1, 50);
      setHistory(response.data.alerts || []);
    } catch (error) {
      console.error('Failed to load alert history');
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await alertApi.getConfig();
      setConfig(response.data.config);
    } catch (error) {
      console.error('Failed to load alert config');
    }
  };

  useEffect(() => {
    if (activeTab === 'history') fetchHistory();
    if (activeTab === 'config') fetchConfig();
  }, [activeTab]);

  const handleTestAlert = async () => {
    setLoading(true);
    try {
      const response = await alertApi.test(testData);
      toast.success('Alert test initiated');
      console.log('Test result:', response.data);
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to test alert');
    } finally {
      setLoading(false);
    }
  };

  const handleAddPhone = () => {
    if (phoneNumber && !testData.phone_numbers.includes(phoneNumber)) {
      setTestData({
        ...testData,
        phone_numbers: [...testData.phone_numbers, phoneNumber],
      });
      setPhoneNumber('');
    }
  };

  const handleRemovePhone = (phone: string) => {
    setTestData({
      ...testData,
      phone_numbers: testData.phone_numbers.filter(p => p !== phone),
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Alerts</h1>
        <p className="text-gray-600 mt-1">Manage and test alert notifications</p>
      </div>

      <div className="flex space-x-2 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('test')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'test'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Bell className="h-4 w-4 inline mr-2" />
          Test Alert
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'history'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <History className="h-4 w-4 inline mr-2" />
          History
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'config'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Settings className="h-4 w-4 inline mr-2" />
          Configuration
        </button>
      </div>

      {activeTab === 'test' && (
        <div className="card max-w-2xl">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Test Alert System</h3>
          <div className="space-y-4">
            <div>
              <label className="label">Alert Type</label>
              <select
                value={testData.alert_type}
                onChange={(e) => setTestData({ ...testData, alert_type: e.target.value })}
                className="input"
              >
                <option value="tts">TTS (Text-to-Speech)</option>
                <option value="voice">Voice Call</option>
                <option value="sms">SMS</option>
                <option value="all">All Types</option>
              </select>
            </div>

            <div>
              <label className="label">Message</label>
              <textarea
                value={testData.message}
                onChange={(e) => setTestData({ ...testData, message: e.target.value })}
                className="input"
                rows={4}
              />
            </div>

            {(testData.alert_type === 'voice' || testData.alert_type === 'sms' || testData.alert_type === 'all') && (
              <div>
                <label className="label">Phone Numbers</label>
                <div className="flex space-x-2 mb-2">
                  <input
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="+1234567890"
                    className="input flex-1"
                  />
                  <Button variant="secondary" onClick={handleAddPhone}>
                    Add
                  </Button>
                </div>
                {testData.phone_numbers.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {testData.phone_numbers.map((phone) => (
                      <span
                        key={phone}
                        className="inline-flex items-center px-3 py-1 bg-gray-100 rounded-full text-sm"
                      >
                        {phone}
                        <button
                          onClick={() => handleRemovePhone(phone)}
                          className="ml-2 text-gray-500 hover:text-gray-700"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <Button onClick={handleTestAlert} disabled={loading} className="w-full">
              <Send className="h-4 w-4 mr-2" />
              {loading ? 'Sending...' : 'Send Test Alert'}
            </Button>
          </div>
        </div>
      )}

      {activeTab === 'history' && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Alert History</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Type</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Message</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Timestamp</th>
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Status</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-gray-500">
                      No alert history
                    </td>
                  </tr>
                ) : (
                  history.map((alert, idx) => (
                    <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-sm text-gray-900">{alert.type || 'N/A'}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">{alert.message || '-'}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {formatDate(alert.timestamp)}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                          {alert.status || 'Sent'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'config' && (
        <div className="card max-w-2xl">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Alert Configuration</h3>
          {config ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Min Confidence</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={config.min_confidence || 0.75}
                    className="input"
                    readOnly
                  />
                </div>
                <div>
                  <label className="label">Cooldown (minutes)</label>
                  <input
                    type="number"
                    value={config.cooldown_minutes || 5}
                    className="input"
                    readOnly
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="label">Enabled Alert Types</label>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.enable_tts_alerts !== false}
                      className="mr-2"
                      readOnly
                    />
                    TTS Alerts
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.enable_voice_alerts || false}
                      className="mr-2"
                      readOnly
                    />
                    Voice Alerts
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.enable_sms_alerts || false}
                      className="mr-2"
                      readOnly
                    />
                    SMS Alerts
                  </label>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">Loading configuration...</p>
          )}
        </div>
      )}
    </div>
  );
}

