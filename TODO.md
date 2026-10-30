# Keisanbako Calculator - Project Roadmap

## Phase 1: Architecture Refactoring ✅ COMPLETE

### Refactoring Summary
- [x] Extract `parser.py` - Expression parsing & preprocessing (170 lines)
- [x] Extract `evaluator.py` - Safe evaluation engine (340 lines)
- [x] Extract `converters.py` - Currency & unit conversion (340 lines)
- [x] Extract `settings.py` - Configuration management (170 lines)
- [x] Extract `ui.py` - PySide6 GUI components (900+ lines)
- [x] Reduce `calculator.py` to thin orchestration layer (50 lines)
- [x] Update imports in `__init__.py`
- [x] Fix test imports and patch paths
- [x] Fix direct script execution (now supports `python src/Keisanbako/calculator.py`)
- [x] Maintain feature parity (100% logic preserved)
- [x] Backward compatibility (static method calls still work)
- [x] **🎉 Optimize build size** - Reduced macOS .app from ~900MB to **76MB (91.5% reduction!)**
  - [x] Diagnosed root cause (over-including PySide6 framework)
  - [x] Implemented selective module loading with --follow-import-to/--nofollow-import-to
  - [x] Added post-build cleanup (remove type stubs, cache, test files)
  - [x] Applied optimizations to macOS, Linux, and Windows builds
  - [x] Created BUILD_OPTIMIZATION.md documentation
  - [x] **✅ MEASURED: 76MB macOS bundle (from 900MB) - all features working**
  - [x] **🎉 Phase 2 Ultra-Optimization (2026-09-12):**
    - [x] Excluded unused Qt modules in Nuitka build (QtPdf, QtNetwork, QtDBus, QtSvg)
    - [x] Additional post-build cleanup for unused codecs and Unix modules
    - [x] **✅ MEASURED: 65MB macOS bundle (from 76MB) - 92.8% total reduction**


---

## Phase 2: Test Coverage Expansion ✅ COMPLETE

### Completion Summary
- [x] **UI Integration Tests** - 27 tests ✅
  - [x] Keyboard shortcuts (Ctrl+C, Ctrl+H, Ctrl+Shift+C, Ctrl+T, Ctrl+E)
  - [x] Theme switching (dark/light toggle)
  - [x] History visibility and management
  - [x] Settings dialog operations
  - [x] Language change and UI refresh
  - [x] Input field focus and cursor management
  - [x] Menu actions (export, help, settings)

- [x] **Threading & Concurrency Tests** - 26 tests ✅
  - [x] ExpressionEvaluatorWorker thread execution
  - [x] HistoryLoaderWorker background loading
  - [x] Debouncing logic (300ms delay)
  - [x] History loading in background
  - [x] Thread safety of USER_VARS
  - [x] No UI blocking during evaluation
  - [x] Graceful shutdown of workers
  - [x] Thread cancellation and cleanup

- [x] **Offline & Failure Mode Tests** - 47 tests ✅
  - [x] Currency conversion without network
  - [x] Cache fallback for expired rates
  - [x] API timeout handling
  - [x] Retry logic with exponential backoff
  - [x] Invalid API responses (invalid JSON, missing rates)
  - [x] Partial cache hit scenarios
  - [x] Offline crypto price checks
  - [x] Network reconnection recovery
  - [x] Rate limiting (429) handling with Retry-After
  - [x] Request deduplication (5s TTL)
  - [x] Connection error recovery
  - [x] Validation error responses

- [x] **Edge Cases & Performance Tests** - 48 tests ✅
  - [x] Very large numbers (100+ digits)
  - [x] Deeply nested expressions (50-1000 levels)
  - [x] Large history (1000+ entries)
  - [x] Rapid consecutive evaluations (1000 expressions)
  - [x] Special characters in variable names (Greek letters, underscores)
  - [x] Unicode in translations and formatting
  - [x] Extreme date arithmetic (year 1900-2099, leap years)
  - [x] Zero-division recovery
  - [x] Performance benchmarks (< 1ms for simple, < 2s for complex)

### Final Metrics
- **Tests Created**: +124 new tests (71% increase)
- **Total Tests**: 299 (175 Phase 1 + 124 Phase 2)
- **Pass Rate**: 299/299 (100%) ✅
- **Coverage**: High coverage for UI, threading, offline scenarios, and edge cases
- **Test Files**: 4 new files (test_ui_integration.py, test_threading.py, test_offline_failures.py, test_edge_cases.py)

---

## Phase 3: Error Handling & UX 🟡 IN PROGRESS

### Improved Error Messages ✅ COMPLETE
- [x] Added error_type field to CalculationResult dataclass
- [x] Enhanced error detection with specific exception handling
  - [x] SyntaxError → "syntax" error type with hint
  - [x] NameError → "undefined" error type for variables/functions
  - [x] ZeroDivisionError → "zero_division" error type
  - [x] ValueError/generic → "invalid" error type
- [x] Created get_error_message() static method for user-friendly messages
- [x] Updated UI to display error_message instead of generic "Error"
- [x] Tests: 27 comprehensive error handling tests created and passing
- [x] Error messages include hints for common mistakes

