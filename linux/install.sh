#!/bin/bash
# Install Keisanbako on Linux

set -e

echo "📦 Installing Keisanbako..."

if [ ! -d "dist/Keisanbako" ]; then
    echo "❌ Built app not found. Run build_linux.sh first"
    exit 1
fi

# Copy app to /opt
echo "  Copying application..."
sudo mkdir -p /opt/Keisanbako
sudo cp -r dist/Keisanbako/* /opt/Keisanbako/

# Make executable
sudo chmod +x /opt/Keisanbako/Keisanbako

# Install desktop file
echo "  Installing desktop file..."
sudo cp linux/Keisanbako.desktop /usr/share/applications/

# Install icon
echo "  Installing icon..."
ICON_DIR="/usr/share/icons/hicolor"
for size in 16 32 48 64 128 256 512; do
    ICON_FILE="src/Keisanbako/resources/linux/keisanbako_${size}x${size}.png"
    if [ -f "$ICON_FILE" ]; then
        sudo mkdir -p "$ICON_DIR/${size}x${size}/apps"
        sudo cp "$ICON_FILE" "$ICON_DIR/${size}x${size}/apps/keisanbako.png"
    fi
done

# Update icon cache
echo "  Updating icon cache..."
sudo gtk-update-icon-cache "$ICON_DIR" 2>/dev/null || true

# Create symlink for command line
sudo ln -sf /opt/Keisanbako/Keisanbako /usr/local/bin/keisanbako 2>/dev/null || true

echo "✅ Installation complete!"
echo ""
echo "To launch Keisanbako:"
echo "  keisanbako"
echo "or find it in your application menu"
echo ""
echo "To uninstall:"
echo "  sudo rm -rf /opt/Keisanbako"
echo "  sudo rm /usr/share/applications/Keisanbako.desktop"
echo "  sudo rm /usr/local/bin/keisanbako"
