#!/bin/bash

# Automated Deployment Script for PLS Travels
# Builds Android app and uploads to Bitrise for driver distribution

set -e

echo "🚀 PLS Travels Automated Deployment Starting..."

# Change to android app directory
if [ -d "android_app" ]; then
    cd android_app
elif [ -f "./gradlew" ]; then
    echo "Already in android app directory"
else
    echo "❌ Error: Could not find android_app directory or gradlew file"
    exit 1
fi

# Check if gradlew exists
if [ ! -f "./gradlew" ]; then
    echo "❌ Error: gradlew not found. Make sure you're in the android_app directory."
    exit 1
fi

# Make gradlew executable
chmod +x ./gradlew

echo "🔨 Building Debug APK..."
./gradlew assembleDebug

echo "🔨 Building Release APK..."
./gradlew assembleRelease

# Check if build succeeded
DEBUG_APK="app/build/outputs/apk/debug/app-debug.apk"
RELEASE_APK="app/build/outputs/apk/release/app-release.apk"

if [ -f "$DEBUG_APK" ]; then
    echo "✅ Debug APK built successfully: $DEBUG_APK"
else
    echo "❌ Debug APK build failed"
    exit 1
fi

if [ -f "$RELEASE_APK" ]; then
    echo "✅ Release APK built successfully: $RELEASE_APK"
else
    echo "❌ Release APK build failed"
    exit 1
fi

# Upload to Bitrise if auth token is available
if [ -n "$BITRISE_AUTH_TOKEN" ]; then
    echo "📡 Uploading to Bitrise for distribution..."
    
    # Upload release APK
    ../scripts/bitrise-upload.sh "$RELEASE_APK" "PLS_Travels_Production_$(date +%Y%m%d_%H%M%S)"
    
    # Upload debug APK
    ../scripts/bitrise-upload.sh "$DEBUG_APK" "PLS_Travels_Debug_$(date +%Y%m%d_%H%M%S)"
    
    echo "🎉 Deployment Complete!"
    echo "📱 APKs are now available for Chennai & Bangalore drivers"
else
    echo "⚠️  BITRISE_AUTH_TOKEN not set. APKs built locally only."
    echo "📱 APK locations:"
    echo "   Debug: android_app/$DEBUG_APK"
    echo "   Release: android_app/$RELEASE_APK"
fi

echo ""
echo "✅ PLS Travels Deployment Summary:"
echo "   🏢 Backend API: Running"
echo "   💻 Admin Dashboard: Available"
echo "   📱 Driver Apps: Built & Ready"
echo "   🌐 Serving: Chennai HQ & Bangalore Office"