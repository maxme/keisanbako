#!/bin/bash
# Create DMG installer for Keisanbako on macOS

set -e

echo "📦 Creating DMG installer..."

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    echo "❌ create-dmg not found. Install with:"
    echo "   brew install create-dmg"
    exit 1
fi

# Paths
APP_PATH="dist/Keisanbako.app"
DMG_PATH="dist/Keisanbako-0.1.0.dmg"
ICON_PATH="src/Keisanbako/resources/macos/keisanbako.icns"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ App not found at $APP_PATH"
    echo "   Run build_macos.sh first"
    exit 1
fi

# Clean up old DMG if exists
rm -f "$DMG_PATH"

# Create DMG with custom background and layout
create-dmg \
  --volname "Keisanbako 0.1.0" \
  --volicon "$ICON_PATH" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Keisanbako.app" 150 190 \
  --hide-extension "Keisanbako.app" \
  --app-drop-link 450 190 \
  "$DMG_PATH" \
  "$APP_PATH"

if [ -f "$DMG_PATH" ]; then
    echo "✅ DMG created successfully!"
    echo "📦 Location: $DMG_PATH"
    echo ""
    echo "To distribute:"
    echo "  1. Code sign: codesign -s - \"$DMG_PATH\""
    echo "  2. Notarize: xcrun altool --notarize-app -f \"$DMG_PATH\" ..."
    echo "  3. Staple: xcrun stapler staple \"$DMG_PATH\""
else
    echo "❌ Failed to create DMG"
    exit 1
fi
