from backend.app import create_app
import json

app = create_app()

endpoints = [
    ('GET', '/api/v1/system/health'),
    ('GET', '/api/v1/system/config'),
    ('GET', '/api/v1/inference/status'),
    ('GET', '/api/v1/cameras')
]

results = {}

with app.test_client() as client:
    for method, path in endpoints:
        try:
            resp = client.open(path, method=method)
            body = None
            try:
                body = resp.get_json()
            except Exception:
                body = resp.data.decode('utf-8', errors='replace')[:1000]
            results[path] = {'status_code': resp.status_code, 'body': body}
        except Exception as e:
            results[path] = {'error': str(e)}

    # Integration: create a camera and fetch it
    cam_payload = {
        'camera_id': 'test_cam_1',
        'name': 'Test Camera 1',
        'stream_url': 'file://test.mp4'
    }
    try:
        post_resp = client.post('/api/v1/cameras', json=cam_payload)
        results['/api/v1/cameras (POST)'] = {'status_code': post_resp.status_code, 'body': post_resp.get_json()}

        get_resp = client.get('/api/v1/cameras/test_cam_1')
        results['/api/v1/cameras/test_cam_1'] = {'status_code': get_resp.status_code, 'body': get_resp.get_json()}

        # Single-frame detection test (generate synthetic image)
        try:
            import numpy as np
            import cv2
            import io

            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, 'TEST', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 4, (255,255,255), 8)
            _, buf = cv2.imencode('.jpg', img)
            file_bytes = io.BytesIO(buf.tobytes())

            data = {
                'camera_id': 'test_cam_1',
                'frame': (file_bytes, 'frame.jpg')
            }

            detect_resp = client.post('/api/v1/inference/detect', data=data, content_type='multipart/form-data')
            try:
                detect_body = detect_resp.get_json()
            except Exception:
                detect_body = detect_resp.data.decode('utf-8', errors='replace')
            results['/api/v1/inference/detect'] = {'status_code': detect_resp.status_code, 'body': detect_body}
        except Exception as e:
            results['/api/v1/inference/detect'] = {'error': str(e)}

    except Exception as e:
        results['camera_integration'] = {'error': str(e)}

print(json.dumps(results, indent=2))
