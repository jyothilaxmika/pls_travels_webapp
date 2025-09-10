from app import app, socketio

if __name__ == '__main__':
    # Use SocketIO for WebSocket support
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True, log_output=True)
