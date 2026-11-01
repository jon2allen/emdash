# Portable Global Git Hook: Em-Dash & Unicode Dash Cleaner

A portable, cross-platform global Git pre-commit hook that automatically catches and replaces non-standard Unicode dash variants (`-`, `-`, `-`, `-`, `-`, `-`, `-`, etc.) with standard ASCII hyphens (`-`, `U+002D`) upon `git commit`.

Compatible across **macOS**, **Linux** (bash/sh), and **FreeBSD** (sh/csh/tcsh).

---

## What It Does
When installed, running `git commit` in **any** Git repository on your machine will:
1. Identify all currently staged files (excluding deletions).
2. Scan them with `detect_emdash.py`.
3. If any Unicode dashes are present, automatically replace them with standard ASCII `-` (`U+002D`).
4. Re-stage the cleaned files before completing the commit.

---

## Directory Contents
- **`detect_emdash.py`**: Standalone Python 3 scanner and in-place corrector (supports `--fix`, `--dry-run`, `--backup`, `--json`, and `-q`).
- **`pre-commit`**: POSIX `/bin/sh` hook script placed in `~/.git_hooks/`.
- **`setup.sh`**: Setup installer for macOS and Linux (`sh`/`bash`/`zsh`).
- **`setup.csh`**: Setup installer for FreeBSD and `csh`/`tcsh` shells.

---

## Quick Installation

### On macOS / Linux (bash / zsh / sh):
```bash
cd emdash
chmod +x setup.sh
./setup.sh
```

### On FreeBSD (csh / tcsh):
```csh
cd emdash
chmod +x setup.csh
./setup.csh
```

---

## How It Works Under the Hood
1. Copies `detect_emdash.py` and `pre-commit` into `~/.git_hooks/`.
2. Runs `git config --global core.hooksPath ~/.git_hooks`.
3. Applies universally to all current and future Git repositories on the system without needing per-repository configuration.

---

## How to Uninstall / Disable
If you ever want to remove or disable the global hook:

```bash
# Disable global hooks in Git:
git config --global --unset core.hooksPath

# Optional: Remove the ~/.git_hooks folder:
rm -rf ~/.git_hooks
```

To temporarily bypass the hook on a single commit:
```bash
git commit --no-verify
```

