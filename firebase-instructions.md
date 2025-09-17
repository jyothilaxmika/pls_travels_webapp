# Firebase Cloud Messaging Setup Instructions

## 🔥 Firebase Configuration Required

To enable push notifications in the PLS Travels app, you need to set up Firebase Cloud Messaging:

### Step 1: Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use existing one
3. Enable Firebase Cloud Messaging (FCM)

### Step 2: Generate Service Account Key
1. Go to Project Settings → Service accounts
2. Generate new private key
3. Save the JSON file as `firebase-service-account.json` in the root directory

### Step 3: Get Android App Configuration
1. Add Android app to Firebase project
2. Package name: `com.plstravels.driver`
3. Download `google-services.json` 
4. Place it in `android_app/app/` directory

### Step 4: Server Configuration
The `firebase_service.py` module is ready and will automatically:
- ✅ Initialize Firebase Admin SDK
- ✅ Handle FCM token registration
- ✅ Send targeted push notifications
- ✅ Manage invalid tokens automatically

### Step 5: Test Notifications
Once configured, the system supports:

**📱 Notification Types:**
- 🚗 Duty assignments with vehicle details
- 📋 Duty status updates
- 🚨 Emergency alerts (high priority)
- 📢 System messages
- 🔄 Silent background sync requests

**🎯 Targeting:**
- Individual drivers
- Multiple users (batch notifications)
- Branch-specific notifications

### Usage Examples:

```python
from firebase_service import send_push_notification, send_duty_notification

# Send duty assignment
send_duty_notification(
    driver_id=123,
    duty_id=456, 
    vehicle_registration="TN01AB1234",
    start_time="2025-09-17 09:00 AM"
)

# Send custom notification
send_push_notification(
    user_id=123,
    title="Payment Received",
    body="Your advance payment of ₹500 has been processed",
    notification_type="payment_update"
)
```

### 🔒 Security Features:
- ✅ Invalid token cleanup
- ✅ Error handling and logging
- ✅ User permission checks
- ✅ Data payload validation

The Firebase service is production-ready and integrates seamlessly with the Android app's FCM implementation!