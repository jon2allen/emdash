# Portable Global Git Hook: Em-Dash & Unicode Dash Cleaner

A portable, cross-platform global Git pre-commit hook that automatically catches and replaces non-standard Unicode dash variants (em dash U+2014, en dash U+2013, minus sign U+2212, non-breaking hyphen U+2011, and more) with standard ASCII hyphens (`-`, `U+002D`) upon `git commit`.

Compatible across **macOS**, **Linux** (bash/sh), and **FreeBSD** (sh/csh/tcsh).

---

## What It Does
When installed, running `git commit` in **any** Git repository on your machine will:
1. Identify all currently staged files (excluding deletions).
2. Scan them with `detect_emdash.py`.
3. If any Unicode dashes are staged, automatically replace them with standard ASCII `-` (`U+002D`). Soft hyphens (`U+00AD`) are invisible, so they are deleted instead.
4. Re-stage the cleaned files before completing the commit.

The commit is **rejected** rather than auto-fixed when fixing could disturb your work: the file has unstaged edits, you ran `git commit <path>`, or the file cannot be written. Files with no staged dashes are never touched.

The hook also runs the repository's own `.git/hooks/pre-commit` first, then any sibling hook sharing the global hooks directory (for example the emoji cleaner preserved as `pre-commit-emoji`). Hooks in other locations and other hook types are not chained, and commit messages are not scanned.

### Dashes that must stay
Auto-fix changes string literals as well as prose. Exempt paths in a repository's `.gitattributes`:

```
tests/fixtures/** -emdash
locale/** -emdash
```

---

## Directory Contents
- **`detect_emdash.py`**: Standalone Python 3 scanner and in-place corrector (supports `-r`, `--fix`, `--dry-run`, `--backup`, `--json`, `--exit-code`, and `-q`; requires Python 3.7+).
- **`pre-commit`**: POSIX `/bin/sh` hook script placed in `~/.git_hooks/`.
- **`setup.sh`**: Setup installer for macOS and Linux (`sh`/`bash`/`zsh`).
- **`setup.csh`**: Setup installer for FreeBSD and `csh`/`tcsh` shells.
- **`test_emdash.py`**, **`test_hook.py`**: Test suite (`python3 -m pytest`).

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

Both installers prompt by default and accept `--noprompt` / `-y` / `--all`, `--hook-only`, or `--bin-only`. Without a terminal, one of these flags is required.

If a different global pre-commit hook already occupies `~/.git_hooks/pre-commit` (for example the emoji cleaner), it is preserved as `pre-commit-emoji` (or `pre-commit-legacy`) and chained automatically, so both hooks keep running.

---

## Scanning Piped Input
With no file arguments, piped or redirected input is scanned automatically. Use `-` to request stdin explicitly, which is the safer choice in scripts:

```bash
git log | detect_emdash.py
git log | detect_emdash.py --exit-code -q
detect_emdash.py --fix - < notes.txt > clean.txt
```

With `--fix`, the cleaned text goes to stdout and reports go to stderr.

---

## How It Works Under the Hood
1. Copies `detect_emdash.py` and `pre-commit` into `~/.git_hooks/`.
2. Runs `git config --global core.hooksPath ~/.git_hooks`, saving any previous value as `core.hooksPathBackup`.
3. Applies universally to all current and future Git repositories on the system without needing per-repository configuration.

The hook hands the NUL-delimited list of staged paths to `detect_emdash.py --scan-staged`, which filters exempt paths (`git check-attr`) and reads every staged blob (`git cat-file --batch`) in one batched pass: a 50-file commit pays one Python startup instead of fifty. The staged path list is NUL-delimited end to end, so filenames containing newlines are detected; only the rare fixing loop falls back to newline splitting, and a path it cannot round-trip is rejected rather than silently committed. Requires Git 2.20+ for the batched object protocol.

---

## How to Uninstall / Disable
If you ever want to remove or disable the global hook:

```bash
# Disable global hooks in Git:
git config --global --unset core.hooksPath

# If setup saved a previous value, restore it:
git config --global core.hooksPath "$(git config --global core.hooksPathBackup)"
git config --global --unset core.hooksPathBackup

# Optional: Remove the ~/.git_hooks folder:
rm -rf ~/.git_hooks
```

To temporarily bypass the hook on a single commit:
```bash
git commit --no-verify
```

