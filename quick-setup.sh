#!/bin/bash

# PLS Travels - Quick Play Store Setup
# One-time setup for Play Store deployment secrets

set -e

echo "⚡ PLS Travels - Quick Play Store Setup"
echo "======================================"
echo ""
echo "This script will guide you through setting up Play Store deployment."
echo "You'll need to add secrets to GitHub repository settings."
echo ""

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

REPO_URL=$(git config --get remote.origin.url | sed 's/.*[\/:]//g' | sed 's/.git$//')
echo "📁 Repository: $REPO_URL"
echo ""

echo "🔑 Required GitHub Secrets:"
echo "=========================="
echo ""
echo "1. ANDROID_KEYSTORE_BASE64"
echo "   - Your Android keystore file encoded in base64"
echo "   - Generate: keytool -genkey -v -keystore upload-keystore.jks ..."
echo "   - Encode: base64 -i upload-keystore.jks | tr -d '\\n'"
echo ""
echo "2. ANDROID_KEY_ALIAS"
echo "   - Keystore alias (e.g., 'upload')"
echo ""
echo "3. ANDROID_KEY_PASSWORD"
echo "   - Password for the key alias"
echo ""
echo "4. ANDROID_KEYSTORE_PASSWORD" 
echo "   - Password for the keystore file"
echo ""
echo "5. PLAY_STORE_SERVICE_ACCOUNT_JSON"
echo "   - Google Play Console service account JSON"
echo "   - Create at: https://console.cloud.google.com"
echo "   - Enable Google Play Android Developer API"
echo ""

echo "📖 Detailed setup instructions:"
echo "   File: PLAY_STORE_SECRETS.md"
echo "   Contains step-by-step guide with commands"
echo ""

echo "🌐 Add secrets at:"
echo "   https://github.com/$REPO_URL/settings/secrets/actions"
echo ""

echo "✅ After adding secrets, use: ./deploy-playstore.sh"
echo ""
echo "🚀 That's it! Your app will auto-deploy to Play Store!"