#!/usr/bin/env python3
"""
Convert SVG icons to PNG in multiple sizes and create platform-specific icon resources.

Usage:
    python scripts/convert_icons.py

This script:
1. Converts assets/keisanbako_icon.svg to PNG in various sizes
2. Creates platform-specific icon directories (macOS, Windows, Linux)
3. Generates iconset for macOS
4. Creates .ico file for Windows
5. Generates optimized PNG for Linux
"""

import subprocess
import sys
from pathlib import Path

# Define icon sizes needed
ICON_SIZES = {
    16: "16x16",
    32: "32x32",
    64: "64x64",
    128: "128x128",
    256: "256x256",
    512: "512x512",
    1024: "1024x1024",
}

# macOS .icns requires specific sizes
MACOS_SIZES = [16, 32, 64, 128, 256, 512, 1024]

# Windows .ico supports these sizes
WINDOWS_SIZES = [16, 32, 64, 128, 256]

# Linux uses PNG
LINUX_SIZES = [16, 32, 48, 64, 128, 256, 512]


def check_dependencies() -> bool:
    """Check if required tools are installed."""
    try:
        subprocess.run(["which", "cairosvg"], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        print("❌ cairosvg not found. Install with: pip install cairosvg")
        return False


def convert_svg_to_png(svg_path: Path, output_path: Path, size: int) -> bool:
    """Convert SVG to PNG at specified size using cairosvg."""
    try:
        subprocess.run(
            [
                "cairosvg",
                str(svg_path),
                "-o",
                str(output_path),
                "--output-width",
                str(size),
                "--output-height",
                str(size),
            ],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to convert {svg_path}: {e.stderr.decode() if e.stderr else e}")
        return False


def create_macos_icns(png_dir: Path, output_path: Path) -> bool:
    """Create .icns file from PNG images using iconutil."""
    try:
        import shutil

        # Prepare iconset directory
        iconset_path = png_dir / "keisanbako.iconset"
        iconset_path.mkdir(exist_ok=True)

        # macOS icon naming convention: icon_{size}x{size}@{scale}x.png
        # For standard resolution: icon_256x256.png, icon_512x512.png, etc.
        # For retina (@2x): icon_256x256@2x.png, etc.

        macos_files = {
            16: "icon_16x16.png",
            32: "icon_32x32.png",
            64: "icon_64x64.png",
            128: "icon_128x128.png",
            256: "icon_256x256.png",
            512: "icon_512x512.png",
            1024: "icon_512x512@2x.png",  # 512@2x becomes 1024
        }

        for size, filename in macos_files.items():
            src = png_dir / f"keisanbako_{size}x{size}.png"
            dst = iconset_path / filename
            if src.exists():
                shutil.copy2(str(src), str(dst))

        # Convert iconset to .icns
        subprocess.run(
            ["iconutil", "-c", "icns", "-o", str(output_path), str(iconset_path)],
            check=True,
            capture_output=True,
        )

        print(f"✅ Created macOS icon: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create .icns: {e.stderr.decode() if e.stderr else e}")
        return False
    except Exception as e:
        print(f"❌ Failed to create .icns: {e}")
        return False


def create_windows_ico(png_dir: Path, output_path: Path) -> bool:
    """Create .ico file from PNG images using pillow."""
    try:
        from PIL import Image

        # Collect PNG files in order of size
        png_files = sorted(png_dir.glob("keisanbako_*x*.png"), key=lambda p: int(p.stem.split("_")[1].split("x")[0]))

        if not png_files:
            print("⚠️  No PNG files found for .ico creation")
            return False

        images = []
        for png_file in png_files:
            try:
                img = Image.open(png_file)
                images.append(img)
            except Exception as e:
                print(f"  Warning: Could not open {png_file}: {e}")

        if images:
            # Save as ICO with multiple sizes
            images[0].save(
                str(output_path),
                format="ICO",
                sizes=[(img.width, img.height) for img in images],
            )
            print(f"✅ Created Windows icon: {output_path}")
            return True
        else:
            print("❌ No valid images for .ico creation")
            return False
    except ImportError:
        print("⚠️  Pillow not installed. Skipping .ico creation.")
        print("   Install with: pip install Pillow")
        return False
    except Exception as e:
        print(f"❌ Failed to create .ico: {e}")
        return False


def main() -> int:
    """Main conversion process."""
    project_root = Path(__file__).parent.parent
    assets_dir = project_root / "assets"
    resources_dir = project_root / "src" / "Keisanbako" / "resources"

    # Create resources directory
    resources_dir.mkdir(parents=True, exist_ok=True)

    # Create platform-specific directories
    macos_dir = resources_dir / "macos"
    windows_dir = resources_dir / "windows"
    linux_dir = resources_dir / "linux"

    for directory in [macos_dir, windows_dir, linux_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    svg_file = assets_dir / "keisanbako_icon.svg"

    if not svg_file.exists():
        print(f"❌ Icon file not found: {svg_file}")
        return 1

    if not check_dependencies():
        return 1

    print("🔨 Converting icons...")
    print()

    # Convert for macOS
    print("📱 macOS icons...")
    macos_pngs = []
    for size in MACOS_SIZES:
        png_path = macos_dir / f"keisanbako_{size}x{size}.png"
        if convert_svg_to_png(svg_file, png_path, size):
            macos_pngs.append(png_path)
            print(f"  ✓ {size}x{size}")

    if macos_pngs:
        icns_path = macos_dir / "keisanbako.icns"
        create_macos_icns(macos_dir, icns_path)

    # Convert for Windows
    print("🪟 Windows icons...")
    for size in WINDOWS_SIZES:
        png_path = windows_dir / f"keisanbako_{size}x{size}.png"
        if convert_svg_to_png(svg_file, png_path, size):
            print(f"  ✓ {size}x{size}")

    ico_path = windows_dir / "keisanbako.ico"
    create_windows_ico(windows_dir, ico_path)

    # Convert for Linux
    print("🐧 Linux icons...")
    for size in LINUX_SIZES:
        png_path = linux_dir / f"keisanbako_{size}x{size}.png"
        if convert_svg_to_png(svg_file, png_path, size):
            print(f"  ✓ {size}x{size}")

    print()
    print("✅ Icon conversion complete!")
    print()
    print("Icon resources created at:")
    print(f"  macOS: {macos_dir}")
    print(f"  Windows: {windows_dir}")
    print(f"  Linux: {linux_dir}")
    print()
    print("Next steps:")
    print("  1. Update build scripts to reference these icons")
    print("  2. Configure PyInstaller spec file with icon paths")
    print("  3. Run build scripts to create platform-specific bundles")

    return 0


if __name__ == "__main__":
    sys.exit(main())
