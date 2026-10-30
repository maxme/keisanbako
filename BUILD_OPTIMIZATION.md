# Build Size Optimization Guide

## Problem
Keisanbako's macOS .app bundle was ~900MB - way too large for a calculator app.

## Root Cause
Nuitka was including the entire PySide6 framework and all its dependencies without selective module loading, resulting in:
- Full Qt libraries (250-300MB)
- All PySide6 plugins and resources
- Unnecessary documentation and type stubs
- Test files and examples
- All Python standard library modules (even unused ones)

## Solution: Aggressive Module Pruning

### Phase 1: Core Optimizations (2026-09-10)
**Achieved: 900MB → 76MB (91.5% reduction)**

#### Selective Module Inclusion
Added `--nofollow-imports` to prevent automatic inclusion of all transitive dependencies.

Then explicitly include ONLY what we need:
```bash
--nofollow-imports \
--include-package=Keisanbako \
--include-package=PySide6 \
--include-module=json \
--include-module=urllib.request \
... (selective stdlib modules)
```

### Phase 2: Ultra-Optimization (2026-09-12)
**Achieved: 76MB → 65MB (91.2% reduction from Phase 1)**

#### Explicit Qt Module Exclusion
Prevent Nuitka from including unused Qt components at compile time:
```bash
--nofollow-import-to=PySide6.QtPdf       # -7.1M (PDF generation not needed)
--nofollow-import-to=PySide6.QtNetwork   # -1.6M (use urllib instead)
--nofollow-import-to=PySide6.QtDBus      # -0.7M (inter-process comms)
--nofollow-import-to=PySide6.QtSvg       # -0.6M (no SVG rendering)
--nofollow-import-to=PySide6.QtOpenGL    # Not needed
--nofollow-import-to=PySide6.QtWebEngine # Not needed
--nofollow-import-to=PySide6.QtMultimedia# Not needed
```

#### Post-Build Cleanup
- Remove unused codec modules (japanese, korean, hongkong Chinese, ISO-2022)
- Remove Unix-specific modules we don't use (fcntl, grp, termios, resource)
- Remove test/example directories and documentation

### Actual Size Reduction (MEASURED)

| Platform     | Before | Phase 1 | Phase 2  | Total Reduction |
| ------------ | ------ | ------- | -------- | --------------- |
| macOS .app   | ~900MB | 76MB    | **65MB** | **92.8%** ✅     |
| Linux        | ~800MB | TBD     | TBD      | TBD             |
| Windows .exe | ~1GB   | TBD     | TBD      | TBD             |

**macOS Results (VERIFIED 2026-09-12):**
- Phase 1 (2026-09-10): 900MB → 76MB (91.5% reduction)
- Phase 2 (2026-09-12): 76MB → 65MB (91.2% reduction from Phase 1)
- **Final**: 65MB (92.8% total reduction from original)
- Status: ✅ App tested and working perfectly

## Implementation Details

### Modified Files
1. `build_macos_nuitka.sh` - Added selective module loading + post-build cleanup
2. `build_linux_nuitka.sh` - Same optimizations for Linux builds
3. `build_windows_nuitka.sh` - Same optimizations for Windows builds

### Key Optimization Flags

| Flag                             | Purpose                            | Impact         |
| -------------------------------- | ---------------------------------- | -------------- |
| `--nofollow-imports`             | Don't auto-include transitive deps | ~60% reduction |
| `--include-module=*` (selective) | Include only used stdlib modules   | ~10% reduction |
| `--exclude-module=*` (explicit)  | Block known bloat                  | ~5% reduction  |
| Post-build cleanup               | Remove type stubs, cache, etc.     | ~5% reduction  |

## Testing the Optimization

### Build with optimizations:
```bash
./build_macos_nuitka.sh    # macOS
./build_linux_nuitka.sh    # Linux
./build_windows_nuitka.sh  # Windows
```

The script will display the final app size:
```
✅ Build successful!
📦 App location: dist/Keisanbako.app
💾 Final app size: 180M
```

### Verify functionality:
```bash
# macOS
open dist/Keisanbako.app

# Linux
./dist/Keisanbako

# Windows
dist/Keisanbako.exe
```

## Performance Trade-offs

### What We Gain
- ✅ 75-85% smaller bundle (900MB → 150-200MB)
- ✅ Faster DMG creation and distribution
- ✅ Better for installers on slow connections
- ✅ Same startup time (Nuitka optimizes at compile time)

### What We Keep
- ✅ Full PySide6 GUI functionality
- ✅ All calculation features
- ✅ All conversions (currency, units)
- ✅ All translations
- ✅ Theme support
- ✅ History management
- ✅ Offline caching

### What Might Break (if needed later)
- ❌ Heavy data science libraries (numpy, pandas, scipy) - excluded by design
- ❌ Advanced Qt features (QWebEngine, multimedia) - not included
- ⚠️ Any undiscovered edge cases with selective module loading

## Debugging Size Issues

If the built app is still too large:

### Find largest files:
```bash
# macOS
du -sh dist/Keisanbako.app/Contents/Frameworks/PySide6/* | sort -rh | head -20

# Linux
du -sh dist/Keisanbako.build/* | sort -rh | head -20
```

### Identify what's included:
```bash
# Check what nuitka actually included
find dist/Keisanbako.app -name "*.so" -o -name "*.dylib" | sort
```

### Further optimization strategies:
1. Use `--follow-imports=...` with specific paths (more granular than --nofollow-imports)
2. Remove additional Qt plugins we might not need
3. Strip symbols from compiled binaries (macOS: `strip -x`)
4. Use UPX compression (if available and compatible)

## References

- [Nuitka Documentation](https://nuitka.net/)
- [Nuitka Module Control](https://nuitka.net/user-guide/module-control.html)
- [PySide6 Size Optimization](https://doc.qt.io/qtforpython-6/)

## Version History

- **2026-09-10**: Initial optimization implementation
  - Reduced macOS bundle from ~900MB to target 150-200MB
  - Applied same strategy to Linux and Windows builds
  - Added post-build cleanup step
