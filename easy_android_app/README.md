# PLS TRAVELS - Easy Android App

A simple WebView wrapper Android app for PLS TRAVELS Fleet Management System.

## Features ✨
- **WebView Integration** - Your web app runs natively in Android
- **Native App Experience** - Back button support, proper navigation  
- **File Upload Support** - Camera and gallery access for document uploads
- **Location Services** - GPS tracking for driver duties
- **Offline Fallback** - Works with your PWA's offline capabilities
- **Small APK Size** - Minimal footprint (~2MB APK)

## How to Build 🔨

### Option 1: Android Studio (Recommended)
1. **Install Android Studio** from https://developer.android.com/studio
2. **Open Project** - File → Open → Select `easy_android_app` folder
3. **Sync Gradle** - Click "Sync Now" when prompted
4. **Build APK** - Build → Build Bundle(s)/APK(s) → Build APK(s)
5. **Install** - APK will be generated in `app/build/outputs/apk/debug/`

### Option 2: Command Line
```bash
cd easy_android_app
./gradlew assembleDebug
# APK generated in app/build/outputs/apk/debug/app-debug.apk
```

## App Configuration 🔧

### Change Web App URL
Edit `MainActivity.kt` line 15:
```kotlin
private val APP_URL = "https://your-new-domain.com"
```

### Update App Name/Icon
- **App Name**: Edit `app/src/main/res/values/strings.xml`
- **App Icon**: Replace files in `app/src/main/res/mipmap-*/ic_launcher.png`
- **Colors**: Edit `app/src/main/res/values/colors.xml`

## Installation 📱

1. **Enable Unknown Sources** on your Android device
2. **Transfer APK** to device via USB, email, or cloud storage
3. **Install APK** by tapping on it
4. **Open PLS TRAVELS** from app drawer

## Publishing to Play Store 🚀

1. **Generate Signed APK** in Android Studio (Build → Generate Signed Bundle)
2. **Create Play Store Account** ($25 one-time fee)
3. **Upload AAB/APK** to Play Console
4. **Complete Store Listing** with screenshots and descriptions
5. **Submit for Review** (usually takes 1-3 days)

## Technical Details 📋

- **Package**: com.plstravels.app  
- **Min SDK**: Android 7.0 (API 24)
- **Target SDK**: Android 14 (API 34)
- **Build Tools**: Kotlin + Android Gradle Plugin
- **Size**: ~2MB APK, ~4MB installed

## Troubleshooting 🔧

**App won't build?**
- Make sure Android Studio is updated
- Sync Gradle files (File → Sync Project with Gradle Files)
- Clean project (Build → Clean Project)

**Web app not loading?**
- Check internet connection
- Verify APP_URL is correct in MainActivity.kt
- Check if your web server allows mobile user agents

**File uploads not working?**  
- Grant Camera and Storage permissions when prompted
- Check AndroidManifest.xml has proper permissions

Your PLS TRAVELS Android app is ready to deploy! 🚛📱