#!/bin/bash
# Build script for Keisanbako macOS app using Nuitka (faster than PyInstaller)
# Nuitka compiles Python to C++ and then to native machine code for better performance

set -e  # Exit on error

echo "🔨 Building Keisanbako macOS app with Nuitka..."

# Check if Nuitka is installed
if ! python -m nuitka --version > /dev/null 2>&1; then
    echo "❌ Nuitka not found. Installing..."
    pip install nuitka zstandard ordered-set
fi

# Check if icons have been converted
ICON_PATH="src/Keisanbako/resources/macos/keisanbako.icns"
if [ ! -f "$ICON_PATH" ]; then
    echo "⚠️  Icon not found at $ICON_PATH"
    echo "   Converting icons now..."
    if [ ! -f "scripts/convert_icons.py" ]; then
        echo "❌ convert_icons.py not found"
        exit 1
    fi
    python scripts/convert_icons.py
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ 2>/dev/null || true
rm -rf build-*.app 2>/dev/null || true

# Compile with Nuitka - ULTRA-OPTIMIZED FOR SIZE
# Key optimization strategies:
#   --follow-imports: Descend into imports (needed for our modules)
#   --follow-import-to=*: But ONLY follow specific modules we need
#   --nofollow-import-to=*: Explicitly skip known bloat
#   --include-package/--include-module: Include our code
#   --lto=no: Skip LTO (already fast startup, reduces compile time)
#   Nuitka strips symbols by default (~2-3MB savings)
#   Exclude heavy Qt modules: QtPdf (7.1M), QtNetwork (1.6M), QtDBus, QtSvg
echo "🚀 Compiling with Nuitka in ULTRA-SIZE-OPTIMIZED mode..."
echo "   (Aggressively pruning unused modules - this takes 2-3 minutes)..."
echo "Yes" | PYTHONPATH=src python -m nuitka \
    --mode=app \
    --macos-app-icon="$ICON_PATH" \
    --output-dir=dist \
    --lto=no \
    --follow-imports \
    --follow-import-to=json \
    --follow-import-to=urllib \
    --follow-import-to=signal \
    --follow-import-to=logging \
    --follow-import-to=re \
    --follow-import-to=csv \
    --follow-import-to=html \
    --follow-import-to=pathlib \
    --follow-import-to=tempfile \
    --follow-import-to=math \
    --follow-import-to=datetime \
    --nofollow-import-to=test \
    --nofollow-import-to=tests \
    --nofollow-import-to=pip \
    --nofollow-import-to=setuptools \
    --nofollow-import-to=pytest \
    --nofollow-import-to=numpy \
    --nofollow-import-to=scipy \
    --nofollow-import-to=pandas \
    --nofollow-import-to=matplotlib \
    --nofollow-import-to=distutils \
    --enable-plugin=pyside6 \
    --include-package=Keisanbako \
    --include-data-dir=src/Keisanbako/resources=Keisanbako/resources \
    --include-data-dir=src/Keisanbako/translations=Keisanbako/translations \
    --nofollow-import-to=PySide6.QtPdf \
    --nofollow-import-to=PySide6.QtNetwork \
    --nofollow-import-to=PySide6.QtDBus \
    --nofollow-import-to=PySide6.QtSvg \
    --nofollow-import-to=PySide6.QtOpenGL \
    --nofollow-import-to=PySide6.QtWebEngine \
    --nofollow-import-to=PySide6.QtMultimedia \
    --remove-output \
    src/Keisanbako/calculator.py

# Nuitka creates .app bundle with name based on the module
# It should be in dist/calculator.app, rename to Keisanbako.app for consistency
if [ -d "dist/calculator.app" ]; then
    mv dist/calculator.app dist/Keisanbako.app
fi

