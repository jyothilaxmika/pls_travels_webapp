# GitHub Actions Setup for PLS Travels Android App

## 🚀 Automated Android APK Building

Your PLS Travels Android app is now configured for **automated building via GitHub Actions**!

## 📋 Setup Instructions

### 1. Create GitHub Repository
```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit: PLS Travels Driver App"

# Create GitHub repository and push
git branch -M main
git remote add origin https://github.com/yourusername/pls-travels-android.git
git push -u origin main
```

### 2. Configure GitHub Secrets

In your GitHub repository settings → Secrets and Variables → Actions, add these **Repository Secrets**:

#### Required for Release Builds:
- `ANDROID_KEYSTORE_BASE64` - Your Android signing keystore encoded in base64
- `ANDROID_KEY_ALIAS` - The key alias in your keystore  
- `ANDROID_KEY_PASSWORD` - Password for the signing key
- `ANDROID_KEYSTORE_PASSWORD` - Password for the keystore file

#### How to Generate Keystore:
```bash
# Generate new keystore (do this locally, NOT in repository)
keytool -genkey -v -keystore pls-travels-release.keystore -alias pls-travels -keyalg RSA -keysize 2048 -validity 10000

# Convert to base64 for GitHub secrets
base64 -i pls-travels-release.keystore | pbcopy  # macOS
base64 -i pls-travels-release.keystore | xclip   # Linux
```

### 3. Automated Build Triggers

The GitHub Actions workflow automatically triggers on:

#### **Pull Requests** → Debug Build + Tests
- ✅ Runs lint checks and unit tests
- ✅ Creates debug APK for testing
- ✅ No signing required

#### **Push to Main** → Release Candidate
- ✅ Creates signed release APK
- ✅ Stores as GitHub artifact
- ✅ Ready for internal testing

#### **Git Tags (v*)** → Production Release
```bash
# Create production release
git tag v1.0.0
git push origin v1.0.0
```
- ✅ Creates signed release APK
- ✅ Generates GitHub Release with APK download
- ✅ Includes ProGuard mapping for crash analysis
- ✅ Ready for Google Play Store upload

## 🔄 Build Pipeline Overview

### Stage 1: Quality Checks (All PRs)
1. **Android Lint** - Code quality analysis
2. **Unit Tests** - Fast automated testing  
3. **Debug APK** - Artifact for manual testing

### Stage 2: Release Build (Main branch)
1. **Decode Signing Keys** - From GitHub secrets
2. **Signed APK Generation** - Production-ready build
3. **ProGuard Mapping** - For crash symbolication
4. **Artifact Upload** - Store build outputs

### Stage 3: GitHub Release (Tags)
1. **Create Release** - Automatic GitHub release
2. **APK Attachment** - Download ready APK
3. **Release Notes** - Generated changelog
4. **Version Management** - Semantic versioning

## 📦 Build Artifacts

### Available Downloads:
- **Debug APK** - `app-debug.apk` (PR builds)
- **Release APK** - `pls-travels-driver-v1.0.0.apk` (Tagged releases)
- **ProGuard Mapping** - `proguard-mapping-v1.0.0.txt` (Release analysis)
- **Test Reports** - Lint results and unit test output

## 🔒 Security Features

### ✅ Secrets Management
- Signing keys stored securely in GitHub Secrets
- No keystore files committed to repository
- Environment-based configuration

### ✅ Build Security  
- Signed APKs for production releases
- ProGuard obfuscation enabled
- Certificate pinning configured for API calls

### ✅ Access Control
- Private repository recommended (contains business logic)
- Protected main branch (optional)
- Environment protection for production builds

## 🎯 Next Steps

### Immediate Actions:
1. **Create GitHub Repository** and push your code
2. **Generate Android Keystore** and configure secrets
3. **Test the pipeline** by creating a pull request

### Weekly Releases:
```bash
# Regular release cycle
git tag v1.0.1
git push origin v1.0.1
# → Automatic APK build and GitHub release
```

### Google Play Store:
1. Download signed APK from GitHub releases  
2. Upload to Google Play Console
3. Configure internal testing → production rollout

## 🏆 Benefits of This Setup

**✅ Automated Quality** - Every code change tested automatically  
**✅ Consistent Builds** - Same environment every time  
**✅ Secure Signing** - Keys safely managed in GitHub  
**✅ Release Management** - Organized versioning and distribution  
**✅ Team Collaboration** - Multiple developers, one build system  

Your PLS Travels Android app is now **enterprise-ready** with professional CI/CD! 🚀