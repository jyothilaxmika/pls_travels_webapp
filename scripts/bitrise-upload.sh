#!/bin/bash

# Bitrise API Upload Script for PLS Travels Android App
# Uploads APK/AAB files to Bitrise for distribution

set -e

# Configuration
BITRISE_APP_ID="30904a3f-00ca-4345-b519-e252c693a33a"
BITRISE_API_BASE="https://api.bitrise.io/release-management/v1"

# Check required environment variables
if [ -z "$BITRISE_AUTH_TOKEN" ]; then
    echo "❌ Error: BITRISE_AUTH_TOKEN environment variable is required"
    exit 1
fi

if [ -z "$1" ]; then
    echo "❌ Error: File path is required"
    echo "Usage: $0 <file_path> [artifact_name]"
    echo "Example: $0 app/build/outputs/apk/release/app-release.apk PLS_Travels_v1.0"
    exit 1
fi

FILE_PATH="$1"
ARTIFACT_NAME="${2:-PLS_Travels_$(date +%Y%m%d_%H%M%S)}"

# Validate file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "❌ Error: File not found: $FILE_PATH"
    exit 1
fi

# Get file info
FILE_NAME=$(basename "$FILE_PATH")
FILE_SIZE=$(stat -c%s "$FILE_PATH" 2>/dev/null || stat -f%z "$FILE_PATH" 2>/dev/null)
FILE_EXT="${FILE_NAME##*.}"

echo "📱 Uploading PLS Travels Android App..."
echo "   File: $FILE_NAME"
echo "   Size: $FILE_SIZE bytes"
echo "   Type: $FILE_EXT"

# Generate unique artifact UUID
NEW_ARTIFACT_UUID=$(uuidgen 2>/dev/null || python3 -c "import uuid; print(uuid.uuid4())")

echo "🔑 Generated artifact UUID: $NEW_ARTIFACT_UUID"

# Step 1: Get upload URL
echo "📡 Step 1: Getting upload URL..."
UPLOAD_RESPONSE=$(curl -s -H "Authorization: $BITRISE_AUTH_TOKEN" \
    "$BITRISE_API_BASE/connected-apps/$BITRISE_APP_ID/installable-artifacts/$NEW_ARTIFACT_UUID/upload-url?file_name=$FILE_NAME&file_size_bytes=$FILE_SIZE")

# Check if upload URL request was successful
if echo "$UPLOAD_RESPONSE" | grep -q '"upload_url"'; then
    UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['upload_url'])")
    echo "✅ Upload URL obtained"
else
    echo "❌ Failed to get upload URL"
    echo "Response: $UPLOAD_RESPONSE"
    exit 1
fi

# Step 2: Upload file
echo "⬆️  Step 2: Uploading file..."

# Set content type based on file extension
if [ "$FILE_EXT" = "aab" ]; then
    CONTENT_TYPE="application/x-authorware-bin"
elif [ "$FILE_EXT" = "apk" ]; then
    CONTENT_TYPE="application/vnd.android.package-archive"
else
    echo "❌ Unsupported file type: $FILE_EXT"
    exit 1
fi

# Upload the file
UPLOAD_STATUS=$(curl -s -w "%{http_code}" -o /dev/null \
    -X "PUT" \
    -H "Content-Type: $CONTENT_TYPE" \
    -H "X-Goog-Content-Length-Range: 0,$FILE_SIZE" \
    --upload-file "$FILE_PATH" \
    "$UPLOAD_URL")

if [ "$UPLOAD_STATUS" = "200" ]; then
    echo "✅ File uploaded successfully"
else
    echo "❌ Upload failed with status: $UPLOAD_STATUS"
    exit 1
fi

# Step 3: Check status
echo "🔍 Step 3: Checking upload status..."
STATUS_RESPONSE=$(curl -s -H "Authorization: $BITRISE_AUTH_TOKEN" \
    "$BITRISE_API_BASE/connected-apps/$BITRISE_APP_ID/installable-artifacts/$NEW_ARTIFACT_UUID/status")

echo "📊 Upload Status Response:"
echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "$STATUS_RESPONSE"

# Generate sharing info
SHARING_URL="https://bitrise.io/artifacts/$NEW_ARTIFACT_UUID"

echo ""
echo "🎉 PLS Travels Android App Upload Complete!"
echo "📱 Artifact Name: $ARTIFACT_NAME"
echo "🆔 Artifact UUID: $NEW_ARTIFACT_UUID"
echo "🔗 Sharing URL: $SHARING_URL"
echo ""
echo "📲 Share this link with your Chennai & Bangalore drivers to download the app!"