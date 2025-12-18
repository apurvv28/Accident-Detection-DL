'use client';

import { useState, useRef, useEffect } from 'react';
import { videoApi, detectionApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Upload as UploadIcon, FileVideo, CheckCircle, RefreshCw, Eye } from 'lucide-react';
import toast from 'react-hot-toast';
import Link from 'next/link';
import { formatDate } from '@/lib/utils';

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<any>(null);
  const [recentDetections, setRecentDetections] = useState<any[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchRecentDetections();
  }, []);

  useEffect(() => {
    if (videoId) {
      const interval = setInterval(async () => {
        try {
          const statusRes = await videoApi.getStatus(videoId);
          // API returns { status, data: { processing_status, ... } }
          const statusData = statusRes.data?.data ?? statusRes.data;
          setProcessingStatus(statusData);
          
          // Refresh detections and stop polling when processing is complete
          if (statusData.processing_status === 'completed') {
            fetchRecentDetections();
            // stop further polling for this video
            setVideoId(null);
          }
        } catch (error) {
          console.error('Failed to check status');
        }
      }, 5000); // Check every 5 seconds

      return () => clearInterval(interval);
    }
  }, [videoId]);

  const fetchRecentDetections = async () => {
    try {
      const response = await detectionApi.getAll({ limit: 5, page: 1 });
      setRecentDetections(response.data.detections || []);
    } catch (error) {
      console.error('Failed to load recent detections');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/quicktime'];
      if (!allowedTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|mkv)$/i)) {
        toast.error('Invalid file type. Please upload MP4, AVI, MOV, or MKV files.');
        return;
      }
      setSelectedFile(file);
      setUploaded(false);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error('Please select a video file');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('video', selectedFile);
      formData.append('camera_id', 'default_upload_camera'); // Static camera ID
      formData.append('metadata', JSON.stringify({ uploaded_at: new Date().toISOString() }));

      const response = await videoApi.upload(formData);
      toast.success('Video uploaded successfully. Processing started.');
      setUploaded(true);
      setVideoId(response.data.video_id);
      setProcessingStatus({
        processing_status: 'in_progress',
        video_id: response.data.video_id
      });
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      // Start checking status
      fetchRecentDetections();
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Failed to upload video');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Video Upload</h1>
        <p className="text-gray-600 mt-1">Upload CCTV videos for accident detection analysis. Videos will be automatically processed.</p>
      </div>

      <div className="card max-w-2xl">
        <div className="space-y-6">
          <div>
            <label className="label">Select Video File *</label>
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary-500 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/avi,video/mov,video/mkv"
                onChange={handleFileSelect}
                className="hidden"
              />
              {selectedFile ? (
                <div className="space-y-2">
                  <FileVideo className="h-12 w-12 text-primary-600 mx-auto" />
                  <p className="font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-sm text-gray-600">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <UploadIcon className="h-12 w-12 text-gray-400 mx-auto" />
                  <p className="text-gray-600">
                    Click to select or drag and drop
                  </p>
                  <p className="text-sm text-gray-500">
                    MP4, AVI, MOV, MKV (Max 500MB)
                  </p>
                </div>
              )}
            </div>
          </div>

          {uploaded && processingStatus && (
            <div className="space-y-3">
              <div className={`flex items-center space-x-2 p-4 rounded-lg ${
                processingStatus.processing_status === 'completed'
                  ? (processingStatus.accident_detected ? 'bg-red-50 text-red-800' : 'bg-success-50 text-success-800')
                  : 'bg-blue-50 text-blue-800'
              }`}>
                {processingStatus.processing_status === 'completed' ? (
                  <CheckCircle className="h-5 w-5" />
                ) : (
                  <RefreshCw className="h-5 w-5 animate-spin" />
                )}
                <div className="flex-1">
                  <span className="font-medium">
                    {processingStatus.processing_status === 'completed'
                      ? (processingStatus.accident_detected ? 'Accident detected!' : 'No accident detected')
                      : 'Processing in progress...'}
                  </span>
                  {processingStatus.accident_detected && processingStatus.accidents_detected !== undefined && (
                    <p className="text-sm mt-1">
                      Accidents detected: {processingStatus.accidents_detected}
                    </p>
                  )}
                </div>
              </div>
              {processingStatus.processing_status === 'completed' && (
                <Link href="/detections">
                  <Button className="w-full">
                    <Eye className="h-4 w-4 mr-2" />
                    View Detections
                  </Button>
                </Link>
              )}
            </div>
          )}

          <Button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            className="w-full"
          >
            {uploading ? 'Uploading...' : 'Upload Video'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Upload Guidelines</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li>• Supported formats: MP4, AVI, MOV, MKV</li>
            <li>• Maximum file size: 500MB</li>
            <li>• Videos will be processed asynchronously</li>
            <li>• Processing status will be shown above</li>
            <li>• Ensure the video contains clear footage for better detection accuracy</li>
            <li>• Results will appear in the Detections page after processing</li>
          </ul>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Detections</h3>
          <div className="space-y-2">
            {recentDetections.length === 0 ? (
              <p className="text-gray-500 text-center py-4 text-sm">No detections yet</p>
            ) : (
              recentDetections.slice(0, 5).map((detection) => (
                <div key={detection.detection_id} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {detection.is_accident ? 'Accident Detected' : 'Detection'}
                      </p>
                      <p className="text-xs text-gray-600">
                        {formatDate(detection.timestamp)}
                      </p>
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
            {recentDetections.length > 0 && (
              <Link href="/detections">
                <Button variant="secondary" className="w-full mt-3">
                  View All Detections
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

