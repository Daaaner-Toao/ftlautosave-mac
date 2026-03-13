# FTL Autosave Makefile
# =====================
# Build and development commands for FTL Autosave Mac app

# Configuration
PYTHON = /opt/homebrew/bin/python3.11
APP_NAME = FTL Autosave
APP_DIR = dist/FTL Autosave.app
DEST_DIR = /Applications

# Colors for output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[0;33m
BLUE = \033[0;34m
RESET = \033[0m

# Default target
.DEFAULT_GOAL := help

# =============================================================================
# Development
# =============================================================================

.PHONY: run
run: ## Start the application (development mode)
	@echo "$(BLUE)Starting FTL Autosave...$(RESET)"
	@pkill -f "python.*ftlautosave" 2>/dev/null || true
	@$(PYTHON) run_ftlautosave.py &

.PHONY: run-fg
run-fg: ## Start the application in foreground (for debugging)
	@echo "$(BLUE)Starting FTL Autosave (foreground)...$(RESET)"
	@$(PYTHON) run_ftlautosave.py

.PHONY: stop
stop: ## Stop any running instance
	@echo "$(YELLOW)Stopping FTL Autosave...$(RESET)"
	@pkill -f "python.*ftlautosave" 2>/dev/null || echo "No running instance found"

# =============================================================================
# Build
# =============================================================================

.PHONY: build
build: clean-build ## Build the Mac App Bundle
	@echo "$(BLUE)Building $(APP_NAME).app...$(RESET)"
	@$(PYTHON) setup.py py2app
	@echo "$(GREEN)Build complete: $(APP_DIR)$(RESET)"
	@ls -la dist/ 2>/dev/null || echo "Build failed!"

.PHONY: clean-build
clean-build: ## Remove build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(RESET)"
	@rm -rf build/ dist/ 2>/dev/null || true
	@rm -rf *.egg-info 2>/dev/null || true

.PHONY: clean
clean: clean-build ## Remove all generated files (build, cache, etc.)
	@echo "$(YELLOW)Cleaning all generated files...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -Delete 2>/dev/null || true

# =============================================================================
# Installation
# =============================================================================

.PHONY: install
install: build ## Build and install app to /Applications
	@echo "$(BLUE)Installing $(APP_NAME) to $(DEST_DIR)...$(RESET)"
	@if [ -d "$(DEST_DIR)/$(APP_NAME).app" ]; then \
		echo "$(YELLOW)Removing existing installation...$(RESET)"; \
		rm -rf "$(DEST_DIR)/$(APP_NAME).app"; \
	fi
	@cp -R "$(APP_DIR)" "$(DEST_DIR)/"
	@echo "$(GREEN)Installed to $(DEST_DIR)/$(APP_NAME).app$(RESET)"

.PHONY: uninstall
uninstall: ## Remove app from /Applications
	@echo "$(YELLOW)Uninstalling $(APP_NAME)...$(RESET)"
	@rm -rf "$(DEST_DIR)/$(APP_NAME).app" 2>/dev/null || echo "App not installed"
	@echo "$(GREEN)Uninstalled$(RESET)"

# =============================================================================
# Testing & Quality
# =============================================================================

.PHONY: test
test: ## Run tests
	@echo "$(BLUE)Running tests...$(RESET)"
	@$(PYTHON) -m pytest tests/ -v 2>/dev/null || echo "No tests found or pytest not installed"

.PHONY: lint
lint: ## Run code linter
	@echo "$(BLUE)Running linter...$(RESET)"
	@$(PYTHON) -m flake8 ftlautosave/ --max-line-length=100 2>/dev/null || echo "flake8 not installed"

.PHONY: format
format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(RESET)"
	@$(PYTHON) -m black ftlautosave/ 2>/dev/null || echo "black not installed"

# =============================================================================
# Git
# =============================================================================

.PHONY: status
status: ## Show git status
	@echo "$(BLUE)Git Status:$(RESET)"
	@git status -s

.PHONY: commit
commit: ## Stage all changes and commit (requires MSG variable)
ifndef MSG
	@echo "$(RED)Error: MSG variable required. Use: make commit MSG='your message'$(RESET)"
	@exit 1
endif
	@echo "$(BLUE)Committing changes...$(RESET)"
	@git add -A
	@git commit -m "$(MSG)"
	@echo "$(GREEN)Committed: $(MSG)$(RESET)"

.PHONY: push
push: ## Push to remote
	@echo "$(BLUE)Pushing to remote...$(RESET)"
	@git push

# =============================================================================
# Info
# =============================================================================

.PHONY: info
info: ## Show project info
	@echo "$(BLUE)=== FTL Autosave Project Info ===$(RESET)"
	@echo "Python: $(PYTHON)"
	@echo "App Name: $(APP_NAME)"
	@echo "Build Output: $(APP_DIR)"
	@echo ""
	@echo "$(BLUE)Project Structure:$(RESET)"
	@ls -la
	@echo ""
	@echo "$(BLUE)ftlautosave module:$(RESET)"
	@ls -la ftlautosave/

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "$(BLUE)FTL Autosave - Makefile Commands$(RESET)"
	@echo "$(BLUE)================================$(RESET)"
	@echo ""
	@echo "$(GREEN)Development:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Examples:$(RESET)"
	@echo "  make run                    # Start the app"
	@echo "  make build                  # Build the Mac app"
	@echo "  make install                # Install to /Applications"
	@echo "  make commit MSG='message'   # Commit changes"
	@echo ""