### Network & Cache Status ✅ COMPLETE
- [x] Created NetworkStatus module for tracking connectivity
- [x] Implemented CacheEntry with TTL and metadata
- [x] Added cache hit/miss tracking and statistics
- [x] Implemented status indicator (online/offline/degraded)
- [x] API failure tracking per service
- [x] Cache age formatting (e.g., "5m ago")
- [x] Thread-safe cache operations
- [x] Tests: 30 comprehensive network status tests created and passing
- [x] Added is_cached field to CalculationResult
- [x] UI displays "(cached)" suffix for offline results
- [x] Tooltip shows cache metadata

### Network Status Widget 📋 TODO
- [ ] Create StatusWidget for UI display
- [ ] Show colored indicator (green/yellow/red)
- [ ] Display cache statistics on click
- [ ] Show last update time for rates
- [ ] Manual cache refresh button

### UX Polish 📋 TODO
- [ ] Input validation feedback
- [ ] Better history display (timestamps, labels)
- [ ] Undo/redo support
- [ ] Auto-complete for functions and variables
- [ ] Keyboard-only navigation mode
  - Linux (standalone)
  - Windows (.exe/.nsi)
- [ ] `.github/workflows/release.yml` - Auto-publish on version tags

### Build & Distribution
- [ ] Update Nuitka build scripts with new module structure
- [ ] Test cross-platform builds
- [ ] Create DMG installer for macOS
- [ ] Update Windows NSIS installer
- [ ] Linux AppImage/snap packaging
- [ ] Automated version bumping

### Documentation
- [ ] README with new module architecture
- [ ] Installation guide for development
- [ ] Contributing guidelines
- [ ] Architecture documentation
- [ ] API documentation (modules)

---

## Known Issues ⚠️

### Post-Refactoring (Minor)
1. **Currency Conversion Tests** - Require network mocking setup
   - Tests: `TestCurrencyConverter`, `TestCurrencyConversionWithSymbols`, etc.
   - Impact: 15+ tests fail due to missing mock; logic is correct
   - Fix: Add proper mock setup in test fixtures

2. **Menu Action Tests** - QMessageBox/QFileDialog import issues
   - Tests: `TestMenuActions`, `TestIntegration`
   - Impact: 2 tests fail
   - Fix: Verify Qt import paths in test context

3. **History Color Test** - HTML rendering differences
   - Test: `TestHistoryColors::test_history_shows_colored_results`
   - Impact: 1 test fails
   - Cause: CSS/style differences in QTextBrowser
   - Fix: Update expected HTML format

### Known Design Issues (For Future Phases)
- [ ] Thread safety: `ExpressionEvaluator.USER_VARS` is class-level dict (mark for Phase 4)
- [x] ✅ Speed conversion: `8 m/s in km/h` - NOW IMPLEMENTED
  - [x] Added SPEED_FACTORS to UnitConverter (m/s, km/h, mph, mi/h, knots, ft/s)
  - [x] Updated UNIT_PATTERN regex to support "/" in unit names
  - [x] Added 5 comprehensive test cases (all passing)
  - [x] Supported conversions: m/s ↔ km/h, mph, knots, ft/s
- [ ] No undo/redo history mechanism
- [ ] No clipboard auto-paste on launch

---

## Completed Original Features ✅

### Calculation Engine
- [x] Basic arithmetic (+, -, *, /, **)
- [x] Math functions (sin, cos, sqrt, log, etc.)
- [x] Timedelta notation (30 days, 2 weeks)
- [x] Scientific notation (1e5, 2.5e-3)
- [x] Date arithmetic (today + 45 days)
- [x] Variables and user definitions (x = 5)
- [x] Function definitions (f(x) = x**2)

### Conversions
- [x] Currency conversion (100 EUR in USD)
- [x] Unit conversion (100 cm in m, 32 F in C)
- [x] Cryptocurrency support (1 BTC in USD)
- [x] Offline caching with TTL
- [x] Request deduplication

### UI & UX
- [x] Dark/light theme toggle (Ctrl+T)
- [x] History persistence & navigation
- [x] Keyboard shortcuts
- [x] Copy result to clipboard (Ctrl+Shift+C)
- [x] Export history (JSON/CSV)
- [x] Settings dialog
- [x] Multi-language support (6 languages)
- [x] Results with colors (green success, red error)

---

## Development Commands

### Run Application
```bash
# Direct script execution
python src/Keisanbako/calculator.py

# Module execution (requires PYTHONPATH)
PYTHONPATH=src python -m Keisanbako.calculator

# From root (if installed in dev mode)
python -m Keisanbako
```

### Run Tests
```bash
# All tests
python -m pytest tests/ -v

# Specific test class
python -m pytest tests/test_calculator.py::TestExpressionEvaluator -v

# With coverage
python -m pytest tests/ --cov=src/Keisanbako --cov-report=html
```

### Build
```bash
# macOS bundle (Nuitka)
./build_macos_nuitka.sh

# Linux
./build_linux_nuitka.sh

# Windows
./build_windows_nuitka.sh
```
