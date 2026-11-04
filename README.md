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
- **`detect_emdash.py`**: Standalone Python 3 scanner and in-place corrector (supports `-r`, `--fix`, `--dry-run`, `--density`, `--backup`, `--json`, `--exit-code`, and `-q`; requires Python 3.7+; tested on 3.10.12).
- **`pre-commit`**: POSIX `/bin/sh` hook script placed in `~/.git_hooks/`.
- **`setup.sh`**: Setup installer for macOS and Linux (`sh`/`bash`/`zsh`).
- **`setup.csh`**: Setup installer for FreeBSD and `csh`/`tcsh` shells.
- **`test_emdash.py`**, **`test_hook.py`**: Test suite (`python3 -m pytest`).
- **`emdash_analysis.sh`**: Runner script that executes unit tests and generates the density analysis table across the testbed.
- **`pull_melville.sh`**: Fetches Melville and 19th-century public-domain texts into `melville/`.

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

The hook hands the NUL-delimited list of staged paths to `detect_emdash.py --scan-staged`, which filters exempt paths (`git check-attr`) and reads every staged blob (`git cat-file --batch`) in one batched pass: a 50-file commit pays one Python startup instead of fifty. The staged path list is NUL-delimited end to end, so filenames containing newlines are detected; only the rare fixing loop falls back to newline splitting, and a path it cannot round-trip is rejected rather than silently committed. Staged blob IDs come from `git ls-files --stage -z`, and blobs are requested by ID with plain `git cat-file --batch`, so the batch needs no newer Git flags.

### Tested versions
- Git 2.34.1
- Python 3.10.12, with pytest 9.2.0 (`python3 -m pytest`, 36 tests passing)

Other Git and Python versions have not been tested.

---

## Dash Density
`detect_emdash.py --density` reports, for each file, how many dashes appear per 1,000 words:

```
density = (dash count / word count) x 1000
```

It gives two densities: em dashes (U+2014) only, and all Unicode dash variants. A word is any token, split on whitespace and Unicode dashes, that contains a letter or digit. Every file is measured the same way, and nothing is modified (`--density` cannot be combined with `--fix`).

```bash
detect_emdash.py --density melville
detect_emdash.py --density -r docs/ --json
cat draft.md | detect_emdash.py --density
```

Inspired by the em dash frequency metric in ["The Last Fingerprint: How Markdown Training Shapes LLM Prose"](https://arxiv.org/html/2603.27006v1) (arXiv:2603.27006; see their research repository at [emfreeburg/the-last-fingerprint](https://github.com/emfreeburg/the-last-fingerprint)), which measures em dash frequency per 1,000 words:

- **Calculation note:** The reference script in the paper's study (`run_study.py`) performs a naive whitespace split (`text.split()`), which causes words conjoined by unspaced em dashes (e.g. `word\u2014word` (`word` + U+2014 + `word`)) to be counted as a single word. `detect_emdash.py` splits on Unicode dashes as well as whitespace, ensuring conjoined words are recognized as distinct words and yielding a slightly more accurate word count denominator. Because em dashes represent a small fraction of overall vocabulary, this subtle distinction does not diminish or alter the broader empirical findings of the paper.

### Melville & 19th-Century Testbed
The `melville/` directory (fetched by `pull_melville.sh`) serves as a testbed of public-domain literature. Running `./detect_emdash.py --density melville/*.txt` produces:

```
File                                     Words  Em dashes    Em/1k  All dashes   All/1k
-----------------------------------------------------------------------------------------
melville/a_tale_of_two_cities.txt       138903          2     0.01           2     0.01
melville/bartleby_the_scrivener.txt      14479        110     7.60         110     7.60
melville/benito_cereno.txt               82719        581     7.02         581     7.02
melville/billy_budd.txt                 119289          0     0.00           0     0.00
melville/frankenstein.txt                78198        126     1.61         126     1.61
melville/huckleberry_finn.txt           115170       1127     9.79        1127     9.79
melville/moby_dick_full.txt             217395       1730     7.96        1730     7.96
melville/omoo.txt                       105282        545     5.18         545     5.18
melville/pierre.txt                     155102          2     0.01           2     0.01
melville/the_confidence_man.txt          96628          2     0.02           2     0.02
melville/typee.txt                      116331          2     0.02           2     0.02
melville/white_jacket.txt               143392       1005     7.01        1005     7.01
-----------------------------------------------------------------------------------------
TOTAL                                  1382888       5232     3.78        5232     3.78
Density = (dash count / word count) x 1000
```
*(Note: Variations across digital editions reflect Project Gutenberg transcription styles, where some texts transcribe em dashes as literal Unicode `U+2014` while others used typewriter `--` conventions).*

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

---

## References
- Freeburg, E. M. (2026). *The Last Fingerprint: How Markdown Training Shapes LLM Prose*. [arXiv:2603.27006](https://arxiv.org/abs/2603.27006) (Empirical evaluation and analysis of em dash frequencies across large language model prose; research code: [emfreeburg/the-last-fingerprint](https://github.com/emfreeburg/the-last-fingerprint)).
- Project Gutenberg. Public-domain literary corpus texts retrieved for benchmarking historical 19th-century typography.

