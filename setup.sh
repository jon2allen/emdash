#!/bin/sh
# setup.sh - Portable POSIX setup script for macOS, Linux, and FreeBSD (sh/bash)
# Supports interactive prompt or --noprompt / -y to install both automatically.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_DIR="$HOME/.git_hooks"
BIN_DIR="$HOME/.local/bin"

INSTALL_HOOK=0
INSTALL_BIN=0

# Parse command line options
for arg in "$@"; do
    case "$arg" in
        --noprompt|-y|--all)
            INSTALL_HOOK=1
            INSTALL_BIN=1
            ;;
        --hook-only)
            INSTALL_HOOK=1
            INSTALL_BIN=0
            ;;
        --bin-only)
            INSTALL_HOOK=0
            INSTALL_BIN=1
            ;;
        --help|-h)
            echo "Usage: ./setup.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --noprompt, -y, --all   Install both global Git hook and CLI tool without prompting"
            echo "  --hook-only             Install only global Git hook (~/.git_hooks)"
            echo "  --bin-only              Install only CLI tool (~/.local/bin)"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            echo "Run ./setup.sh --help for available options." >&2
            exit 1
            ;;
    esac
done

# If no flags passed, prompt the user interactively
if [ "$INSTALL_HOOK" -eq 0 ] && [ "$INSTALL_BIN" -eq 0 ]; then
    echo "========================================================"
    echo "       Em-Dash & Unicode Dash Cleaner Setup"
    echo "========================================================"
    echo ""
    echo "What would you like to install?"
    echo "  1) Both: Global Git Hook (~/.git_hooks) AND CLI Tool (~/.local/bin) [Recommended]"
    echo "  2) Global Git Hook only (~/.git_hooks)"
    echo "  3) CLI Tool only (~/.local/bin)"
    echo "  4) Exit without installing"
    echo ""
    printf "Enter choice [1-4] (default: 1): "
    read -r choice < /dev/tty || choice=""

    case "$choice" in
        1|""|"both"|"b")
            INSTALL_HOOK=1
            INSTALL_BIN=1
            ;;
        2|"hook"|"h")
            INSTALL_HOOK=1
            INSTALL_BIN=0
            ;;
        3|"bin")
            INSTALL_HOOK=0
            INSTALL_BIN=1
            ;;
        4|"q"|"quit"|"exit")
            echo "Setup cancelled. No changes made."
            exit 0
            ;;
        *)
            echo "Invalid selection: $choice. Aborting." >&2
            exit 1
            ;;
    esac
fi

echo ""
echo "--------------------------------------------------------"

# 1. Install CLI Tool to ~/.local/bin
if [ "$INSTALL_BIN" -eq 1 ]; then
    echo "[1/2] Installing CLI Tool to $BIN_DIR..."
    mkdir -p "$BIN_DIR"
    cp "$SCRIPT_DIR/detect_emdash.py" "$BIN_DIR/detect_emdash.py"
    chmod +x "$BIN_DIR/detect_emdash.py"
    echo "      -> Installed: $BIN_DIR/detect_emdash.py"
    
    # Check if ~/.local/bin is in PATH
    case ":$PATH:" in
        *":$BIN_DIR:"*) ;;
        *)
            echo "      NOTE: $BIN_DIR is not currently in your PATH."
            echo "            Add it with: export PATH=\"\$HOME/.local/bin:\$PATH\""
            ;;
    esac
fi

# 2. Install Global Git Hook to ~/.git_hooks
if [ "$INSTALL_HOOK" -eq 1 ]; then
    echo "[2/2] Installing Global Git Hook to $HOOKS_DIR..."
    mkdir -p "$HOOKS_DIR"
    cp "$SCRIPT_DIR/detect_emdash.py" "$HOOKS_DIR/detect_emdash.py"
    cp "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/detect_emdash.py"
    chmod +x "$HOOKS_DIR/pre-commit"
    
    git config --global core.hooksPath "$HOOKS_DIR"
    echo "      -> Installed: $HOOKS_DIR/pre-commit"
    echo "      -> Configured git core.hooksPath = $(git config --global core.hooksPath)"
fi

echo "--------------------------------------------------------"
echo "Setup completed successfully!"
if [ "$INSTALL_HOOK" -eq 1 ]; then
    echo "* 'git commit' in any repo will auto-clean Unicode dashes in staged files."
fi
if [ "$INSTALL_BIN" -eq 1 ]; then
    echo "* Run 'detect_emdash.py --help' to use the CLI tool manually anytime."
fi
echo "========================================================"
