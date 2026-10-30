.PHONY: help build build-macos build-windows build-linux install install-macos install-linux icons clean dmg test check

# Detect OS
UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
    OS := macos
else ifeq ($(UNAME),Linux)
    OS := linux
else ifeq ($(OS),Windows_NT)
    OS := windows
else
    OS := unknown
endif

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;35m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║        Keisanbako Calculator - Build System (Nuitka)        ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Detected OS: $(OS)$(NC)"
	@echo ""
	@echo "$(GREEN)Main Targets:$(NC)"
	@echo "  $(BLUE)make run$(NC)           - Run app (dev mode, no build needed)"
	@echo "  $(BLUE)make run-dist$(NC)      - Build and run compiled app"
	@echo "  $(BLUE)make build$(NC)         - Build app for your platform (Nuitka)"
	@echo "  $(BLUE)make build-macos$(NC)   - Build macOS app with Nuitka"
	@echo "  $(BLUE)make build-linux$(NC)   - Build Linux app with Nuitka"
	@echo "  $(BLUE)make build-windows$(NC) - Build Windows app with Nuitka"
	@echo "  $(BLUE)make install$(NC)       - Install app (platform-specific)"
	@echo "  $(BLUE)make install-macos$(NC) - Install macOS app"
	@echo "  $(BLUE)make install-linux$(NC) - Install Linux system-wide"
	@echo ""
	@echo "$(GREEN)Additional:$(NC)"
	@echo "  $(BLUE)make icons$(NC)         - Convert SVG icons to all formats"
	@echo "  $(BLUE)make dmg$(NC)           - Create macOS DMG installer"
	@echo "  $(BLUE)make test$(NC)          - Run test suite"
	@echo "  $(BLUE)make check$(NC)         - Run type checking and linting"
	@echo "  $(BLUE)make clean$(NC)         - Clean build artifacts"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  $(BLUE)make dev$(NC)           - Install dev dependencies"
	@echo "  $(BLUE)make format$(NC)        - Format code with black"
	@echo "  $(BLUE)make lint$(NC)          - Lint with ruff"
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  # Build app for current platform"
	@echo "  $$ make build"
	@echo ""
	@echo "  # Build for specific platform"
	@echo "  $$ make build-macos"
	@echo ""
	@echo "  # Full workflow"
	@echo "  $$ make dev        # Install dependencies"
	@echo "  $$ make icons      # Convert icons"
	@echo "  $$ make test       # Run tests"
	@echo "  $$ make build      # Build app"
	@echo ""

# ============================================================================
# Main Targets (Nuitka)
# ============================================================================

build: icons
	@echo "$(GREEN)Building Keisanbako for $(OS) with Nuitka...$(NC)"
ifeq ($(OS),macos)
	@./build_macos_nuitka.sh
else ifeq ($(OS),linux)
	@./build_linux_nuitka.sh
else ifeq ($(OS),windows)
	@./build_windows_nuitka.sh
else
	@echo "$(RED)Error: Unknown OS $(OS)$(NC)"
	@exit 1
endif
	@echo "$(GREEN)✅ Nuitka build complete!$(NC)"

# ============================================================================
# Platform-Specific Builds (Nuitka)
# ============================================================================

build-macos: icons
	@echo "$(GREEN)Building Keisanbako for macOS with Nuitka...$(NC)"
	@./build_macos_nuitka.sh
	@echo "$(GREEN)✅ macOS build complete!$(NC)"
	@echo "   Run: open dist/Keisanbako.app"

build-windows: icons
	@echo "$(GREEN)Building Keisanbako for Windows with Nuitka...$(NC)"
	@./build_windows_nuitka.sh
	@echo "$(GREEN)✅ Windows build complete!$(NC)"
	@echo "   Run: dist\\Keisanbako.exe"

build-linux: icons
	@echo "$(GREEN)Building Keisanbako for Linux with Nuitka...$(NC)"
	@./build_linux_nuitka.sh
	@echo "$(GREEN)✅ Linux build complete!$(NC)"
	@echo "   Run: dist/Keisanbako"

run:
	@echo "$(GREEN)Running Keisanbako (dev mode)...$(NC)"
	@PYTHONPATH=src python -m Keisanbako.calculator

run-dist: build
	@echo "$(GREEN)Running Keisanbako (compiled)...$(NC)"
ifeq ($(OS),macos)
	@open dist/Keisanbako.app
