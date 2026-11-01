#!/bin/csh -f
# setup.csh - Native FreeBSD / csh / tcsh setup script
# Supports interactive prompt or --noprompt / -y to install both automatically.

set SCRIPT_DIR = `dirname $0`
set SCRIPT_DIR = `cd "$SCRIPT_DIR" && pwd`
set HOOKS_DIR = "$HOME/.git_hooks"
set BIN_DIR = "$HOME/.local/bin"

set INSTALL_HOOK = 0
set INSTALL_BIN = 0
set PROMPT_USER = 1

# Parse arguments
foreach arg ( $argv )
    switch ( "$arg" )
        case "--noprompt":
        case "-y":
        case "--all":
            set INSTALL_HOOK = 1
            set INSTALL_BIN = 1
            set PROMPT_USER = 0
            breaksw
        case "--hook-only":
            set INSTALL_HOOK = 1
            set INSTALL_BIN = 0
            set PROMPT_USER = 0
            breaksw
        case "--bin-only":
            set INSTALL_HOOK = 0
            set INSTALL_BIN = 1
            set PROMPT_USER = 0
            breaksw
        case "--help":
        case "-h":
            echo "Usage: ./setup.csh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --noprompt, -y, --all   Install both global Git hook and CLI tool without prompting"
            echo "  --hook-only             Install only global Git hook (~/.git_hooks)"
            echo "  --bin-only              Install only CLI tool (~/.local/bin)"
            echo "  -h, --help              Show this help message"
            exit 0
        default:
            echo "Unknown option: $arg"
            echo "Run ./setup.csh --help for available options."
            exit 1
    endsw
end

# Interactive prompt if no arguments were passed
if ( $PROMPT_USER == 1 ) then
    echo "========================================================"
    echo "       Em-Dash & Unicode Dash Cleaner Setup (csh)"
    echo "========================================================"
    echo ""
    echo "What would you like to install?"
    echo "  1) Both: Global Git Hook (~/.git_hooks) AND CLI Tool (~/.local/bin) [Recommended]"
    echo "  2) Global Git Hook only (~/.git_hooks)"
    echo "  3) CLI Tool only (~/.local/bin)"
    echo "  4) Exit without installing"
    echo ""
    echo -n "Enter choice [1-4] (default: 1): "
    set choice = "$<"

    switch ( "$choice" )
        case "1":
        case "":
        case "both":
            set INSTALL_HOOK = 1
            set INSTALL_BIN = 1
            breaksw
        case "2":
        case "hook":
            set INSTALL_HOOK = 1
            set INSTALL_BIN = 0
            breaksw
        case "3":
        case "bin":
            set INSTALL_HOOK = 0
            set INSTALL_BIN = 1
            breaksw
        case "4":
        case "q":
        case "quit":
        case "exit":
            echo "Setup cancelled. No changes made."
            exit 0
        default:
            echo "Invalid selection: $choice. Aborting."
            exit 1
    endsw
endif

echo ""
echo "--------------------------------------------------------"

# 1. Install CLI Tool to ~/.local/bin
if ( $INSTALL_BIN == 1 ) then
    echo "[1/2] Installing CLI Tool to $BIN_DIR..."
    if ( ! -d "$BIN_DIR" ) then
        mkdir -p "$BIN_DIR"
    endif
    cp "$SCRIPT_DIR/detect_emdash.py" "$BIN_DIR/detect_emdash.py"
    chmod +x "$BIN_DIR/detect_emdash.py"
    echo "      -> Installed: $BIN_DIR/detect_emdash.py"
endif

# 2. Install Global Git Hook to ~/.git_hooks
if ( $INSTALL_HOOK == 1 ) then
    echo "[2/2] Installing Global Git Hook to $HOOKS_DIR..."
    if ( ! -d "$HOOKS_DIR" ) then
        mkdir -p "$HOOKS_DIR"
    endif
    cp "$SCRIPT_DIR/detect_emdash.py" "$HOOKS_DIR/detect_emdash.py"
    cp "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/detect_emdash.py"
    chmod +x "$HOOKS_DIR/pre-commit"

    git config --global core.hooksPath "$HOOKS_DIR"
    set CURRENT_PATH = `git config --global core.hooksPath`
    echo "      -> Installed: $HOOKS_DIR/pre-commit"
    echo "      -> Configured git core.hooksPath = $CURRENT_PATH"
endif

echo "--------------------------------------------------------"
echo "Setup completed successfully!"
if ( $INSTALL_HOOK == 1 ) then
    echo "* 'git commit' in any repo will auto-clean Unicode dashes in staged files."
endif
if ( $INSTALL_BIN == 1 ) then
    echo "* Run 'detect_emdash.py --help' to use the CLI tool manually anytime."
endif
echo "========================================================"
