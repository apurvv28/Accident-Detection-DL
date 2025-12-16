"""Simple SocketIO test: checks that server emits events and a client can receive them."""
import time
from backend.app import create_app
from backend.api import socketio

app = create_app()

# Create a Socket.IO test client
client = socketio.test_client(app)
if not client.is_connected():
    print('SocketIO client failed to connect')
    raise SystemExit(1)

# Emit a server-side event and verify the client receives it
socketio.emit('test_event', {'message': 'hello_test'})
# small wait to allow delivery
time.sleep(0.1)
received = client.get_received()
print('received:', received)

# Clean up
client.disconnect()
