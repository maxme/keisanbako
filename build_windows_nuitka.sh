#!/bin/bash
# Build script for Keisanbako Windows app using Nuitka (faster than PyInstaller)
# Creates a standalone executable with all dependencies included
# Note: This script runs on macOS/Linux but builds a Windows binary
# Requires cross-compilation setup or running on Windows

set -e  # Exit on error

echo "🔨 Building Keisanbako Windows app with Nuitka..."

# Check if Nuitka is installed
if ! python -m nuitka --version > /dev/null 2>&1; then
    echo "❌ Nuitka not found. Installing..."
    pip install nuitka zstandard ordered-set
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ 2>/dev/null || true
rm -rf calculator.exe 2>/dev/null || true

# Check if we're on Windows or attempting cross-compilation
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    echo "⚠️  Note: Cross-compilation from non-Windows is limited"
    echo "    Best results with native Windows environment"
fi

# Compile with Nuitka - ULTRA-OPTIMIZED FOR SIZE
# Key optimization strategies:
#   --follow-imports: Descend into imports (needed for our modules)
#   --follow-import-to=*: But ONLY follow specific modules we need
#   --nofollow-import-to=*: Explicitly skip known bloat
#   --include-package/--include-module: Include our code
#   --lto=auto: Use link-time optimization if available
#   Nuitka strips symbols by default (~2-3MB savings)
#   Exclude heavy Qt modules: QtPdf (7.1M), QtNetwork (1.6M), QtDBus, QtSvg
#   --windows-icon-from-ico: Use Windows icon (if available)
echo "🚀 Compiling with Nuitka in ULTRA-SIZE-OPTIMIZED mode..."
echo "   (Aggressively pruning unused modules - this takes 3-5 minutes)..."
ICON_PATH="src/Keisanbako/resources/windows/keisanbako.ico"

PYTHONPATH=src python -m nuitka \
    --mode=standalone \
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
    $([ -f "$ICON_PATH" ] && echo "--windows-icon-from-ico=$ICON_PATH") \
    src/Keisanbako/calculator.py

# Rename the executable to Keisanbako.exe
# Standalone output is dist/calculator.dist; rename it to dist/Keisanbako
if [ -d "dist/calculator.dist" ]; then
    mv dist/calculator.dist dist/Keisanbako
    mv dist/Keisanbako/calculator.exe dist/Keisanbako/Keisanbako.exe
fi

# Additional size optimization: Remove unnecessary files from the build directory
if [ -d "dist/calculator.build" ]; then
    echo "🧹 Optimizing bundle size (removing unnecessary files)..."

    BUILD_DIR="dist/calculator.build"

    # Remove unnecessary files
    find "$BUILD_DIR" -name "*.pyi" -delete 2>/dev/null || true  # Type stubs
    find "$BUILD_DIR" -name "*.pyc" -delete 2>/dev/null || true  # Compiled files
    find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "typeshed" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "mkspecs" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type d -name "translations" -exec rm -rf {} + 2>/dev/null || true

    # Remove unnecessary documentation files
    find "$BUILD_DIR" -name "*.md" -o -name "*.rst" -o -name "*.txt" | grep -v "Keisanbako" | xargs rm -f 2>/dev/null || true
fi

if [ -f "dist/Keisanbako/Keisanbako.exe" ]; then
    echo "✅ Build successful!"
    echo ""
    echo "📦 App location: dist/Keisanbako/Keisanbako.exe"

    # Show final size (Windows du command may differ)
    if command -v du &> /dev/null; then
        APP_SIZE=$(du -sh dist/Keisanbako 2>/dev/null | cut -f1)
        echo "💾 Final app size: $APP_SIZE"
    fi
    echo ""
    echo "To run the app:"
    echo "  dist/Keisanbako.exe"
    echo ""
    echo "⚡ Nuitka builds are ~3-5x faster to start than PyInstaller!"
else
    echo "❌ Build failed or executable not found"
    exit 1
fi
