import os
from app import app  # socketio temporarily disabled

if __name__ == '__main__':
    # Use Flask directly while WebSocket is disabled
    # Use Cloud Run's PORT environment variable if available, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
