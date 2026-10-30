#!/bin/bash
# Build script for Keisanbako Linux app using Nuitka (faster than PyInstaller)
# Creates a standalone binary with all dependencies included

set -e  # Exit on error

echo "🔨 Building Keisanbako Linux app with Nuitka..."

# Check if Nuitka is installed
if ! python -m nuitka --version > /dev/null 2>&1; then
    echo "❌ Nuitka not found. Installing..."
    pip install nuitka zstandard ordered-set
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ 2>/dev/null || true
rm -rf calculator.linux 2>/dev/null || true

# Compile with Nuitka - ULTRA-OPTIMIZED FOR SIZE
# Key optimization strategies:
#   --follow-imports: Descend into imports (needed for our modules)
#   --follow-import-to=*: But ONLY follow specific modules we need
#   --nofollow-import-to=*: Explicitly skip known bloat
#   --include-package/--include-module: Include our code
#   --lto=auto: Use link-time optimization if available
#   Nuitka strips symbols by default (~2-3MB savings)
#   Exclude heavy Qt modules: QtPdf (7.1M), QtNetwork (1.6M), QtDBus, QtSvg
echo "🚀 Compiling with Nuitka in ULTRA-SIZE-OPTIMIZED mode..."
echo "   (Aggressively pruning unused modules - this takes 2-5 minutes)..."
PYTHONPATH=src python -m nuitka \
    --mode=standalone \
    --assume-yes-for-downloads \
    --output-filename=Keisanbako \
    --output-dir=dist \
    --lto=auto \
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

# Standalone output is dist/Keisanbako.dist; rename it to dist/Keisanbako
if [ -d "dist/Keisanbako.dist" ]; then
    mv dist/Keisanbako.dist dist/Keisanbako
fi

chmod +x dist/Keisanbako/Keisanbako 2>/dev/null || true

# Additional size optimization: Remove unnecessary files from the bundle
if [ -f "dist/Keisanbako/Keisanbako" ] && [ -d "dist/Keisanbako.build" ]; then
    echo "🧹 Optimizing bundle size (removing unnecessary files)..."

    BUILD_DIR="dist/Keisanbako.build"

    # Remove unnecessary files
    find "$BUILD_DIR" -name "*.pyi" -delete 2>/dev/null || true  # Type stubs
    find "$BUILD_DIR" -name "*.pyc" -delete 2>/dev/null || true  # Compiled files
    find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "typeshed" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "mkspecs" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "translations" -exec rm -rf {} + 2>/dev/null || true

    # Remove unnecessary documentation files
    find "$BUILD_DIR" -name "*.md" -o -name "*.rst" -o -name "*.txt" | grep -v "Keisanbako" | xargs rm -f 2>/dev/null || true
fi

echo "✅ Build successful!"
echo ""
echo "📦 App location: dist/Keisanbako"

# Show final size
APP_SIZE=$(du -sh dist/Keisanbako* 2>/dev/null | tail -1 | cut -f1)
echo "💾 Final app size: $APP_SIZE"
echo ""
echo "To run the app:"
echo "  ./dist/Keisanbako"
echo ""
echo "To install system-wide:"
echo "  sudo cp dist/Keisanbako /usr/local/bin/"
    echo ""
    echo "⚡ Nuitka builds are ~3-5x faster to start than PyInstaller!"
else
    echo "❌ Build failed or executable not found"
    exit 1
fi