else ifeq ($(OS),linux)
	@./dist/Keisanbako
else ifeq ($(OS),windows)
	@./dist/Keisanbako.exe
else
	@echo "$(RED)Error: Unknown OS $(OS)$(NC)"
	@exit 1
endif

# ============================================================================
# Installation
# ============================================================================

install: build
ifeq ($(OS),macos)
	@$(MAKE) install-macos
else ifeq ($(OS),linux)
	@$(MAKE) install-linux
else
	@echo "$(YELLOW)Install not yet supported for $(OS)$(NC)"
	@echo "See BUILD.md for manual installation instructions"
endif

install-macos: build-macos
	@echo "$(GREEN)Installing Keisanbako for macOS to /Applications/...$(NC)"
	@if [ ! -w /Applications ]; then \
		echo "$(YELLOW)Requires elevated privileges to install to /Applications/$(NC)"; \
		sudo cp -r dist/Keisanbako.app /Applications/; \
	else \
		cp -r dist/Keisanbako.app /Applications/; \
	fi
	@echo "$(GREEN)✅ Installed to /Applications/Keisanbako.app$(NC)"
	@echo "   Open Launchpad or Finder to launch"

install-linux: build-linux
	@echo "$(GREEN)Installing Keisanbako for Linux...$(NC)"
	@sudo ./linux/install.sh
	@echo "$(GREEN)✅ Installed system-wide$(NC)"
	@echo "   Run: keisanbako"

# ============================================================================
# Distribution
# ============================================================================

dmg: build-macos

	@echo "$(GREEN)Creating macOS DMG installer...$(NC)"
	@command -v create-dmg >/dev/null 2>&1 || { echo "$(RED)Error: create-dmg not found$(NC)"; echo "Install with: brew install create-dmg"; exit 1; }
	@./scripts/create_dmg.sh
	@echo "$(GREEN)✅ DMG created successfully!$(NC)"

# ============================================================================
# Icons
# ============================================================================

icons:
	@echo "$(GREEN)Converting SVG icons to all formats...$(NC)"
	@python scripts/convert_icons.py
	@echo "$(GREEN)✅ Icons converted!$(NC)"

# ============================================================================
# Development
# ============================================================================

dev:
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	@pip install -e ".[dev]"
	@echo "$(GREEN)✅ Dev dependencies installed!$(NC)"

test:
	@echo "$(GREEN)Running tests...$(NC)"
	@python -m pytest tests/ -v
	@echo "$(GREEN)✅ Tests complete!$(NC)"

check: format lint type-check

format:
	@echo "$(GREEN)Formatting code with black...$(NC)"
	@black src/ tests/
	@echo "$(GREEN)✅ Code formatted!$(NC)"

lint:
	@echo "$(GREEN)Linting with ruff...$(NC)"
	@ruff check src/ tests/ --fix
	@echo "$(GREEN)✅ Linting complete!$(NC)"

type-check:
	@echo "$(GREEN)Running mypy type checking...$(NC)"
	@mypy --strict src/Keisanbako/
	@echo "$(GREEN)✅ Type checking complete!$(NC)"

# ============================================================================
# Cleanup
# ============================================================================

clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@rm -rf build/ dist/ *.spec .pytest_cache __pycache__ .mypy_cache
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✅ Cleaned!$(NC)"

clean-icons:
	@echo "$(YELLOW)Cleaning icon resources...$(NC)"
	@rm -rf src/Keisanbako/resources/
	@echo "$(GREEN)✅ Icon resources removed!$(NC)"

clean-all: clean clean-icons
	@echo "$(GREEN)✅ Full cleanup complete!$(NC)"

# ============================================================================
# Info
# ============================================================================

info:
	@echo "$(BLUE)Project Information:$(NC)"
	@echo "  Name: Keisanbako Calculator"
	@echo "  Version: 0.1.0"
	@echo "  Python: 3.10+"
	@echo "  GUI: PyQt6"
	@echo ""
	@echo "$(BLUE)Build Information:$(NC)"
	@echo "  Detected OS: $(OS)"
	@echo "  Uname: $(UNAME)"
	@echo ""
	@echo "$(BLUE)Directory Structure:$(NC)"
	@ls -la | grep -E "^d" | awk '{print "  " $$NF}'

# ============================================================================
# Shortcuts
# ============================================================================

b: build
r: run
i: install
t: test
c: clean
h: help

.DEFAULT_GOAL := help
