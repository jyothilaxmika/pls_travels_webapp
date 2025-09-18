#!/bin/bash

# PLS Travels - Easy Auto Play Store Deploy
# Simple one-command deployment to Google Play Store

set -e

echo "🚀 PLS Travels - Easy Auto Deploy to Play Store"
echo "=============================================="

# Get current version or auto-increment
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/v//' || echo "1.0.0")
echo "📱 Current version: v$CURRENT_VERSION"

# Auto-increment patch version
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=$((${VERSION_PARTS[2]} + 1))
NEW_VERSION="$MAJOR.$MINOR.$PATCH"

echo "📈 New version: v$NEW_VERSION"
echo ""

# Ask for deployment track
echo "🎯 Choose deployment track:"
echo "1) Internal Testing (fast, 100 testers)"
echo "2) Alpha Testing (closed group)"
echo "3) Beta Testing (wider audience)" 
echo "4) Production (all users)"
echo ""
read -p "Enter choice (1-4) [1]: " TRACK_CHOICE
TRACK_CHOICE=${TRACK_CHOICE:-1}

case $TRACK_CHOICE in
    1) TRACK="internal" ;;
    2) TRACK="alpha" ;;
    3) TRACK="beta" ;;
    4) TRACK="production" ;;
    *) TRACK="internal" ;;
esac

echo "✅ Selected track: $TRACK"
echo ""

# Confirm deployment
echo "🔍 Deployment Summary:"
echo "   Version: v$NEW_VERSION"
echo "   Track: $TRACK"
echo "   App: PLS Travels Driver"
echo ""
read -p "Continue with deployment? (y/N): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo ""
echo "🏗️ Starting deployment process..."

# Create and push release tag
git tag "v$NEW_VERSION-release"
git push origin "v$NEW_VERSION-release"

echo "✅ Release tag created and pushed"
echo "🔄 GitHub Actions will now:"
echo "   1. Build signed AAB file"
echo "   2. Upload to Play Store ($TRACK track)"
echo "   3. Generate ProGuard mapping"
echo "   4. Create release artifacts"
echo ""
echo "📊 Monitor progress at:"
echo "   https://github.com/$(git config --get remote.origin.url | sed 's/.*[\/:]//g' | sed 's/.git$//')/actions"
echo ""
echo "🎉 Deployment initiated successfully!"
echo "⏱️  Expected time: 5-15 minutes"
echo ""
echo "📱 Once complete, check your Play Console:"
echo "   https://play.google.com/console/developers"