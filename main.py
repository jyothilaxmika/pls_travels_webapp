import os
from app import create_app
from flask import render_template

# Create the app instance for gunicorn
app = create_app()

# Legal pages for Play Store compliance
@app.route('/privacy-policy')
def privacy_policy():
    return render_template('legal/privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    return render_template('legal/terms_of_service.html')

if __name__ == '__main__':
    # Use Flask directly while WebSocket is disabled
    # Use Cloud Run's PORT environment variable if available, otherwise default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