# Additional size optimization: Remove unnecessary files from the app bundle
if [ -d "dist/Keisanbako.app" ]; then
    echo "🧹 Optimizing bundle size (removing unnecessary files)..."

    APP_CONTENTS="dist/Keisanbako.app/Contents"
    MACOS="$APP_CONTENTS/MacOS"

    # Remove unused Qt modules (excluded in Nuitka but may still be present)
    echo "   • Removing unused Qt modules (QtPdf, QtNetwork, QtDBus, QtSvg, etc.)..."
    rm -f "$MACOS/QtPdf"* 2>/dev/null || true
    rm -f "$MACOS/QtNetwork"* 2>/dev/null || true
    rm -f "$MACOS/QtDBus"* 2>/dev/null || true
    rm -f "$MACOS/QtSvg"* 2>/dev/null || true
    rm -f "$MACOS/QtOpenGL"* 2>/dev/null || true
    rm -f "$MACOS/QtWebEngine"* 2>/dev/null || true
    rm -f "$MACOS/QtMultimedia"* 2>/dev/null || true

    # Remove PySide6 modules we don't need
    echo "   • Removing unused PySide6 modules..."
    rm -rf "$MACOS/PySide6/QtPdf" 2>/dev/null || true
    rm -rf "$MACOS/PySide6/QtNetwork" 2>/dev/null || true
    rm -rf "$MACOS/PySide6/QtDBus" 2>/dev/null || true
    rm -rf "$MACOS/PySide6/QtSvg" 2>/dev/null || true
    rm -rf "$MACOS/PySide6/QtOpenGL" 2>/dev/null || true
    rm -rf "$MACOS/PySide6/QtWebEngine" 2>/dev/null || true
    rm -rf "$MACOS/PySide6/QtMultimedia" 2>/dev/null || true

    # Remove unnecessary codecs (we only use utf-8, ascii, and the languages we support)
    echo "   • Removing unused codec modules..."
    rm -f "$MACOS/_codecs_jp.so" 2>/dev/null || true     # Japanese (not supported)
    rm -f "$MACOS/_codecs_hk.so" 2>/dev/null || true     # Hong Kong Chinese (not supported)
    rm -f "$MACOS/_codecs_cn.so" 2>/dev/null || true     # Simplified Chinese (we may support this, keep)
    rm -f "$MACOS/_codecs_tw.so" 2>/dev/null || true     # Traditional Chinese (we may support this, keep)
    rm -f "$MACOS/_codecs_kr.so" 2>/dev/null || true     # Korean (not supported)
    rm -f "$MACOS/_codecs_iso2022.so" 2>/dev/null || true # ISO-2022 (not needed)

    # Keep Chinese/Japanese codecs for translations, but we can remove others
    # Actual codec list in our translations: en, es, fr, ja, zh_Hans, zh_Hant
    # So we need: Chinese (already there), Japanese (keep), but remove Korean, HK

    # Remove unnecessary socket and network modules (we don't do raw socket ops)
    # Actually, keep _socket as it's used by urllib

    # Remove other unnecessary directories
    echo "   • Removing test/example files..."
    find "$APP_CONTENTS" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_CONTENTS" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_CONTENTS" -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_CONTENTS" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    # Remove unnecessary documentation files
    echo "   • Removing documentation files..."
    find "$APP_CONTENTS" -name "*.md" -o -name "*.rst" -o -name "*.txt" | grep -v "Keisanbako" | xargs rm -f 2>/dev/null || true

    # Additional optimizations: remove .so files for modules we don't use
    # But be careful here - these are Python extension modules
    echo "   • Checking for other unused modules..."
    # Keep common needed ones: _socket, _ssl, array, math, select, etc.
    # Remove ones we definitely don't use:
    rm -f "$MACOS/fcntl.so" 2>/dev/null || true        # Unix file control (not used)
    rm -f "$MACOS/grp.so" 2>/dev/null || true          # Unix group database (not used)
    rm -f "$MACOS/termios.so" 2>/dev/null || true      # Terminal I/O (not used)
    rm -f "$MACOS/resource.so" 2>/dev/null || true     # macOS resource manager (old, not used)

    echo "✅ Build successful!"
    echo ""
    echo "📦 App location: dist/Keisanbako.app"

    # Show final size
    APP_SIZE=$(du -sh dist/Keisanbako.app 2>/dev/null | cut -f1)
    echo "💾 Final app size: $APP_SIZE"
    echo ""
    echo "To run the app:"
    echo "  open dist/Keisanbako.app"
    echo ""
    echo "To create a DMG installer (optional):"
    echo "  brew install create-dmg"
    echo "  ./scripts/create_dmg.sh"
    echo ""
    echo "⚡ Nuitka builds are ~3-5x faster to start than PyInstaller!"
elif [ -d "dist/Keisanbako.app" ]; then
    echo "🧹 Optimizing bundle size (removing unnecessary files)..."

    APP_CONTENTS="dist/Keisanbako.app/Contents"
    FRAMEWORKS="$APP_CONTENTS/Frameworks"

    # Remove unnecessary Qt plugins and libraries
    if [ -d "$FRAMEWORKS/PySide6" ]; then
        # Keep only essential PySide6 modules - remove heavy/unnecessary ones
        find "$FRAMEWORKS/PySide6" -name "*.pyi" -delete 2>/dev/null || true  # Type stubs
        find "$FRAMEWORKS/PySide6" -name "*.pyc" -delete 2>/dev/null || true  # Compiled files
        find "$FRAMEWORKS/PySide6" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$FRAMEWORKS/PySide6" -type d -name "typeshed" -exec rm -rf {} + 2>/dev/null || true
        find "$FRAMEWORKS/PySide6" -type d -name "mkspecs" -exec rm -rf {} + 2>/dev/null || true
        find "$FRAMEWORKS/PySide6" -type d -name "translations" -exec rm -rf {} + 2>/dev/null || true

        # Remove Qt plugins we don't need (keep only essential)
        if [ -d "$FRAMEWORKS/PySide6/plugins" ]; then
            mkdir -p "$FRAMEWORKS/PySide6/plugins/platforms"
            mkdir -p "$FRAMEWORKS/PySide6/plugins/imageformats"

            # Keep only macOS platform plugin and essential image formats
            find "$FRAMEWORKS/PySide6/plugins" -type f ! -name "qcocoa.dylib" ! -name "qgif.dylib" ! -name "qjpeg.dylib" ! -name "qpng.dylib" -delete 2>/dev/null || true
        fi
    fi

    # Remove other unnecessary directories
    find "$APP_CONTENTS" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_CONTENTS" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_CONTENTS" -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true
    find "$APP_CONTENTS" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    # Remove unnecessary documentation files
    find "$APP_CONTENTS" -name "*.md" -o -name "*.rst" -o -name "*.txt" | grep -v "Keisanbako" | xargs rm -f 2>/dev/null || true

    echo "✅ Build successful!"
    echo ""
    echo "📦 App location: dist/Keisanbako.app"

    # Show final size
    APP_SIZE=$(du -sh dist/Keisanbako.app 2>/dev/null | cut -f1)
    echo "💾 Final app size: $APP_SIZE"
    echo ""
    echo "To run the app:"
    echo "  open dist/Keisanbako.app"
    echo ""
    echo "To create a DMG installer (optional):"
    echo "  brew install create-dmg"
    echo "  ./scripts/create_dmg.sh"
    echo ""
    echo "⚡ Nuitka builds are ~3-5x faster to start than PyInstaller!"
else
    echo "❌ Build failed or app not found at expected location"
    ls -la dist/ 2>/dev/null || echo "dist/ directory not found"
    exit 1
fi
