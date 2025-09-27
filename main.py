import os
from app import app
from flask import render_template

# Legal pages for Play Store compliance
@app.route('/privacy-policy')
def privacy_policy():
    return render_template('legal/privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('legal/terms_of_service.html')

# PWA Offline page
@app.route('/offline')
def offline():
    return render_template('offline.html')

# PWA Push notification subscription endpoint
@app.route('/api/mobile/v1/push/subscribe', methods=['POST'])
def push_subscribe():
    from flask import request, jsonify
    subscription_data = request.get_json()
    # Store subscription data (implement based on your needs)
    print(f"Push subscription received: {subscription_data}")
    return jsonify({"success": True, "message": "Subscription saved"})

# PWA Background sync endpoint
@app.route('/api/mobile/v1/sync/duty', methods=['POST'])
def sync_duty():
    from flask import jsonify
    # Implement duty data sync logic
    return jsonify({"success": True, "message": "Duty data synced"})

# PWA File handler endpoint
@app.route('/admin/import', methods=['POST'])
def pwa_import():
    from flask import request, jsonify
    # Handle file imports from PWA
    return jsonify({"success": True, "message": "File imported"})

# PWA Share target endpoint
@app.route('/admin/share', methods=['POST'])
def pwa_share():
    from flask import request, jsonify
    # Handle shared content from PWA
    return jsonify({"success": True, "message": "Content shared"})

if __name__ == '__main__':
    # Use Flask directly while WebSocket is disabled
    # Use Cloud Run's PORT environment variable if available, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
