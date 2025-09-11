from app import app  # socketio temporarily disabled

if __name__ == '__main__':
    # Use Flask directly while WebSocket is disabled
    app.run(host='0.0.0.0', port=5000, debug=False)
